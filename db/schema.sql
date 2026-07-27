-- Supabase schema.
--
-- Two independent things live here:
--   1. email_subscribers — the digest list. Committed so the privacy claims in
--      PRIVACY.md are checkable rather than something you take on trust.
--   2. companies / jobs / scrape_runs — the optional Postgres mirror written by
--      src/intern_engine/db.py. These MUST match what `db.sync` actually writes;
--      a schema that merely looks reasonable makes the mirror fail silently.
--
-- Apply with:  supabase db execute --file db/schema.sql
-- (or paste into the Supabase SQL editor).

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Email subscribers
-- ---------------------------------------------------------------------------
-- Security model in one line: the anon key may INSERT a subscription and
-- nothing else. It cannot read the list, update it, or delete from it.
-- Unsubscribing goes through a security-definer function whose only credential
-- is a per-subscriber secret token.

create table if not exists public.email_subscribers (
    id           uuid primary key default gen_random_uuid(),
    email        text        not null unique,
    -- The secret in the unsubscribe URL. Random per subscriber, so knowing one
    -- tells you nothing about any other.
    unsub_token  text        not null unique default encode(gen_random_bytes(24), 'hex'),
    created_at   timestamptz not null default now()
);

alter table public.email_subscribers
    drop constraint if exists email_shape;
alter table public.email_subscribers
    add constraint email_shape check (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$');

alter table public.email_subscribers enable row level security;

-- INSERT only. Note there is deliberately NO select/update/delete policy for
-- anon or authenticated: with RLS on, absent policy = denied. The digest sender
-- reads the list with the service key, which bypasses RLS.
drop policy if exists "anon can subscribe" on public.email_subscribers;
create policy "anon can subscribe"
    on public.email_subscribers
    for insert
    to anon, authenticated
    with check (true);

revoke all on public.email_subscribers from anon, authenticated;
grant insert on public.email_subscribers to anon, authenticated;

create or replace function public.unsubscribe_email(token text)
returns void
language sql
security definer
set search_path = public
as $$
    delete from public.email_subscribers where unsub_token = token;
$$;

revoke all on function public.unsubscribe_email(text) from public;
grant execute on function public.unsubscribe_email(text) to anon, authenticated;

-- ---------------------------------------------------------------------------
-- Run mirror (optional; service key only)
-- ---------------------------------------------------------------------------
-- Written by db.sync when SUPABASE_URL + SUPABASE_SERVICE_KEY are set. Column
-- names and the upsert conflict targets below are load-bearing — they have to
-- match db.py exactly.

create table if not exists public.companies (
    key   text primary key,          -- "<ats>:<slug>", db.py's on_conflict
    ats   text not null,
    slug  text not null,
    name  text
);

create table if not exists public.jobs (
    id               text primary key,   -- db.py's on_conflict
    company_key      text references public.companies(key) on delete set null,
    source           text,
    company          text,
    title            text,
    location         text,
    url              text,
    category         text,
    season           text,
    -- Cycles the employer stated, when a posting names more than one.
    seasons          text[],
    -- False = the employer named the cycle; true = we inferred it from the
    -- posting date. The single most important qualifier on this table.
    season_inferred  boolean,
    region           text,
    sponsorship      text,
    salary           text,
    skills           text[],
    posted_at        timestamptz,
    -- exact | date_only | relative_derived — how much the date above is worth.
    posted_at_source text,
    first_seen_at    timestamptz,
    last_seen_at     timestamptz,
    closed_at        timestamptz,
    -- gone-from-feed | out-of-scope
    closed_reason    text,
    is_open          boolean
);

-- Migration for projects created before these columns existed. `create table
-- if not exists` above is a no-op on an existing table, so without this an
-- older database silently keeps rejecting every write db.py makes (the sync
-- swallows its own errors, so the mirror just quietly stops updating).
-- Safe to re-run: each add is itself `if not exists`.
alter table public.jobs add column if not exists seasons          text[];
alter table public.jobs add column if not exists season_inferred  boolean;
alter table public.jobs add column if not exists salary           text;
alter table public.jobs add column if not exists skills           text[];
alter table public.jobs add column if not exists posted_at_source text;
alter table public.jobs add column if not exists closed_at        timestamptz;
alter table public.jobs add column if not exists closed_reason    text;
alter table public.jobs add column if not exists company_key      text;
alter table public.jobs add column if not exists region           text;

create index if not exists jobs_open_idx on public.jobs (is_open, posted_at desc);
create index if not exists jobs_company_idx on public.jobs (company_key);

create table if not exists public.scrape_runs (
    id                uuid primary key default gen_random_uuid(),
    created_at        timestamptz not null default now(),
    duration_seconds  numeric,
    companies_total   integer,
    fetched_ok        integer,
    fetch_errors      integer,
    fetch_success_rate numeric,
    roles_matched     integer,
    new_this_run      integer,
    open_total        integer,
    roles_by_source   jsonb,
    roles_by_cycle    jsonb,
    roles_by_region   jsonb,
    detection_latency jsonb
);

-- Service-key only: RLS on with no policies means the anon key can't read or
-- write any of these.
alter table public.companies   enable row level security;
alter table public.jobs        enable row level security;
alter table public.scrape_runs enable row level security;
