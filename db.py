"""
db.py
-----
All Neon PostgreSQL database access lives here, in one place, so server.py never
talks to the database directly. Every function that touches the `expenses`
table takes a `user_id` and filters by it -- this is what keeps each
user's data private on a server that many different users share.
"""

import os
import logging
from datetime import date, timedelta
from typing import Optional, Any
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()
logger = logging.getLogger("expense-tracker-db")


def _clean_database_url(url: str) -> str:
    """Sanitize database URL to avoid libpq quoting issues and unsupported parameters."""
    if not url:
        return ""
    cleaned = url.strip().strip("'").strip('"')
    # Remove unsupported channel_binding in libpq connection string if present
    cleaned = cleaned.replace("&channel_binding=require", "")
    cleaned = cleaned.replace("channel_binding=require&", "")
    cleaned = cleaned.replace("channel_binding=require", "")
    if cleaned.endswith("?"):
        cleaned = cleaned[:-1]
    return cleaned


def get_db_connection():
    """Create a connection to Neon PostgreSQL using sanitized DATABASE_URL."""
    raw_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_UNPOOLED")
    if not raw_url:
        raise RuntimeError("Database connection error: DATABASE_URL is not set in environment.")
    
    clean_url = _clean_database_url(raw_url)
    try:
        return psycopg.connect(clean_url, row_factory=dict_row)
    except Exception as exc:
        logger.error("Database connection failure: %s", type(exc).__name__)
        # Never leak raw credentials or connection string in error message
        raise RuntimeError("Database connection failed. Please verify the database configuration and credentials.") from None


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Helper to convert date/uuid/decimal objects to JSON-serializable primitives."""
    if not row:
        return row
    result = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        elif hasattr(v, "__str__") and type(v).__name__ in ("UUID", "Decimal"):
            result[k] = float(v) if type(v).__name__ == "Decimal" else str(v)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------
# Auth lookup: API key -> user_id
# ---------------------------------------------------------------------

def lookup_user_id_by_api_key(api_key: str) -> Optional[str]:
    """Return the user_id that owns this API key, or None if it's invalid or revoked."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM api_keys WHERE api_key = %s AND revoked = false LIMIT 1",
                    (api_key,),
                )
                row = cur.fetchone()
                if row:
                    return str(row["user_id"])
    except Exception as exc:
        logger.error("lookup_user_id_by_api_key error: %s", type(exc).__name__)
        raise RuntimeError("Database error during authentication.") from None
    return None


# ---------------------------------------------------------------------
# Expense CRUD -- every query below is scoped to a single user_id
# ---------------------------------------------------------------------

def db_add_expense(
    user_id: str,
    amount: float,
    category: str,
    description: str,
    expense_date: str,
) -> dict:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO expenses (user_id, amount, category, description, expense_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, amount, category, description or "", expense_date),
                )
                row = cur.fetchone()
                conn.commit()
                return _serialize_row(row)
    except Exception as exc:
        logger.error("db_add_expense error: %s", type(exc).__name__)
        raise RuntimeError("Database error while adding expense.") from None


def db_list_expenses(
    user_id: str,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    query = "SELECT * FROM expenses WHERE user_id = %s"
    params: list[Any] = [user_id]

    if category:
        query += " AND category = %s"
        params.append(category)
    if start_date:
        query += " AND expense_date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND expense_date <= %s"
        params.append(end_date)

    query += " ORDER BY expense_date DESC, created_at DESC LIMIT %s"
    params.append(limit)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [_serialize_row(r) for r in rows]
    except Exception as exc:
        logger.error("db_list_expenses error: %s", type(exc).__name__)
        raise RuntimeError("Database error while listing expenses.") from None


def db_get_expense(user_id: str, expense_id: str) -> Optional[dict]:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM expenses WHERE id = %s AND user_id = %s LIMIT 1",
                    (expense_id, user_id),
                )
                row = cur.fetchone()
                return _serialize_row(row) if row else None
    except Exception as exc:
        logger.error("db_get_expense error: %s", type(exc).__name__)
        raise RuntimeError("Database error while fetching expense.") from None


def db_update_expense(user_id: str, expense_id: str, fields: dict) -> Optional[dict]:
    if not fields:
        return db_get_expense(user_id, expense_id)

    set_clauses = []
    params: list[Any] = []

    for k, v in fields.items():
        if k in ("amount", "category", "description", "expense_date"):
            set_clauses.append(f"{k} = %s")
            params.append(v)

    if not set_clauses:
        return db_get_expense(user_id, expense_id)

    set_clauses.append("updated_at = NOW()")
    sql = f"UPDATE expenses SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s RETURNING *"
    params.extend([expense_id, user_id])

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                conn.commit()
                return _serialize_row(row) if row else None
    except Exception as exc:
        logger.error("db_update_expense error: %s", type(exc).__name__)
        raise RuntimeError("Database error while updating expense.") from None


def db_delete_expense(user_id: str, expense_id: str) -> bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM expenses WHERE id = %s AND user_id = %s RETURNING id",
                    (expense_id, user_id),
                )
                row = cur.fetchone()
                conn.commit()
                return row is not None
    except Exception as exc:
        logger.error("db_delete_expense error: %s", type(exc).__name__)
        raise RuntimeError("Database error while deleting expense.") from None


def db_list_categories(user_id: str) -> list[str]:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT category FROM expenses WHERE user_id = %s ORDER BY category ASC",
                    (user_id,),
                )
                rows = cur.fetchall()
                return [r["category"] for r in rows]
    except Exception as exc:
        logger.error("db_list_categories error: %s", type(exc).__name__)
        raise RuntimeError("Database error while listing categories.") from None


def db_get_summary(user_id: str, period: str) -> dict:
    """period: 'week' | 'month' | 'year' | 'all'"""
    today = date.today()

    if period == "week":
        start = today - timedelta(days=today.weekday())
    elif period == "month":
        start = today.replace(day=1)
    elif period == "year":
        start = today.replace(month=1, day=1)
    else:  # "all"
        start = None

    query = "SELECT amount, category, expense_date FROM expenses WHERE user_id = %s"
    params: list[Any] = [user_id]

    if start:
        query += " AND expense_date >= %s"
        params.append(start.isoformat())

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as exc:
        logger.error("db_get_summary error: %s", type(exc).__name__)
        raise RuntimeError("Database error while calculating summary.") from None

    total = sum(float(r["amount"]) for r in rows)
    by_category: dict[str, float] = {}
    for r in rows:
        by_category[r["category"]] = by_category.get(r["category"], 0.0) + float(r["amount"])

    breakdown = sorted(
        [{"category": c, "total": round(t, 2)} for c, t in by_category.items()],
        key=lambda x: x["total"],
        reverse=True,
    )

    return {
        "period": period,
        "since": start.isoformat() if start else None,
        "until": today.isoformat(),
        "total_spent": round(total, 2),
        "transaction_count": len(rows),
        "by_category": breakdown,
    }
