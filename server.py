"""
server.py
---------
Expense Tracker MCP Server backed by Neon PostgreSQL.
Deployable to FastMCP Cloud (Prefect Horizon), Render, Railway, Docker,
or local development (FastMCP dev / Inspector / Claude Desktop).
Supports multiple users with complete data isolation using user_id or API keys.
"""

import os
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from fastmcp import FastMCP

from db import (
    lookup_user_id_by_api_key,
    db_add_expense,
    db_list_expenses,
    db_update_expense,
    db_delete_expense,
    db_get_summary,
    db_list_categories,
)

load_dotenv()

# Create the FastMCP server instance (this is what FastMCP Cloud / Horizon imports)
mcp = FastMCP(
    "expenses-maneger",
    instructions=(
        "Track, list, update, and summarize personal expenses backed by Neon PostgreSQL. "
        "Supports multiple users: users can specify their 'user_id' (such as their username, email, or name) "
        "or their personal 'api_key' to keep their expenses completely isolated and private from other users."
    ),
)

VALID_PERIODS = {"week", "month", "year", "all"}
DEFAULT_USER_ID = "default_user"


def _resolve_user_id(user_id: Optional[str], api_key: Optional[str]) -> str:
    """Resolve user identity from API key, custom user_id string, or environment default."""
    if api_key and api_key.strip():
        resolved = lookup_user_id_by_api_key(api_key.strip())
        if resolved:
            return resolved
    if user_id and user_id.strip():
        return user_id.strip()
    return os.environ.get("DEFAULT_USER_ID", DEFAULT_USER_ID)


# ---------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------

@mcp.tool
def add_expense(
    amount: float,
    category: str,
    description: str = "",
    expense_date: Optional[str] = None,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Add a new expense record for a specific user.

    amount: positive number, e.g. 12.50
    category: short label, e.g. "Food", "Transport", "Rent"
    description: optional note
    expense_date: optional date in YYYY-MM-DD format (defaults to today)
    user_id: optional user identifier (e.g. "alice", "bob", "john@example.com") to keep data separate
    api_key: optional API key (et_...) to scope to a specific user
    """
    if amount <= 0:
        raise ValueError("amount must be greater than 0")

    uid = _resolve_user_id(user_id, api_key)
    d = expense_date or date.today().isoformat()
    clean_category = category.strip().title()

    row = db_add_expense(uid, amount, clean_category, description, d)
    return {"status": "created", "expense": row}


@mcp.tool
def list_expenses(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """List expenses for a specific user, sorted by date descending.

    category: optional category filter, e.g. "Food"
    start_date / end_date: optional YYYY-MM-DD range filters (inclusive)
    limit: maximum number of rows to return (default 50)
    user_id: optional user identifier (e.g. "alice", "bob") to view only that person's expenses
    api_key: optional API key (et_...) to scope to a specific user
    """
    uid = _resolve_user_id(user_id, api_key)
    clean_category = category.strip().title() if category else None
    rows = db_list_expenses(uid, clean_category, start_date, end_date, limit)
    return {"user_id": uid, "count": len(rows), "expenses": rows}


@mcp.tool
def update_expense(
    expense_id: str,
    amount: Optional[float] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    expense_date: Optional[str] = None,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Update one or more fields of an existing expense for a specific user.

    expense_id: UUID of the expense to update
    user_id: optional user identifier who owns this expense
    Only provide the fields you want to change.
    """
    uid = _resolve_user_id(user_id, api_key)
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

    row = db_update_expense(uid, expense_id, fields)
    if row is None:
        raise ValueError("Expense not found, or it doesn't belong to this user.")
    return {"status": "updated", "expense": row}


@mcp.tool
def delete_expense(
    expense_id: str,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Permanently delete an expense for a specific user.

    expense_id: UUID of the expense to delete
    user_id: optional user identifier who owns this expense
    """
    uid = _resolve_user_id(user_id, api_key)
    ok = db_delete_expense(uid, expense_id)
    if not ok:
        raise ValueError("Expense not found, or it doesn't belong to this user.")
    return {"status": "deleted", "expense_id": expense_id}


@mcp.tool
def get_summary(
    period: str = "month",
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """Summarize spending with totals and per-category breakdown for a specific user.

    period: one of "week", "month", "year", "all" (default "month")
    user_id: optional user identifier (e.g. "alice", "bob") to summarize only that person's spending
    """
    uid = _resolve_user_id(user_id, api_key)
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of: {', '.join(sorted(VALID_PERIODS))}")
    summary = db_get_summary(uid, period)
    summary["user_id"] = uid
    return summary


@mcp.tool
def list_categories(
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """List all distinct expense categories recorded so far by a specific user.

    user_id: optional user identifier
    """
    uid = _resolve_user_id(user_id, api_key)
    return {"user_id": uid, "categories": db_list_categories(uid)}


@mcp.prompt
def monthly_report_prompt(user_id: Optional[str] = None) -> str:
    """A ready-made prompt for generating a comprehensive monthly spending report."""
    target_user = f" for user '{user_id}'" if user_id else ""
    return (
        f"Call get_summary with period='month'{target_user} and list_expenses for this month. "
        "Then generate a clear summary containing: total amount spent, top 3 spending categories, "
        "and practical recommendations to optimize expenses next month."
    )


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="sse", port=port, host="0.0.0.0")
