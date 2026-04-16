"""
database/schema.py
SQLite schema — customers, orders, order_items, returns, refunds.
"""
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "./orders.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cur  = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        email         TEXT NOT NULL,
        phone         TEXT,
        city          TEXT
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id           TEXT PRIMARY KEY,
        customer_id        TEXT NOT NULL,
        status             TEXT NOT NULL,
        payment_method     TEXT,
        payment_status     TEXT,
        subtotal           REAL,
        shipping_charge    REAL,
        discount           REAL,
        total              REAL,
        placed_at          TEXT,
        shipped_at         TEXT,
        estimated_delivery TEXT,
        delivered_at       TEXT,
        tracking_number    TEXT,
        courier            TEXT,
        delivery_address   TEXT,
        notes              TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id    TEXT NOT NULL,
        product     TEXT NOT NULL,
        quantity    INTEGER NOT NULL,
        unit_price  REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );

    CREATE TABLE IF NOT EXISTS returns (
        return_id       TEXT PRIMARY KEY,
        order_id        TEXT NOT NULL,
        customer_id     TEXT NOT NULL,
        reason          TEXT NOT NULL,
        status          TEXT NOT NULL,
        items_returned  TEXT NOT NULL,
        pickup_date     TEXT,
        picked_up_at    TEXT,
        received_at     TEXT,
        inspection_note TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT,
        FOREIGN KEY (order_id)    REFERENCES orders(order_id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS refunds (
        refund_id      TEXT PRIMARY KEY,
        order_id       TEXT NOT NULL,
        return_id      TEXT,
        customer_id    TEXT NOT NULL,
        amount         REAL NOT NULL,
        method         TEXT NOT NULL,
        status         TEXT NOT NULL,
        reason         TEXT,
        initiated_at   TEXT NOT NULL,
        processed_at   TEXT,
        utr_number     TEXT,
        notes          TEXT,
        FOREIGN KEY (order_id)    REFERENCES orders(order_id),
        FOREIGN KEY (return_id)   REFERENCES returns(return_id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """)

    conn.commit()
    conn.close()
