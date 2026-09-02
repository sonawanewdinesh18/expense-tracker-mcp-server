-- ============================================================
-- Expense Tracker MCP -- Supabase schema
-- Run this once in Supabase: Dashboard -> SQL Editor -> New query
-- ============================================================

create extension if not exists pgcrypto;  -- for gen_random_uuid()

-- One row per issued API key. user_id is the value that scopes
-- every expense to a single person.
create table if not exists api_keys (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default gen_random_uuid(),
    api_key     text not null unique,
    label       text,                       -- e.g. "Alice's laptop"
    created_at  timestamptz not null default now(),
    revoked     boolean not null default false
);

create table if not exists expenses (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null,
    amount        numeric(12,2) not null check (amount > 0),
    category      text not null,
    description   text default '',
    expense_date  date not null default current_date,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

-- Speeds up the exact queries this server actually runs.
create index if not exists idx_expenses_user_date
    on expenses (user_id, expense_date desc);

create index if not exists idx_expenses_user_category
    on expenses (user_id, category);

create index if not exists idx_api_keys_key
    on api_keys (api_key);

-- ------------------------------------------------------------
-- Row Level Security: defense in depth.
--
-- The server connects with the SERVICE ROLE key, which bypasses RLS
-- by design, and the server's own code (db.py) already filters every
-- query by user_id. Enabling RLS here with NO permissive policies
-- means that even if a client ever mistakenly connected with the
-- public "anon" key instead, it would see and change nothing.
-- ------------------------------------------------------------
alter table expenses enable row level security;
alter table api_keys enable row level security;
-- (No policies are added on purpose -- anon/authenticated roles get
--  zero access; only the service_role key, used by this server, can
--  read or write these tables.)
