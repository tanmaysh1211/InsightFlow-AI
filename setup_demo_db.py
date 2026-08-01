import sqlite3
import datetime
import random

def setup_db():
    db_path = "enterprise_demo.db"
    print(f"Setting up demo database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS payments;")
    cursor.execute("DROP TABLE IF EXISTS orders;")
    cursor.execute("DROP TABLE IF EXISTS inventory;")
    cursor.execute("DROP TABLE IF EXISTS products;")
    cursor.execute("DROP TABLE IF EXISTS customers;")

    cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        country TEXT NOT NULL,
        segment TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        cost REAL NOT NULL,
        stock INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        payment_date TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        supplier TEXT NOT NULL,
        last_restocked TEXT NOT NULL,
        safety_stock INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    customers_data = [
        ("Acme Corp", "info@acme.com", "USA", "Enterprise", "2025-01-15"),
        ("Globex Corporation", "billing@globex.com", "Canada", "Enterprise", "2025-02-10"),
        ("Initech", "contact@initech.com", "USA", "Mid-Market", "2025-03-01"),
        ("Umbrella Corp", "orders@umbrella.com", "UK", "Enterprise", "2025-03-12"),
        ("Hooli", "support@hooli.com", "USA", "Enterprise", "2025-04-20"),
        ("Soylent Corp", "sales@soylent.com", "Germany", "Mid-Market", "2025-05-02"),
        ("Vehement Capital", "invest@vehement.com", "France", "SMB", "2025-06-15"),
        ("Massive Dynamic", "admin@massivedynamic.com", "USA", "Enterprise", "2025-07-01"),
        ("Tyrell Corp", "replicant@tyrell.com", "Japan", "Enterprise", "2025-07-22"),
        ("Cyberdyne Systems", "help@cyberdyne.com", "USA", "SMB", "2025-08-05")
    ]
    cursor.executemany(
        "INSERT INTO customers (name, email, country, segment, created_at) VALUES (?, ?, ?, ?, ?);",
        customers_data
    )

    products_data = [
        ("Enterprise Server S1", "Hardware", 1200.00, 800.00, 45, "2025-01-10"),
        ("Developer Laptop Pro", "Hardware", 2500.00, 1800.00, 25, "2025-01-10"),
        ("AI Analytics Suite v1", "Software", 5000.00, 500.00, 999, "2025-02-01"),
        ("Cloud Database Host", "SaaS", 150.00, 30.00, 9999, "2025-02-01"),
        ("Office Ergonomic Chair", "Furniture", 450.00, 200.00, 15, "2025-03-05"),
        ("Standing Desk Premium", "Furniture", 850.00, 400.00, 10, "2025-03-05"),
        ("Cybersecurity Firewall", "Software", 3200.00, 1200.00, 30, "2025-04-12"),
        ("Conference Display 4K", "Hardware", 1800.00, 1100.00, 8, "2025-05-18"),
        ("Enterprise Support Pack", "Services", 1000.00, 400.00, 9999, "2025-06-01"),
        ("AI Consulting Workshop", "Services", 3500.00, 1500.00, 9999, "2025-06-15")
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price, cost, stock, created_at) VALUES (?, ?, ?, ?, ?, ?);",
        products_data
    )

    inventory_data = [
        (1, "TechDistributors Inc", "2025-12-01", 10),
        (2, "TechDistributors Inc", "2025-12-01", 5),
        (5, "OfficeDesign Co", "2025-11-15", 4),
        (6, "OfficeDesign Co", "2025-11-15", 3),
        (8, "ScreenCo International", "2025-10-20", 2)
    ]
    cursor.executemany(
        "INSERT INTO inventory (product_id, supplier, last_restocked, safety_stock) VALUES (?, ?, ?, ?);",
        inventory_data
    )

    order_dates = [
        "2025-08-10", "2025-08-15", "2025-09-02", "2025-09-18", "2025-09-29",
        "2025-10-05", "2025-10-12", "2025-10-22", "2025-11-04", "2025-11-15",
        "2025-11-28", "2025-12-02", "2025-12-10", "2025-12-25", "2026-01-05",
        "2026-01-18", "2026-02-02", "2026-02-14", "2026-02-28", "2026-03-05",
        "2026-03-19", "2026-03-31", "2026-04-10", "2026-04-22", "2026-05-02"
    ]

    order_statuses = ["Completed", "Completed", "Completed", "Pending", "Cancelled"]

    random.seed(42)  
    for i, date_str in enumerate(order_dates):
        customer_id = random.randint(1, 10)
        product_id = random.randint(1, 10)
        quantity = random.randint(1, 5)
        
        cursor.execute("SELECT price FROM products WHERE id = ?", (product_id,))
        price = cursor.fetchone()[0]
        total_amount = price * quantity
        status = random.choice(order_statuses) if date_str != order_dates[-1] else "Completed"
        
        cursor.execute(
            "INSERT INTO orders (customer_id, product_id, order_date, quantity, total_amount, status) VALUES (?, ?, ?, ?, ?, ?);",
            (customer_id, product_id, date_str, quantity, total_amount, status)
        )
        order_id = cursor.lastrowid

        if status == "Completed":
            payment_method = random.choice(["Credit Card", "Bank Transfer", "ACH"])
            cursor.execute(
                "INSERT INTO payments (order_id, payment_date, payment_method, amount) VALUES (?, ?, ?, ?);",
                (order_id, date_str, payment_method, total_amount)
            )

    conn.commit()
    conn.close()
    print("Database setup complete.")
    
    import os
    import shutil
    if os.path.exists("backend"):
        shutil.copy2(db_path, os.path.join("backend", db_path))
        print("Demo database copied to backend directory.")

if __name__ == "__main__":
    setup_db()
