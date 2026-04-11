import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

STATES = ["CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
STATUSES = ["ACTIVE", "EXPIRED", "PENDING", "CANCELLED"]
CATEGORIES = ["rate_config", "product_rules", "workflow", "validation", "pricing"]

# ── Create tables ─────────────────────────────────────────────────
def create_tables(conn):
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS policy_data (
            policy_id       INTEGER PRIMARY KEY,
            state           TEXT,
            premium_amount  REAL,
            status          TEXT,
            created_date    TEXT,
            end_date        TEXT,
            product_id      INTEGER,
            data            TEXT
        );

        CREATE TABLE IF NOT EXISTS claims_data (
            claim_id        INTEGER PRIMARY KEY,
            policy_id       INTEGER,
            claim_amount    REAL,
            claim_date      TEXT,
            status          TEXT
        );

        CREATE TABLE IF NOT EXISTS config_table (
            id              INTEGER PRIMARY KEY,
            key             TEXT,
            value           TEXT,
            category        TEXT
        );

        CREATE TABLE IF NOT EXISTS knowledge_base (
            id              INTEGER PRIMARY KEY,
            category        TEXT,
            key             TEXT,
            value           TEXT
        );

        CREATE TABLE IF NOT EXISTS system_logs (
            log_id          INTEGER PRIMARY KEY,
            created_date    TEXT,
            event_type      TEXT,
            policy_id       INTEGER,
            message         TEXT
        );
    """)
    conn.commit()
    print("Tables created.")

# ── Seed data ─────────────────────────────────────────────────────
def seed_data(conn):
    cursor = conn.cursor()

    count = cursor.execute("SELECT COUNT(*) FROM policy_data").fetchone()[0]
    if count > 0:
        print(f"Database already seeded with {count} policies. Skipping.")
        return

    print("Seeding database... this takes 3-5 minutes for 1M rows.")
    base_date = datetime(2020, 1, 1)

    # ── policy_data — 1,000,000 rows ──────────────────────────────
    print("  Seeding policy_data (1,000,000 rows)...")
    policies = []
    for i in range(1, 1000001):
        state = random.choice(STATES)
        status = random.choice(STATUSES)
        created = base_date + timedelta(days=random.randint(0, 1460))
        end = created + timedelta(days=random.randint(180, 730))
        premium = round(random.uniform(500, 5000), 2)
        product_id = random.randint(1, 20)
        data = f'{{"policy": {{"state": "{state}", "premium": {premium}, "status": "{status}"}}}}'
        policies.append((i, state, premium, status, created.strftime("%Y-%m-%d"),
                        end.strftime("%Y-%m-%d"), product_id, data))

        if i % 100000 == 0:
            cursor.executemany("INSERT INTO policy_data VALUES (?,?,?,?,?,?,?,?)", policies)
            conn.commit()
            policies = []
            print(f"    policy_data: {i}/1000000")

    if policies:
        cursor.executemany("INSERT INTO policy_data VALUES (?,?,?,?,?,?,?,?)", policies)
        conn.commit()
    print("  policy_data done.")

    # ── claims_data — 200,000 rows ────────────────────────────────
    print("  Seeding claims_data (200,000 rows)...")
    claims = []
    for i in range(1, 200001):
        policy_id = random.randint(1, 1000000)
        claim_amount = round(random.uniform(100, 50000), 2)
        claim_date = base_date + timedelta(days=random.randint(0, 1460))
        status = random.choice(["OPEN", "CLOSED", "PENDING", "DENIED"])
        claims.append((i, policy_id, claim_amount, claim_date.strftime("%Y-%m-%d"), status))

        if i % 50000 == 0:
            cursor.executemany("INSERT INTO claims_data VALUES (?,?,?,?,?)", claims)
            conn.commit()
            claims = []
            print(f"    claims_data: {i}/200000")

    if claims:
        cursor.executemany("INSERT INTO claims_data VALUES (?,?,?,?,?)", claims)
        conn.commit()
    print("  claims_data done.")

    # ── config_table — 1,000 rows ─────────────────────────────────
    print("  Seeding config_table (1,000 rows)...")
    configs = []
    for i in range(1, 1001):
        category = random.choice(CATEGORIES)
        key = f"{category}_key_{i}"
        value = f"value_{random.randint(1, 9999)}"
        configs.append((i, key, value, category))
    cursor.executemany("INSERT INTO config_table VALUES (?,?,?,?)", configs)
    conn.commit()
    print("  config_table done.")

    # ── knowledge_base — 500 rows ─────────────────────────────────
    print("  Seeding knowledge_base (500 rows)...")
    kb = []
    for i in range(1, 501):
        category = random.choice(CATEGORIES)
        key = f"kb_{category}_{i}"
        value = f"rule_{random.randint(1, 999)}"
        kb.append((i, category, key, value))
    cursor.executemany("INSERT INTO knowledge_base VALUES (?,?,?,?)", kb)
    conn.commit()
    print("  knowledge_base done.")

    # ── system_logs — 500,000 rows ────────────────────────────────
    print("  Seeding system_logs (500,000 rows)...")
    logs = []
    event_types = ["POLICY_CREATED", "POLICY_UPDATED", "CLAIM_FILED",
                   "PAYMENT_PROCESSED", "STATUS_CHANGED"]
    for i in range(1, 500001):
        created = base_date + timedelta(days=random.randint(0, 1460))
        event = random.choice(event_types)
        policy_id = random.randint(1, 1000000)
        logs.append((i, created.strftime("%Y-%m-%d"), event, policy_id,
                    f"Event {event} for policy {policy_id}"))

        if i % 50000 == 0:
            cursor.executemany("INSERT INTO system_logs VALUES (?,?,?,?,?)", logs)
            conn.commit()
            logs = []
            print(f"    system_logs: {i}/500000")

    if logs:
        cursor.executemany("INSERT INTO system_logs VALUES (?,?,?,?,?)", logs)
        conn.commit()
    print("  system_logs done.")

    print("Database seeding complete! 🎉")
    print(f"  policy_data:  1,000,000 rows")
    print(f"  claims_data:    200,000 rows")
    print(f"  config_table:     1,000 rows")
    print(f"  knowledge_base:     500 rows")
    print(f"  system_logs:    500,000 rows")

# ── Drop all indexes (for demo reset) ────────────────────────────
def drop_indexes(conn):
    cursor = conn.cursor()
    indexes = cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
    """).fetchall()
    for (name,) in indexes:
        cursor.execute(f"DROP INDEX IF EXISTS {name}")
    conn.commit()
    print(f"Dropped {len(indexes)} demo indexes.")

# ── Initialize everything ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    seed_data(conn)
    conn.close()
    print(f"Database ready at {DB_PATH}")

# ── Get connection ────────────────────────────────────────────────
def get_connection():
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_db()