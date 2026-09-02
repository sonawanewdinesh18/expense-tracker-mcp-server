"""
server.py
---------
A fully functional, multi-user Expense Tracker MCP server, backed by
Supabase, deployable as a remote server that many different people can
connect to at once -- each one only ever seeing their own expenses.

How multi-user isolation works:
  1. Each user is given a personal API key (see create_user.py).
  2. When they connect, their MCP client sends that key as:
         Authorization: Bearer <their-api-key>
  3. SupabaseAPIKeyVerifier below looks that key up in Supabase and
     resolves it to a user_id.
  4. Every tool call reads that user_id via get_access_token() and passes
     it into every database query -- so User A can never see, edit, or
     delete User B's expenses, even though they're both hitting the same
     running server.

Run it:
    Local dev (stdio, for Claude Desktop):
        python server.py --stdio

    Local dev (HTTP, for testing with the Inspector or a browser client):
        python server.py

    Production (what the Dockerfile runs):
        python server.py
"""

import os
import sys
from datetime import date
from typing import Optional

from pydantic import AnyHttpUrl

from mcp.server.mcpserver import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token

from db import (
    lookup_user_id_by_api_key,
    db_add_expense,
    db_list_expenses,
    db_update_expense,
    db_delete_expense,
    db_get_summary,
    db_list_categories,
)

VALID_PERIODS = {"week", "month", "year", "all"}


# ---------------------------------------------------------------------
# 1. Authentication: verify each request's API key against Supabase
# ---------------------------------------------------------------------

class SupabaseAPIKeyVerifier(TokenVerifier):
    """Treats each user's personal API key as an OAuth-style bearer token.

    MCP's auth layer expects a TokenVerifier; it doesn't care whether the
    token is a "real" OAuth token or, as here, a long random string we
    mint ourselves and store in Supabase. Either way, this class is the
    single place that decides whether a request is allowed through.
    """

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        user_id = lookup_user_id_by_api_key(token)
        if user_id is None:
            return None  # unknown/revoked key -> request gets a 401
        return AccessToken(
            token=token,
            client_id=user_id,       # we stash the user_id here
            scopes=["expense_tracker"],
        )


def _current_user_id() -> str:
    """Every tool calls this first to find out WHO is calling."""
    access_token = get_access_token()
    if access_token is None:
        # Only happens over stdio (no HTTP auth) or if auth is misconfigured.
        raise PermissionError(
            "No authenticated user found. Connect over Streamable HTTP with "
            "'Authorization: Bearer <your-api-key>', or run with --stdio for "
            "trusted local single-user use."
        )
    return access_token.client_id


# ---------------------------------------------------------------------
# 2. Build the server
# ---------------------------------------------------------------------

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")
STDIO_MODE = "--stdio" in sys.argv  # local single-user mode, no HTTP auth needed

if STDIO_MODE:
    # Over stdio there is no HTTP layer, so there's nothing to attach
    # bearer-token auth to -- the process boundary itself is the security
    # boundary. Great for local testing; not for the shared remote server.
    mcp = MCPServer(
        "Expense Tracker",
        instructions="Track, list, update, and summarize personal expenses.",
    )
    LOCAL_STDIO_USER_ID = os.environ.get("LOCAL_USER_ID", "local-dev-user")
else:
    mcp = MCPServer(
        "Expense Tracker",
        instructions=(
            "Track, list, update, and summarize personal expenses. "
            "Every user's data is private to their own API key."
        ),
        token_verifier=SupabaseAPIKeyVerifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(SERVER_URL),
            resource_server_url=AnyHttpUrl(SERVER_URL),
            required_scopes=["expense_tracker"],
        ),
    )


def _user_id() -> str:
    if STDIO_MODE:
        return LOCAL_STDIO_USER_ID
    return _current_user_id()


# ---------------------------------------------------------------------
# 3. Tools
# ---------------------------------------------------------------------

@mcp.tool()
async def add_expense(
    amount: float,
    category: str,
    description: str = "",
    expense_date: Optional[str] = None,
) -> dict:
    """Add a new expense for the current user.

    amount: positive number, e.g. 12.50
    category: a short label, e.g. "Food", "Transport", "Rent"
    description: optional free-text note
    expense_date: optional date in YYYY-MM-DD format; defaults to today
    """
    user_id = _user_id()
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    d = expense_date or date.today().isoformat()
    clean_category = category.strip().title()

    row = db_add_expense(user_id, amount, clean_category, description, d)
    return {"status": "created", "expense": row}


@mcp.tool()
async def list_expenses(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List the current user's expenses, most recent first.

    category: optional exact category filter, e.g. "Food"
    start_date / end_date: optional YYYY-MM-DD range filters (inclusive)
    limit: max rows to return (default 50)
    """
    user_id = _user_id()
    clean_category = category.strip().title() if category else None
    rows = db_list_expenses(user_id, clean_category, start_date, end_date, limit)
    return {"count": len(rows), "expenses": rows}


@mcp.tool()
async def update_expense(
    expense_id: str,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    expense_date: Optional[str] = None,
) -> dict:
    """Update one or more fields of an expense the current user owns.

    Only pass the fields you want to change -- everything else is left as-is.
    """
    user_id = _user_id()
    fields: dict = {}

    if amount is not None:
        if amount <= 0:
            raise ValueError("amount must be greater than 0")
        fields["amount"] = amount
    if category is not None:
        fields["category"] = category.strip().title()
    if description is not None:
        fields["description"] = description
    if expense_date is not None:
        fields["expense_date"] = expense_date

    if not fields:
        raise ValueError("Provide at least one field to update.")

    row = db_update_expense(user_id, expense_id, fields)
    if row is None:
        raise ValueError("Expense not found, or it doesn't belong to you.")
    return {"status": "updated", "expense": row}


@mcp.tool()
async def delete_expense(expense_id: str) -> dict:
    """Permanently delete an expense the current user owns."""
    user_id = _user_id()
    ok = db_delete_expense(user_id, expense_id)
    if not ok:
        raise ValueError("Expense not found, or it doesn't belong to you.")
    return {"status": "deleted", "expense_id": expense_id}


@mcp.tool()
async def get_summary(period: str = "month") -> dict:
    """Summarize the current user's spending.

    period: one of "week", "month", "year", "all"
    Returns the total spent, transaction count, and a per-category breakdown.
    """
    user_id = _user_id()
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of: {', '.join(sorted(VALID_PERIODS))}")
    return db_get_summary(user_id, period)


@mcp.tool()
async def list_categories() -> dict:
    """List the distinct expense categories the current user has used so far."""
    user_id = _user_id()
    return {"categories": db_list_categories(user_id)}


@mcp.prompt()
def monthly_report_prompt() -> str:
    """A ready-made prompt for generating a friendly monthly spending report."""
    return (
        "Call get_summary with period='month' and list_expenses for this "
        "month, then write a short, friendly summary: total spent this "
        "month, the top 3 spending categories, and one practical, specific "
        "suggestion for reducing spending next month."
    )


# ---------------------------------------------------------------------
# 4. Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    if STDIO_MODE:
        mcp.run(transport="stdio")
    else:
        port = int(os.environ.get("PORT", 8000))
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
