# 💰 Expense Tracker MCP Server (Neon PostgreSQL & Remote-Ready)

A production-grade, multi-user **Model Context Protocol (MCP)** server that allows AI assistants (such as Claude Desktop, Claude.ai, or custom MCP agents) to add, list, update, delete, and summarize expenses.

Backed by **Neon PostgreSQL**, this server enforces strict per-user data isolation through Bearer token authentication, allowing a single deployed instance to safely serve multiple users simultaneously.

---

## 🌟 Key Features

- **🛡️ Multi-User Isolation**: Every user receives their own API key (`et_...`). The server resolves the key server-side and scopes all queries to `user_id`.
- **⚡ Neon PostgreSQL**: Serverless, high-performance PostgreSQL persistence with connection pooling.
- **🌐 Remote & Local Transports**: Supports both `streamable-http` (production remote server) and `--stdio` (local single-user testing).
- **🛠️ 6 MCP Tools + 1 Prompt**:
  - `add_expense`: Record a new expense with category, amount, description, and date.
  - `list_expenses`: Query past expenses with category and date-range filters.
  - `update_expense`: Edit specific fields of an existing expense.
  - `delete_expense`: Permanently remove an expense.
  - `get_summary`: Aggregate spending breakdown by period (`week`, `month`, `year`, `all`).
  - `list_categories`: List unique spending categories used by the user.
  - `monthly_report_prompt`: Prompt template for generating spending analysis and savings tips.

---

## 📁 Repository Structure

```
├── server.py              # Main MCP server with auth and tool definitions
├── db.py                  # Neon PostgreSQL query layer (psycopg3)
├── create_user.py         # Admin CLI to mint API keys for users
├── signup_service.py      # Optional FastAPI microservice for self-serve signups
├── test_client.py         # End-to-end Python test client using MCP SDK
├── supabase_schema.sql    # PostgreSQL DDL schema & indexes
├── requirements.txt       # Python dependencies
├── Dockerfile             # Production container definition
├── neon.ts                # Neon configuration
├── .env.example           # Environment template
└── README.md              # Project documentation
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js (for MCP Inspector)
- A [Neon.tech](https://neon.tech) account

### 2. Clone & Install Dependencies
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Neon database connection string:
```env
DATABASE_URL=postgresql://user:password@ep-xyz.region.aws.neon.tech/neondb?sslmode=require
SERVER_URL=http://localhost:8000
PORT=8000
```

### 4. Create Database Tables
Run the SQL schema in your Neon Console SQL Editor or via Neon CLI:
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS api_keys (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL DEFAULT gen_random_uuid(),
    api_key     text NOT NULL UNIQUE,
    label       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    revoked     boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS expenses (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL,
    amount        numeric(12,2) NOT NULL CHECK (amount > 0),
    category      text NOT NULL,
    description   text DEFAULT '',
    expense_date  date NOT NULL DEFAULT current_date,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses (user_id, category);
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (api_key);
```

### 5. Mint Your First User API Key
```powershell
python create_user.py "Alice"
```
Output:
```text
New user created successfully in Neon!
  label   : Alice
  user_id : bca2fa1b-24fb-4937-9964-c4eface24860
  api_key : et_xQa7qTRld5XUDgB9MRhI-EDoMiD1La7XKN6Rw9IxVtI
```

### 6. Run the Server
```powershell
python server.py
```
The server will start on `http://0.0.0.0:8000`.

---

## 🧪 Testing

### Test with the Built-in Test Client
```powershell
python test_client.py http://localhost:8000/mcp et_your_api_key_here
```

### Test in FastMCP / MCP Inspector

**Option A: FastMCP CLI**
```powershell
mcp dev server.py
```
Open the printed URL in your browser (e.g. `http://localhost:6274`).

**Option B: Inspector UI with Streamable HTTP**
```powershell
npx @modelcontextprotocol/inspector
```
- Transport: `Streamable HTTP`
- URL: `http://localhost:8000/mcp`
- Header: `Authorization: Bearer et_your_api_key_here`

---

## ☁️ Remote Cloud Deployment

### Option 1: FastMCP Cloud / Prefect Horizon (Recommended)
1. Push this repository to GitHub.
2. Sign in to [horizon.prefect.io](https://horizon.prefect.io) with your GitHub account.
3. Select your repository.
4. Set the server entry point to: `server.py:mcp`.
5. Add the environment variable: `DATABASE_URL`.

### Option 2: Render.com
1. Create a **New Web Service** connected to your GitHub repository.
2. Select **Docker** environment.
3. Configure Environment Variables:
   - `DATABASE_URL`: Your Neon connection string
   - `SERVER_URL`: `https://your-app-name.onrender.com`
   - `PORT`: `8000`
4. Deploy. Your public MCP endpoint will be:
   `https://your-app-name.onrender.com/mcp`

### Option 3: Railway / Docker / Fly.io
Deploy using the provided `Dockerfile` and configure `DATABASE_URL` and `PORT`.

---

## 🤖 Connecting to Claude Desktop / Claude.ai

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "url": "https://your-deployed-server.onrender.com/mcp",
      "headers": {
        "Authorization": "Bearer et_your_personal_api_key"
      }
    }
  }
}
```

---

## 🔒 Security Architecture

1. **Authentication**: Requests carry `Authorization: Bearer <api_key>`.
2. **Server-Side Token Verification**: `SupabaseAPIKeyVerifier` validates the key against `api_keys` table and resolves `user_id`.
3. **Guaranteed Scoping**: `user_id` is retrieved strictly from the server-side auth token context (`get_access_token()`). Clients cannot spoof or supply a `user_id` parameter.
4. **Query Filtering**: Every query in `db.py` contains `.eq("user_id", user_id)` (or `WHERE user_id = %s`), ensuring full privacy across tenants.

---

## 📄 License
MIT License
