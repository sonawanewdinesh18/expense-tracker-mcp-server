# 💰 Expense Tracker MCP Server (Neon PostgreSQL)

> A beginner-friendly, production-ready **Model Context Protocol (MCP)** server that lets AI assistants (like Claude Desktop, Claude.ai, or custom AI agents) manage and analyze personal expenses with real-time persistence in **Neon PostgreSQL**.

---

## 📑 Table of Contents
1. [How It Works](#-how-it-works)
2. [Prerequisites](#-prerequisites)
3. [Step-by-Step Quickstart](#-step-by-step-quickstart)
4. [Testing Your Server Locally](#-testing-your-server-locally)
5. [Deploying to the Cloud (FastMCP Cloud / Horizon)](#-deploying-to-the-cloud-fastmcp-cloud--horizon)
6. [Connecting to Claude](#-connecting-to-claude)
7. [Copy-and-Paste Test Prompts](#-copy-and-paste-test-prompts)
8. [Tools & Prompts Reference](#-tools--prompts-reference)
9. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                 AI Client (Claude / Agent)                  │
│       "I spent $25 on books. Add this to my expenses."      │
└──────────────────────────────┬──────────────────────────────┘
                               │ MCP Protocol (HTTP / STDIO)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              server.py (FastMCP Server)                     │
│  - Receives AI tool calls (add_expense, list_expenses, etc) │
│  - Resolves user identity & prevents unauthorized access   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Scoped SQL Queries (psycopg3)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Neon PostgreSQL (Cloud Database)               │
│  - Securely stores tables: api_keys & expenses              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

Before you begin, make sure you have:
1. **Python 3.10 or higher** installed (`python --version`).
2. **Node.js 18+** installed (optional, for the web Inspector UI: `node --version`).
3. **A free [Neon.tech](https://neon.tech) account** (free serverless PostgreSQL).
4. **Git** installed (`git --version`).

---

## 🚀 Step-by-Step Quickstart

### Step 1: Clone the Repository & Navigate In
```powershell
git clone https://github.com/sonawanewdinesh18/expense-tracker-mcp-server.git
cd expense-tracker-mcp-server
```

---

### Step 2: Create and Activate a Virtual Environment
A virtual environment keeps project dependencies isolated and clean.

* **Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
* **macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

---

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

---

### Step 4: Set Up Your Free Database on Neon

1. Log in to [Neon.tech](https://neon.tech) and create a project (e.g. `expense-tracker`).
2. In the Neon Console, open **SQL Editor** from the left sidebar ➡️ Click **New Query**.
3. Paste the following SQL and click **Run**:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Stores API keys for multi-user authentication
CREATE TABLE IF NOT EXISTS api_keys (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL DEFAULT gen_random_uuid(),
    api_key     text NOT NULL UNIQUE,
    label       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    revoked     boolean NOT NULL DEFAULT false
);

-- Stores personal expenses
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

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses (user_id, category);
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (api_key);
```

4. Go to **Dashboard** / **Connection Details** and copy your **Postgres Connection URI** (e.g. `postgresql://neondb_owner:password@ep-xyz.aws.neon.tech/neondb?sslmode=require`).

---

### Step 5: Configure Environment Variables

1. Copy the template file `.env.example` to `.env`:
   ```powershell
   cp .env.example .env
   ```
2. Open `.env` in your text editor and paste your Neon connection string:
   ```env
   DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.aws.neon.tech/neondb?sslmode=require
   SERVER_URL=http://localhost:8000
   PORT=8000
   ```
   > ⚠️ **Important**: Do NOT wrap the URL in quotes (`""`).

---

### Step 6: Create Your First User & Generate an API Key

Run the admin CLI script to mint a personal user key:
```powershell
python create_user.py "My Name"
```

**Expected Output:**
```text
New user created successfully in Neon!

  label   : My Name
  user_id : bca2fa1b-24fb-4937-9964-c4eface24860
  api_key : et_xQa7qTRld5XUDgB9MRhI-EDoMiD1La7XKN6Rw9IxVtI
```
Save your printed `api_key` (`et_...`).

---

## 🧪 Testing Your Server Locally

### Option A: Using the FastMCP Web Inspector (Visual GUI)
Run the interactive inspector:
```powershell
mcp dev server.py
```
1. Click the URL printed in your terminal (e.g., `http://localhost:6274`).
2. Go to the **Tools** tab.
3. Test `add_expense`:
   - `amount`: `25.50`
   - `category`: `Food`
   - `description`: `Dinner with friends`
   - Click **Run Tool**.
4. Test `list_expenses` and `get_summary` to verify that your data is saved in Neon!

---

### Option B: Using the Command Line Test Client
In a separate terminal, run:
```powershell
# 1. Start the server
python server.py

# 2. In another terminal, run the test client:
python test_client.py http://localhost:8000/mcp et_YOUR_API_KEY_HERE
```

---

## ☁️ Deploying to the Cloud (FastMCP Cloud / Horizon)

You can host this server online permanently for free using **FastMCP Cloud (Prefect Horizon)**:

1. Push this project to your GitHub repository:
   ```powershell
   git push -u origin main
   ```
2. Visit **[horizon.prefect.io](https://horizon.prefect.io)** and sign in with GitHub.
3. Click **Deploy New Server** and select your `expense-tracker-mcp-server` repository.
4. Set the **Server Entrypoint** to:
   ```
   server.py:mcp
   ```
5. Go to **Settings** ➡️ **Environment Variables** and add:
   * **Key**: `DATABASE_URL`
   * **Value**: `postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.aws.neon.tech/neondb?sslmode=require`
6. Click **Deploy**.
7. Your server is now live at:
   `https://YOUR_SERVER_NAME.fastmcp.app/mcp`

---

## 🤖 Connecting to Claude

### Option 1: Claude.ai (Web Custom Connectors)
1. In [Claude.ai](https://claude.ai), go to **Settings** ➡️ **Connectors** (or click the plus icon in chat ➡️ **Add custom connector**).
2. Enter:
   * **Name**: `Expense Tracker`
   * **URL**: `https://YOUR_SERVER_NAME.fastmcp.app/mcp`
   * **Authentication**: `Always required` *(Detected)*
   * **OAuth client**: `No client ID — register one automatically` *(Detected)*
3. Click **Add Connector** and click **Authorize** in the popup window.

---

### Option 2: Claude Desktop (Local / Remote JSON Config)
1. Open your Claude Desktop config file:
   * **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   * **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Add your server configuration:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "url": "https://YOUR_SERVER_NAME.fastmcp.app/mcp",
      "headers": {
        "Authorization": "Bearer et_YOUR_API_KEY_HERE"
      }
    }
  }
}
```
3. Restart **Claude Desktop**. You will now see the 🔨 tool hammer icon!

---

## 💬 Copy-and-Paste Test Prompts

Once connected in Claude, try these prompts:

1. **Add Expenses**:
   > *"I just spent $32.50 at Trader Joe's on groceries and $4.75 for a coffee today. Please record both under Food."*

2. **List & Filter**:
   > *"Show me all my expenses recorded under the Food category."*

3. **Spending Summary**:
   > *"How much have I spent in total this month? Show me a category breakdown."*

4. **Update Records**:
   > *"Update my Trader Joe's expense amount from $32.50 to $30.00."*

5. **Monthly Report Prompt**:
   > *"Run my monthly expense report and provide 3 practical tips on how I can reduce my spending next month."*

6. **Delete Records**:
   > *"Delete the coffee expense for $4.75."*

---

## 🛠️ Tools & Prompts Reference

| Tool / Prompt | Arguments | Description |
| :--- | :--- | :--- |
| `add_expense` | `amount`, `category`, `description?`, `expense_date?` | Adds a new expense record for the user. |
| `list_expenses` | `category?`, `start_date?`, `end_date?`, `limit?` | Lists past expenses with optional filters. |
| `update_expense` | `expense_id`, `amount?`, `category?`, `description?`, `expense_date?` | Updates one or more fields of an existing expense. |
| `delete_expense` | `expense_id` | Permanently deletes an expense. |
| `get_summary` | `period` (`'week'`, `'month'`, `'year'`, `'all'`) | Calculates totals, transaction counts, and category breakdowns. |
| `list_categories` | *(none)* | Returns a list of all distinct categories used so far. |
| `monthly_report_prompt` | *(none)* | Built-in prompt template for monthly financial insights. |

---

## ❓ Troubleshooting & FAQs

#### Q: I get `invalid connection option` error when connecting to the database.
* **Fix**: Ensure your `DATABASE_URL` does NOT contain surrounding quotation marks `""` or unsupported parameters like `channel_binding=require`. The URL format should strictly be:
  `postgresql://username:password@hostname/database?sslmode=require`

#### Q: I see `fastmcp is not included in your dependencies` during cloud deployment.
* **Fix**: Ensure `fastmcp>=2.0.0` is present in `requirements.txt` and pushed to your GitHub `main` branch.

#### Q: How do I share this with family or colleagues while keeping data private?
* **Fix**: Run `python create_user.py "Person Name"` for each person. Give each person their own `api_key` (`et_...`). Each user will only ever see and manage their own expenses!

---

## 📄 License
This project is open-source and licensed under the **MIT License**.
