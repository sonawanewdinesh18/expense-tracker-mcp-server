"""
test_client.py
---------------
A minimal MCP client that proves the whole system works end to end,
without needing Claude Desktop. Point it at your local server (during
development) or your deployed remote URL (once live), with a real API
key from create_user.py.

Usage:
    python test_client.py http://localhost:8000/mcp et_your_api_key_here
    python test_client.py https://your-app.onrender.com/mcp et_your_api_key_here
"""

import asyncio
import json
import sys
import httpx2

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(url: str, api_key: str) -> None:
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx2.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f"Connected to {url}\n")

                tools = await session.list_tools()
                print("Available tools:", [t.name for t in tools.tools], "\n")

                print("-- Adding a couple of test expenses --")
                r1 = await session.call_tool(
                    "add_expense",
                    {"amount": 12.50, "category": "Food", "description": "Lunch"},
                )
                print("Expense 1:", r1.content[0].text if r1.content else r1)
                r2 = await session.call_tool(
                    "add_expense",
                    {"amount": 40.00, "category": "Transport", "description": "Fuel"},
                )
                print("Expense 2:", r2.content[0].text if r2.content else r2, "\n")

                print("-- Listing this user's expenses --")
                listed = await session.call_tool("list_expenses", {"limit": 10})
                print("Listed expenses:", listed.content[0].text if listed.content else listed, "\n")

                print("-- Monthly summary --")
                summary = await session.call_tool("get_summary", {"period": "month"})
                print("Summary:", summary.content[0].text if summary.content else summary, "\n")

                print("-- Categories used --")
                cats = await session.call_tool("list_categories", {})
                print("Categories:", cats.content[0].text if cats.content else cats)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_client.py <server_url> <api_key>")
        sys.exit(1)

    asyncio.run(main(sys.argv[1], sys.argv[2]))
