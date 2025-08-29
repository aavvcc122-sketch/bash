
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  role TEXT NOT NULL DEFAULT 'buyer', -- buyer | seller | admin
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS countries (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  price_cents INTEGER NOT NULL DEFAULT 0,  -- price * 100
  capacity INTEGER NOT NULL DEFAULT 0,
  confirm_minutes INTEGER NOT NULL DEFAULT 30,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seller_id INTEGER NOT NULL,
  country_code TEXT NOT NULL,
  file_path TEXT NOT NULL,
  original_name TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  used INTEGER NOT NULL DEFAULT 0, -- 0 unused, 1 delivered/used
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buyer_id INTEGER NOT NULL,
  seller_id INTEGER,
  country_code TEXT NOT NULL,
  status TEXT NOT NULL,  -- pending | delivered | released | canceled
  created_at INTEGER NOT NULL,
  delivered_at INTEGER,
  confirm_after INTEGER
);

CREATE TABLE IF NOT EXISTS balances (
  user_id INTEGER PRIMARY KEY,
  cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  amount_cents INTEGER NOT NULL,
  status TEXT NOT NULL,   -- requested | approved | rejected | paid
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_uploads (
  user_id INTEGER PRIMARY KEY,
  country_code TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
