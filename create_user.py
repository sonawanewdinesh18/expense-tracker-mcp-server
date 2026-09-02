"""
create_user.py
---------------
Run this once per new person you want to give access to your Expense
Tracker MCP server. It mints a fresh, unique API key, stores it in
Neon PostgreSQL alongside a brand new user_id, and prints both.

Usage:
    python create_user.py "Alice"
    python create_user.py "Bob's work laptop"

Give the printed api_key to that person. They'll use it as their
Authorization: Bearer <api_key> when connecting an MCP client (or when
adding your server as a remote connector in Claude Desktop / Claude.ai).
"""

import os
import secrets
import sys
import uuid
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()


def main() -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_UNPOOLED")
    if not db_url:
        print("ERROR: DATABASE_URL is not set in your .env file.")
        sys.exit(1)

    label = sys.argv[1] if len(sys.argv) > 1 else "unnamed user"
    api_key = "et_" + secrets.token_urlsafe(32)
    user_id = str(uuid.uuid4())

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_keys (user_id, api_key, label)
                VALUES (%s, %s, %s)
                RETURNING user_id, api_key, label
                """,
                (user_id, api_key, label),
            )
            row = cur.fetchone()
            conn.commit()

    print("\nNew user created successfully in Neon!\n")
    print(f"  label   : {row['label']}")
    print(f"  user_id : {row['user_id']}")
    print(f"  api_key : {row['api_key']}\n")
    print("Give this API key to the user. In their MCP client config, they should")
    print("connect to this server's URL with header:")
    print(f'  Authorization: Bearer {row["api_key"]}\n')


if __name__ == "__main__":
    main()
