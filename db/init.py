from .connection import get_conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        income REAL,
        expenses REAL,
        missed_payments INTEGER,
        credit_utilization REAL,
        loan_amount REAL,
        loan_type TEXT,
        email TEXT,
        phone TEXT,
        added_on TEXT,
        risk_score REAL,
        risk_category TEXT
    )
    """)

    conn.commit()
    conn.close()