"""
server.py
---------
Expense Tracker MCP Server backed by Neon PostgreSQL.
Deployable to FastMCP Cloud (Prefect Horizon), Render, Railway, Docker,
or local development (FastMCP dev / Inspector / Claude Desktop).
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
    instructions="Track, list, update, and summarize personal expenses backed by Neon PostgreSQL.",
)

VALID_PERIODS = {"week", "month", "year", "all"}
DEFAULT_USER_ID = "bca2fa1b-24fb-4937-9964-c4eface24860"


def _resolve_user_id(user_id: Optional[str], api_key: Optional[str]) -> str:
    """Resolve user identity from API key, user_id param, or environment default."""
    if api_key:
        resolved = lookup_user_id_by_api_key(api_key)
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
    """Add a new expense record.

    amount: positive number, e.g. 12.50
    category: short label, e.g. "Food", "Transport", "Rent"
    description: optional note
    expense_date: optional date in YYYY-MM-DD format (defaults to today)
    user_id: optional user identifier
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
    """List expenses, sorted by date descending.

    category: optional category filter, e.g. "Food"
    start_date / end_date: optional YYYY-MM-DD range filters (inclusive)
    limit: maximum number of rows to return (default 50)
    user_id: optional user identifier
    api_key: optional API key (et_...) to scope to a specific user
    """
    uid = _resolve_user_id(user_id, api_key)
    clean_category = category.strip().title() if category else None
    rows = db_list_expenses(uid, clean_category, start_date, end_date, limit)
    return {"count": len(rows), "expenses": rows}


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
    """Update one or more fields of an existing expense.

    expense_id: UUID of the expense to update
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
    """Permanently delete an expense.

    expense_id: UUID of the expense to delete
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
    """Summarize spending with totals and per-category breakdown.

    period: one of "week", "month", "year", "all" (default "month")
    """
    uid = _resolve_user_id(user_id, api_key)
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of: {', '.join(sorted(VALID_PERIODS))}")
    return db_get_summary(uid, period)


@mcp.tool
def list_categories(
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """List all distinct expense categories recorded so far."""
    uid = _resolve_user_id(user_id, api_key)
    return {"categories": db_list_categories(uid)}


@mcp.prompt
def monthly_report_prompt() -> str:
    """A ready-made prompt for generating a comprehensive monthly spending report."""
    return (
        "Call get_summary with period='month' and list_expenses for this month. "
        "Then generate a clear summary containing: total amount spent, top 3 spending categories, "
        "and practical recommendations to optimize expenses next month."
    )


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="sse", port=port, host="0.0.0.0")
