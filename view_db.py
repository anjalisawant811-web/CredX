import sqlite3
from tabulate import tabulate

DB_PATH = "credx.db"


def view_all_customers():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM customers ORDER BY id DESC")
    rows = cur.fetchall()

    if not rows:
        print("\n No data found in customers table.\n")
        return

    # Convert rows to list of dicts
    data = [dict(row) for row in rows]

    print("\n CUSTOMER DATABASE SNAPSHOT\n")
    print(tabulate(data, headers="keys", tablefmt="grid"))

    conn.close()


if __name__ == "__main__":
    view_all_customers()