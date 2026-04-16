"""
database/seed.py
Seeds all tables with realistic sample data.
Run once: python database/seed.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database.schema import get_connection, create_tables

CUSTOMERS = [
    ("CUST001", "Sushant Sehgal",  "sushant@email.com", "+91 9815510270", "Pune"),
    ("CUST002", "Priya Sharma",    "priya@email.com",   "+91 9876543210", "Mumbai"),
    ("CUST003", "Rahul Verma",     "rahul@email.com",   "+91 9123456789", "Delhi"),
    ("CUST004", "Anjali Mehta",    "anjali@email.com",  "+91 9988776655", "Bangalore"),
    ("CUST005", "Karan Patel",     "karan@email.com",   "+91 9765432100", "Hyderabad"),
]

ORDERS = [
    ("ORD100001","CUST001","delivered",       "UPI",          "paid",          2499,0,200,2299, "2025-04-01 10:30","2025-04-02 08:00","2025-04-05","2025-04-04 14:22","BLRT123456IN","BlueDart",  "Flat 4B, Koregaon Park, Pune 411001",             None),
    ("ORD100002","CUST001","out_for_delivery","Credit Card",  "paid",          5999,0,0,  5999, "2025-04-10 14:15","2025-04-11 09:30","2025-04-13",None,              "DTDC987654IN","DTDC",      "Flat 4B, Koregaon Park, Pune 411001",             None),
    ("ORD100003","CUST002","processing",      "Net Banking",  "paid",          1299,49,0, 1348, "2025-04-12 09:00",None,              "2025-04-18",None,              None,          None,        "302, Sea View, Bandra, Mumbai 400050",            "Seller preparing shipment"),
    ("ORD100004","CUST003","cancelled",       "COD",          "refund_pending", 899,49,0,  948, "2025-04-08 16:45",None,              None,        None,              None,          None,        "45, Lajpat Nagar, New Delhi 110024",              "Cancelled by customer"),
    ("ORD100005","CUST004","shipped",         "UPI",          "paid",          3499,0,350,3149, "2025-04-09 11:20","2025-04-10 07:45","2025-04-14",None,              "EKRT556677IN","Ecom Express","12, Indiranagar, Bangalore 560038",            None),
    ("ORD100006","CUST005","delivered",       "Debit Card",   "paid",           799,49,0,  848, "2025-04-03 13:10","2025-04-04 10:00","2025-04-07","2025-04-06 11:30","XPRS223344IN","XpressBees","78, Jubilee Hills, Hyderabad 500033",            None),
    ("ORD100007","CUST001","return_initiated","Credit Card",  "refund_pending",4599,0,0,  4599, "2025-03-28 10:00","2025-03-29 08:30","2025-04-01","2025-04-01 15:00","BLRT778899IN","BlueDart",  "Flat 4B, Koregaon Park, Pune 411001",             "Return pickup scheduled Apr 15"),
    ("ORD100008","CUST002","payment_failed",  "Credit Card",  "failed",        2199,0,0,  2199, "2025-04-12 20:30",None,              None,        None,              None,          None,        "302, Sea View, Bandra, Mumbai 400050",            "Payment declined by bank"),
    ("ORD100009","CUST003","delivered",       "UPI",          "paid",          1599,0,0,  1599, "2025-03-20 11:00","2025-03-21 09:00","2025-03-24","2025-03-23 16:45","SAFE112233IN","SafeExpress","45, Lajpat Nagar, New Delhi 110024",            None),
    ("ORD100010","CUST004","delivered",       "Debit Card",   "refunded",      3299,0,0,  3299, "2025-03-15 10:00","2025-03-16 08:30","2025-03-19","2025-03-18 14:00","EKRT998877IN","Ecom Express","12, Indiranagar, Bangalore 560038",           "Delivered — item returned and refunded"),
]

ORDER_ITEMS = [
    ("ORD100001","Boat Airdopes 141 TWS Earbuds",         1, 1299),
    ("ORD100001","Phone Case - iPhone 14",                 2,  599),
    ("ORD100002","Samsung Galaxy Watch 6 Classic",         1, 5999),
    ("ORD100003","Noise ColorFit Pro 4 Smartwatch",        1, 1299),
    ("ORD100004","Polo T-Shirt Pack of 3",                 1,  899),
    ("ORD100005","Levi's 511 Slim Fit Jeans",              1, 2499),
    ("ORD100005","Nike Dri-FIT T-Shirt",                   1,  999),
    ("ORD100006","Wildcraft Backpack 30L",                 1,  799),
    ("ORD100007","boAt Rockerz 450 Headphones",            1, 4599),
    ("ORD100008","Mi 43 inch 4K Smart TV",                 1, 2199),
    ("ORD100009","Fastrack Casual Watch",                  1, 1599),
    ("ORD100010","Puma Running Shoes",                     1, 3299),
]

RETURNS = [
    # (return_id, order_id, customer_id, reason, status,
    #  items_returned, pickup_date, picked_up_at, received_at,
    #  inspection_note, created_at, updated_at)

    # ORD100007 — return initiated, pickup scheduled
    ("RET001","ORD100007","CUST001",
     "Product not as described — sound quality poor",
     "pickup_scheduled",
     "boAt Rockerz 450 Headphones x1",
     "2025-04-15","2025-04-15 11:00",None,
     None,
     "2025-04-10 09:30","2025-04-10 10:00"),

    # ORD100001 — return completed, refund processed
    ("RET002","ORD100001","CUST001",
     "Wrong item received — ordered black, received blue",
     "completed",
     "Phone Case - iPhone 14 x2",
     "2025-04-08","2025-04-08 10:30","2025-04-09 14:00",
     "Item verified. Original packaging intact. Refund approved.",
     "2025-04-06 15:00","2025-04-09 16:00"),

    # ORD100010 — return completed, full refund
    ("RET003","ORD100010","CUST004",
     "Size too small — need a larger size but not available",
     "completed",
     "Puma Running Shoes x1",
     "2025-03-22","2025-03-22 09:45","2025-03-23 13:00",
     "Shoes unused, tags intact. Full refund approved.",
     "2025-03-20 18:00","2025-03-23 15:00"),

    # ORD100009 — return rejected
    ("RET004","ORD100009","CUST003",
     "Changed mind — don't need the watch anymore",
     "rejected",
     "Fastrack Casual Watch x1",
     None,None,None,
     "Return rejected: 30-day return window expired. Order delivered on Mar 23, return requested Apr 10.",
     "2025-04-10 14:00","2025-04-11 10:00"),

    # ORD100006 — return requested, under review
    ("RET005","ORD100006","CUST005",
     "Backpack zipper broke within 2 days of delivery",
     "under_review",
     "Wildcraft Backpack 30L x1",
     "2025-04-12",None,None,
     None,
     "2025-04-09 11:00","2025-04-09 12:00"),
]

REFUNDS = [
    # (refund_id, order_id, return_id, customer_id, amount, method,
    #  status, reason, initiated_at, processed_at, utr_number, notes)

    # RET002 — refund for wrong item (partial, only the cases)
    ("REF001","ORD100001","RET002","CUST001",
     1198.00,"UPI",
     "processed",
     "Wrong item received — 2x phone cases refunded",
     "2025-04-09 16:30","2025-04-10 11:00",
     "UTR2025041098765","Refund of ₹1198 for 2x Phone Case - iPhone 14"),

    # RET003 — full refund for shoes
    ("REF002","ORD100010","RET003","CUST004",
     3299.00,"Debit Card",
     "processed",
     "Item returned — size unavailable",
     "2025-03-23 15:30","2025-03-25 10:00",
     "UTR2025032567890","Full refund ₹3299 for Puma Running Shoes"),

    # ORD100004 — cancelled order refund (no return needed)
    ("REF003","ORD100004",None,"CUST003",
     948.00,"Bank Transfer (NEFT)",
     "processing",
     "Order cancelled before dispatch",
     "2025-04-08 17:00",None,
     None,"COD order cancelled — refund via NEFT in 5-7 business days"),

    # RET001 — refund pending (return not yet received)
    ("REF004","ORD100007","RET001","CUST001",
     4599.00,"Credit Card",
     "pending",
     "Product not as described — return in progress",
     "2025-04-10 10:00",None,
     None,"Refund will be initiated after item is received and inspected"),
]


def seed():
    create_tables()
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("DELETE FROM refunds")
    cur.execute("DELETE FROM returns")
    cur.execute("DELETE FROM order_items")
    cur.execute("DELETE FROM orders")
    cur.execute("DELETE FROM customers")

    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
    cur.executemany(
        "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ORDERS)
    cur.executemany(
        "INSERT INTO order_items (order_id,product,quantity,unit_price) VALUES (?,?,?,?)",
        ORDER_ITEMS)
    cur.executemany(
        "INSERT INTO returns VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", RETURNS)
    cur.executemany(
        "INSERT INTO refunds VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", REFUNDS)

    conn.commit()
    conn.close()
    print(f"  Seeded {len(CUSTOMERS)} customers, {len(ORDERS)} orders, "
          f"{len(RETURNS)} returns, {len(REFUNDS)} refunds.")


if __name__ == "__main__":
    seed()
