import sqlite3
from contextlib import closing

DB_NAME    = "database.db"
ADMIN_EMAIL    = "admin@pharmainsight.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_NAME     = "Administrator"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _add_col(c, table, col, definition):
    cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")

def create_tables():
    conn = get_db()
    c = conn.cursor()

    # ── users ────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, phone TEXT,
        password TEXT, is_admin INTEGER DEFAULT 0,
        language TEXT DEFAULT 'en',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    for col,dfn in [("phone","TEXT"),("is_admin","INTEGER DEFAULT 0"),
                    ("language","TEXT DEFAULT 'en'"),
                    ("created_at","DATETIME DEFAULT CURRENT_TIMESTAMP")]:
        _add_col(c,"users",col,dfn)

    # ── search_history ────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, medicine_name TEXT,
        search_type TEXT DEFAULT 'Text Search',
        search_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    for col,dfn in [("search_type","TEXT DEFAULT 'Text Search'"),
                    ("search_time","DATETIME DEFAULT CURRENT_TIMESTAMP")]:
        _add_col(c,"search_history",col,dfn)

    # ── visitors ──────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── contact_messages ──────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, subject TEXT, message TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── FEATURE 1: medicine_interactions ─────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS interaction_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, drug1 TEXT, drug2 TEXT,
        severity TEXT, summary TEXT,
        checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── FEATURE 2: reminders ─────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        dose TEXT, frequency TEXT, reminder_time TEXT,
        start_date TEXT, end_date TEXT,
        active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    # ── FEATURE 4: orders / cart ──────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, items_json TEXT,
        address TEXT, total REAL, payment TEXT,
        status TEXT DEFAULT 'Placed',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── FEATURE 9: reviews ────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        medicine_name TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        review_text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    conn.commit()

    # Seed admin
    if not c.execute("SELECT id FROM users WHERE is_admin=1").fetchone():
        try:
            c.execute(
                "INSERT INTO users (name,email,phone,password,is_admin) VALUES (?,?,?,?,1)",
                (ADMIN_NAME, ADMIN_EMAIL, "+91 0000000000", ADMIN_PASSWORD)
            )
            conn.commit()
        except Exception:
            c.execute("UPDATE users SET is_admin=1 WHERE email=?", (ADMIN_EMAIL,))
            conn.commit()

    conn.close()
    print("All tables ready.")

# ── helpers ───────────────────────────────────────────────

def log_visitor():
    with closing(get_db()) as conn:
        conn.execute("INSERT INTO visitors DEFAULT VALUES")
        conn.commit()

def log_search(user_id, medicine, search_type="Text Search"):
    with closing(get_db()) as conn:
        conn.execute(
            "INSERT INTO search_history (user_id,medicine_name,search_type) VALUES (?,?,?)",
            (user_id, medicine, search_type))
        conn.commit()

def save_contact(name, email, subject, message):
    with closing(get_db()) as conn:
        conn.execute(
            "INSERT INTO contact_messages (name,email,subject,message) VALUES (?,?,?,?)",
            (name, email, subject, message))
        conn.commit()
