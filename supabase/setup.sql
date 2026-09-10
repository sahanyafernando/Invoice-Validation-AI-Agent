-- Invoice Validation AI Agent - Supabase setup
-- Run in Supabase Dashboard -> SQL Editor -> New query -> Run.
-- Safe to run repeatedly.

create table if not exists public.suppliers (
  id bigserial primary key,
  name varchar(200) not null unique,
  code varchar(60) unique
);
create index if not exists ix_suppliers_name on public.suppliers(name);

create table if not exists public.purchase_orders (
  id bigserial primary key,
  po_number varchar(80) not null unique,
  supplier_id bigint not null references public.suppliers(id),
  currency varchar(10) not null default 'USD',
  status varchar(30) not null default 'OPEN',
  created_at timestamp without time zone not null default now()
);
create index if not exists ix_purchase_orders_po_number on public.purchase_orders(po_number);

create table if not exists public.po_items (
  id bigserial primary key,
  purchase_order_id bigint not null references public.purchase_orders(id) on delete cascade,
  sku varchar(80),
  description varchar(300) not null,
  quantity double precision not null,
  unit_price double precision not null
);

create table if not exists public.invoices (
  id bigserial primary key,
  invoice_number varchar(100) not null,
  po_number varchar(80),
  supplier_name varchar(200) not null,
  invoice_date date,
  currency varchar(10) not null default 'USD',
  subtotal double precision not null default 0,
  tax double precision not null default 0,
  total double precision not null default 0,
  file_path varchar(500) not null,
  original_filename varchar(250) not null,
  extracted_text text not null default '',
  raw_extraction json not null default '{}'::json,
  extraction_provider varchar(40) not null default 'mock',
  status varchar(40) not null default 'PROCESSING',
  risk_score integer not null default 0,
  risk_level varchar(20) not null default 'LOW',
  explanation text not null default '',
  recommendation text not null default '',
  created_at timestamp without time zone not null default now()
);
create index if not exists ix_invoices_invoice_number on public.invoices(invoice_number);
create index if not exists ix_invoices_po_number on public.invoices(po_number);
create index if not exists ix_invoices_status on public.invoices(status);

create table if not exists public.invoice_items (
  id bigserial primary key,
  invoice_id bigint not null references public.invoices(id) on delete cascade,
  sku varchar(80),
  description varchar(300) not null,
  quantity double precision not null,
  unit_price double precision not null,
  line_total double precision not null
);

create table if not exists public.validation_results (
  id bigserial primary key,
  invoice_id bigint not null references public.invoices(id) on delete cascade,
  rule_code varchar(80) not null,
  passed boolean not null,
  severity varchar(20) not null,
  expected_value varchar(300),
  actual_value varchar(300),
  difference double precision,
  message text not null
);

create table if not exists public.audit_logs (
  id bigserial primary key,
  invoice_id bigint references public.invoices(id),
  actor varchar(120) not null default 'system',
  action varchar(80) not null,
  previous_status varchar(40),
  new_status varchar(40),
  note text,
  created_at timestamp without time zone not null default now()
);

-- Private bucket for original invoice PDFs/images.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'invoices',
  'invoices',
  false,
  12582912,
  array['application/pdf','image/png','image/jpeg']
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- This project deliberately performs Storage operations only in FastAPI with
-- the service-role key. Do NOT expose that key in Next.js. Because the bucket
-- is private, public anonymous users cannot download invoice documents.
