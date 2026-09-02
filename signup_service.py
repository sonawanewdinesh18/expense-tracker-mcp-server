"""
signup_service.py  (OPTIONAL, advanced)
----------------------------------------
Self-serve signup endpoint for the Expense Tracker MCP server, backed by Neon.
"""

import os
import secrets
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg
from psycopg.rows import dict_row

load_dotenv()

app = FastAPI(title="Expense Tracker Signup Service")


def get_db_connection():
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_UNPOOLED")
    if not db_url:
        raise ValueError("DATABASE_URL is not set.")
    return psycopg.connect(db_url, row_factory=dict_row)


class SignupRequest(BaseModel):
    label: str = "unnamed user"


class SignupResponse(BaseModel):
    user_id: str
    api_key: str


@app.post("/signup", response_model=SignupResponse)
def signup(req: SignupRequest):
    if len(req.label) > 200:
        raise HTTPException(400, "label is too long")

    api_key = "et_" + secrets.token_urlsafe(32)
    user_id = str(uuid.uuid4())

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys (user_id, api_key, label)
                VALUES (%s, %s, %s)
                RETURNING user_id, api_key
                """,
                (user_id, api_key, req.label),
            )
            row = cur.fetchone()
            conn.commit()

    return SignupResponse(user_id=str(row["user_id"]), api_key=row["api_key"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SIGNUP_PORT", 8001)))
