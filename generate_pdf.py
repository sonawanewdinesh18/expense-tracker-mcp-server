"""
generate_pdf.py
---------------
Generates a comprehensive, beautifully styled PDF guide for the Expense Tracker MCP Server project.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
    HRFlowable,
)

PDF_FILENAME = "Expense_Tracker_MCP_Complete_Guide.pdf"


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_FILENAME,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563eb"),
        fontName="Helvetica-Bold",
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        fontName="Helvetica",
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontSize=8,
        leading=10.5,
        fontName="Courier",
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("💰 Expense Tracker MCP Server", title_style))
    story.append(
        Paragraph(
            "<b>Complete Learning & Implementation Guide</b> | FastMCP, Neon PostgreSQL, Cloud Deployment, and uv vs pip",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

    # Section 1: Overview
    story.append(Paragraph("1. Project Overview & Architecture", h1_style))
    story.append(
        Paragraph(
            "This project implements a multi-user <b>Model Context Protocol (MCP)</b> server that connects AI clients (like Claude Desktop and Claude.ai) to a serverless <b>Neon PostgreSQL</b> database. It provides full expense management capabilities with strict user data privacy.",
            body_style,
        )
    )

    arch_box = [
        ["AI Client (Claude / Agent)", "→", "FastMCP Server (server.py)", "→", "Neon PostgreSQL (db.py)"],
        [
            "Prompts & Tool Calls\n(Bearer Auth Header)",
            "",
            "Resolves user identity\nValidates arguments",
            "",
            "Stores api_keys & expenses\nEnforces tenant scoping",
        ],
    ]
    t_arch = Table(arch_box, colWidths=[160, 20, 170, 20, 170])
    t_arch.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_arch)
    story.append(Spacer(1, 8))

    # Section 2: PostgreSQL Schema
    story.append(Paragraph("2. Neon PostgreSQL Database Schema", h1_style))
    story.append(
        Paragraph(
            "The database uses PostgreSQL with <code>pgcrypto</code> for UUID generation. Execute this SQL in your Neon Console SQL Editor:",
            body_style,
        )
    )

    sql_code = """CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys (api_key);"""

    t_sql = Table([[Preformatted(sql_code, code_style)]], colWidths=[540])
    t_sql.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_sql)
    story.append(Spacer(1, 8))

    # Section 3: Step-by-Step Setup
    story.append(Paragraph("3. Step-by-Step Local Setup Guide", h1_style))

    steps_text = [
        "<b>Step 1: Clone & Navigate:</b><br/><code>git clone https://github.com/sonawanewdinesh18/expense-tracker-mcp-server.git</code>",
        "<b>Step 2: Create Environment & Install:</b><br/><code>python -m venv .venv</code> &nbsp;|&nbsp; <code>.venv\\Scripts\\Activate.ps1</code> &nbsp;|&nbsp; <code>pip install -r requirements.txt</code>",
        "<b>Step 3: Set Environment Variables in .env:</b><br/><code>DATABASE_URL=postgresql://user:pass@ep-xyz.aws.neon.tech/neondb?sslmode=require</code><br/><i>(Ensure no surrounding quotation marks!)</i>",
        "<b>Step 4: Create Your User API Key:</b><br/><code>python create_user.py \"Your Name\"</code> &nbsp;→ Prints your unique <code>user_id</code> and <code>api_key</code> (e.g. <code>et_...</code>).",
    ]
    for s in steps_text:
        story.append(Paragraph(f"• {s}", body_style))

    story.append(Spacer(1, 6))

    # Section 4: uv vs pip Deep Dive
    story.append(Paragraph("4. Deep Dive: 'uv' vs Traditional 'pip'", h1_style))
    story.append(
        Paragraph(
            "<b>What is uv?</b> <code>uv</code> is an ultra-fast Python package and project manager developed by Astral (written in Rust). FastMCP tutorials frequently reference <code>uv</code> because it eliminates manual virtual environment activation and installs packages 10-100x faster.",
            body_style,
        )
    )

    uv_table_data = [
        ["Workflow Task", "Standard pip / venv", "Modern uv Way ⚡"],
        ["Create Virtual Env", "python -m venv .venv\n.venv\\Scripts\\Activate.ps1", "Automatic (handled by uv)"],
        ["Install Dependencies", "pip install -r requirements.txt", "uv add fastmcp \"psycopg[binary]\""],
        ["Run Server", "python server.py", "uv run server.py"],
        ["Run FastMCP Inspector", "mcp dev server.py", "uv run mcp dev server.py"],
        ["Create User", "python create_user.py \"Alice\"", "uv run create_user.py \"Alice\""],
    ]
    t_uv = Table(uv_table_data, colWidths=[130, 200, 210])
    t_uv.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_uv)
    story.append(Spacer(1, 8))

    # Section 5: Cloud Deployment
    story.append(Paragraph("5. Cloud Deployment (FastMCP Cloud / Prefect Horizon)", h1_style))
    deploy_steps = [
        "<b>1. Push Repository:</b> Push your code to GitHub (branch <code>main</code>).",
        "<b>2. Connect Horizon:</b> Log in to <b>horizon.prefect.io</b> and select your repository.",
        "<b>3. Entrypoint:</b> Set Server Entrypoint to <code>server.py:mcp</code>.",
        "<b>4. Environment Variables:</b> Set <code>DATABASE_URL</code> to your clean Neon PostgreSQL connection string.",
        "<b>5. Deploy:</b> Your server goes live at <code>https://your-server.fastmcp.app/mcp</code>.",
    ]
    for d in deploy_steps:
        story.append(Paragraph(f"• {d}", body_style))

    story.append(Spacer(1, 6))

    # Section 6: Connecting to Claude
    story.append(Paragraph("6. Connecting to Claude (Claude.ai & Claude Desktop)", h1_style))
    story.append(
        Paragraph(
            "<b>Claude.ai Custom Connectors:</b> Add custom connector ➡️ Enter URL <code>https://your-server.fastmcp.app/mcp</code> ➡️ Select <i>Always required</i> & <i>No client ID (automatic)</i> ➡️ Authorize popup.<br/>"
            "<b>Claude Desktop:</b> Add to <code>claude_desktop_config.json</code> under <code>mcpServers</code> with your server URL and Authorization header.",
            body_style,
        )
    )

    story.append(Spacer(1, 6))

    # Section 7: Testing Prompts
    story.append(Paragraph("7. Ready-to-Use Test Prompts for Claude", h1_style))
    prompts = [
        ("Add Expense", "I spent $45.50 on groceries and $12.00 for lunch today. Record both under Food."),
        ("List & Filter", "Show me a list of all expenses recorded under the Food category."),
        ("Summary", "How much have I spent so far this month? Give me a breakdown of totals by category."),
        ("Update", "Change my lunch expense amount from $12.00 to $15.50."),
        ("Monthly Report", "Run my monthly expense report and give me 3 practical tips to optimize my spending next month."),
    ]
    p_table_data = [["Goal", "Prompt to send to Claude"]]
    for g, p in prompts:
        p_table_data.append([g, p])

    t_p = Table(p_table_data, colWidths=[110, 430])
    t_p.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_p)

    doc.build(story)
    print(f"PDF successfully generated: {PDF_FILENAME}")


if __name__ == "__main__":
    build_pdf()
