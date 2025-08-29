
import os, sqlite3, time
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./market.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema_path = Path(__file__).with_name("schema.sql")
    with connect() as con, open(schema_path, "r", encoding="utf-8") as f:
        con.executescript(f.read())

def now_ts():
    return int(time.time())

# Users
def upsert_user(user_id: int, role: str = "buyer"):
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO users (id, role, created_at) VALUES (?, ?, ?)",
                    (user_id, role, now_ts()))
        # keep existing role if present

def set_role(user_id: int, role: str):
    with connect() as con:
        con.execute("INSERT INTO users (id, role, created_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET role=excluded.role",
                    (user_id, role, now_ts()))

def get_role(user_id: int) -> str:
    with connect() as con:
        cur = con.execute("SELECT role FROM users WHERE id=?", (user_id,))
        r = cur.fetchone()
        return r["role"] if r else "buyer"

# Countries
def add_country(code: str, name: str, price_cents: int, capacity: int, confirm_minutes: int):
    with connect() as con:
        con.execute("INSERT OR REPLACE INTO countries (code, name, price_cents, capacity, confirm_minutes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (code.upper(), name, price_cents, capacity, confirm_minutes, now_ts()))

def list_countries():
    with connect() as con:
        cur = con.execute("SELECT * FROM countries ORDER BY code")
        return cur.fetchall()

def get_country(code: str):
    with connect() as con:
        cur = con.execute("SELECT * FROM countries WHERE code=?", (code.upper(),))
        return cur.fetchone()

def set_price(code: str, price_cents: int):
    with connect() as con:
        con.execute("UPDATE countries SET price_cents=? WHERE code=?", (price_cents, code.upper()))

def set_capacity(code: str, capacity: int):
    with connect() as con:
        con.execute("UPDATE countries SET capacity=? WHERE code=?", (capacity, code.upper()))

def set_confirm_minutes(code: str, minutes: int):
    with connect() as con:
        con.execute("UPDATE countries SET confirm_minutes=? WHERE code=?", (minutes, code.upper()))

# Inventory
def add_inventory(seller_id: int, country_code: str, file_path: str, original_name: str, file_size: int):
    with connect() as con:
        con.execute("""INSERT INTO inventory (seller_id, country_code, file_path, original_name, file_size, used, created_at)
                       VALUES (?, ?, ?, ?, ?, 0, ?)""",
                    (seller_id, country_code.upper(), file_path, original_name, file_size, now_ts()))

def get_available_inventory(country_code: str):
    with connect() as con:
        cur = con.execute("""SELECT * FROM inventory
                             WHERE country_code=? AND used=0
                             ORDER BY created_at ASC""", (country_code.upper(),))
        return cur.fetchall()

def mark_inventory_used(inv_id: int):
    with connect() as con:
        con.execute("UPDATE inventory SET used=1 WHERE id=?", (inv_id,))

# Pending uploads
def set_pending_upload(user_id: int, code: str):
    with connect() as con:
        con.execute("INSERT OR REPLACE INTO pending_uploads (user_id, country_code, created_at) VALUES (?, ?, ?)",
                    (user_id, code.upper(), now_ts()))

def pop_pending_upload(user_id: int):
    with connect() as con:
        cur = con.execute("SELECT country_code FROM pending_uploads WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        con.execute("DELETE FROM pending_uploads WHERE user_id=?", (user_id,))
        return r["country_code"] if r else None

# Orders
def create_order(buyer_id: int, country_code: str):
    with connect() as con:
        con.execute("""INSERT INTO orders (buyer_id, country_code, status, created_at)
                       VALUES (?, ?, 'pending', ?)""", (buyer_id, country_code.upper(), now_ts()))
        cur = con.execute("SELECT last_insert_rowid() AS id")
        return cur.fetchone()["id"]

def get_order(order_id: int):
    with connect() as con:
        cur = con.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        return cur.fetchone()

def list_orders(limit: int = 20):
    with connect() as con:
        cur = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()

def set_order_delivered(order_id: int, seller_id: int, confirm_after_ts: int):
    with connect() as con:
        con.execute("""UPDATE orders
                       SET status='delivered', seller_id=?, delivered_at=?, confirm_after=?
                       WHERE id=?""",
                    (seller_id, now_ts(), confirm_after_ts, order_id))

def release_order(order_id: int):
    with connect() as con:
        con.execute("UPDATE orders SET status='released' WHERE id=?", (order_id,))

# Balances
def get_balance(user_id: int) -> int:
    with connect() as con:
        cur = con.execute("SELECT cents FROM balances WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        return r["cents"] if r else 0

def add_balance(user_id: int, cents: int):
    with connect() as con:
        con.execute("""INSERT INTO balances (user_id, cents) VALUES (?, ?)
                       ON CONFLICT(user_id) DO UPDATE SET cents=balances.cents + excluded.cents""",
                    (user_id, cents))

# Payouts
def request_payout(user_id: int, amount_cents: int):
    with connect() as con:
        con.execute("INSERT INTO payouts (user_id, amount_cents, status, created_at) VALUES (?, ?, 'requested', ?)",
                    (user_id, amount_cents, now_ts()))

# Escrow sweep
def due_releases(now_ts_int: int):
    with connect() as con:
        cur = con.execute("""SELECT * FROM orders
                             WHERE status='delivered' AND confirm_after IS NOT NULL AND confirm_after <= ?""",
                          (now_ts_int,))
        return cur.fetchall()
