"""
database/queries.py
All DB read functions — orders, returns, refunds.
"""
import re
from database.schema import get_connection

ORDER_ID_PATTERN  = re.compile(r'\bORD\d{6}\b',  re.IGNORECASE)
RETURN_ID_PATTERN = re.compile(r'\bRET\d{3}\b',  re.IGNORECASE)
REFUND_ID_PATTERN = re.compile(r'\bREF\d{3}\b',  re.IGNORECASE)

# ── ID extraction ─────────────────────────────────────────────────────────────

def extract_order_id(text: str) -> str | None:
    m = ORDER_ID_PATTERN.search(text.upper())
    return m.group(0) if m else None

def extract_return_id(text: str) -> str | None:
    m = RETURN_ID_PATTERN.search(text.upper())
    return m.group(0) if m else None

def extract_refund_id(text: str) -> str | None:
    m = REFUND_ID_PATTERN.search(text.upper())
    return m.group(0) if m else None


# ── Order lookup ──────────────────────────────────────────────────────────────

def get_order(order_id: str) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    row  = cur.execute("""
        SELECT o.*, c.name AS customer_name, c.email AS customer_email,
               c.phone AS customer_phone, c.city AS customer_city
        FROM orders o JOIN customers c ON o.customer_id = c.id
        WHERE UPPER(o.order_id) = UPPER(?)
    """, (order_id,)).fetchone()

    if not row:
        conn.close()
        return None

    order = dict(row)
    order["items"] = [dict(i) for i in cur.execute(
        "SELECT product, quantity, unit_price FROM order_items WHERE order_id=?",
        (order_id,)
    ).fetchall()]

    # Attach any returns for this order
    order["returns"] = [dict(r) for r in cur.execute(
        "SELECT * FROM returns WHERE order_id=? ORDER BY created_at DESC",
        (order_id,)
    ).fetchall()]

    # Attach any refunds for this order
    order["refunds"] = [dict(r) for r in cur.execute(
        "SELECT * FROM refunds WHERE order_id=? ORDER BY initiated_at DESC",
        (order_id,)
    ).fetchall()]

    conn.close()
    return order


# ── Return lookup ─────────────────────────────────────────────────────────────

def get_return(return_id: str) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    row  = cur.execute("""
        SELECT r.*, c.name AS customer_name, c.email AS customer_email,
               c.phone AS customer_phone
        FROM returns r JOIN customers c ON r.customer_id = c.id
        WHERE UPPER(r.return_id) = UPPER(?)
    """, (return_id,)).fetchone()

    if not row:
        conn.close()
        return None

    ret = dict(row)
    # Attach linked refund if any
    refund = cur.execute(
        "SELECT * FROM refunds WHERE return_id=?", (return_id,)
    ).fetchone()
    ret["refund"] = dict(refund) if refund else None
    conn.close()
    return ret


# ── Refund lookup ─────────────────────────────────────────────────────────────

def get_refund(refund_id: str) -> dict | None:
    conn = get_connection()
    cur  = conn.cursor()
    row  = cur.execute("""
        SELECT rf.*, c.name AS customer_name, c.email AS customer_email
        FROM refunds rf JOIN customers c ON rf.customer_id = c.id
        WHERE UPPER(rf.refund_id) = UPPER(?)
    """, (refund_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Label maps ────────────────────────────────────────────────────────────────

ORDER_STATUS = {
    "processing":        "Processing — seller is preparing your shipment",
    "shipped":           "Shipped — your order is on the way",
    "out_for_delivery":  "Out for Delivery — arriving today",
    "delivered":         "Delivered",
    "cancelled":         "Cancelled",
    "return_initiated":  "Return Initiated",
    "payment_failed":    "Payment Failed",
}

RETURN_STATUS = {
    "pickup_scheduled": "Pickup Scheduled",
    "picked_up":        "Item Picked Up — in transit to warehouse",
    "under_review":     "Under Review — our team is assessing your request",
    "received":         "Item Received at Warehouse",
    "completed":        "Return Completed",
    "rejected":         "Return Rejected",
}

REFUND_STATUS = {
    "pending":    "Pending — will be initiated after return inspection",
    "processing": "Processing — refund has been initiated",
    "processed":  "Processed — amount credited to your account",
    "failed":     "Failed — please contact support",
}

PAY_STATUS = {
    "paid":           "Paid",
    "failed":         "Failed",
    "refund_pending": "Refund Pending",
    "refunded":       "Refunded",
}


# ── Context formatters ────────────────────────────────────────────────────────

def format_order_context(order: dict) -> str:
    lines = [
        f"ORDER DETAILS — {order['order_id']}",
        f"Customer    : {order['customer_name']} | {order['customer_email']} | {order['customer_phone']}",
        f"Status      : {ORDER_STATUS.get(order['status'], order['status'])}",
        f"Payment     : {order['payment_method']} — {PAY_STATUS.get(order['payment_status'], order['payment_status'])}",
        "",
        "Items Ordered:",
    ]
    for i in order["items"]:
        lines.append(f"  - {i['product']} x{i['quantity']} @ ₹{i['unit_price']:.0f}")

    lines += ["",
        f"Subtotal    : ₹{order['subtotal']:.0f}"]
    if order["discount"]:
        lines.append(f"Discount    : -₹{order['discount']:.0f}")
    if order["shipping_charge"]:
        lines.append(f"Shipping    : ₹{order['shipping_charge']:.0f}")
    lines.append(f"Total Paid  : ₹{order['total']:.0f}")
    lines += ["",
        f"Address     : {order['delivery_address']}",
        f"Placed At   : {order['placed_at']}"]
    if order["shipped_at"]:
        lines.append(f"Shipped At  : {order['shipped_at']}")
    if order["estimated_delivery"]:
        lines.append(f"Est Delivery: {order['estimated_delivery']}")
    if order["delivered_at"]:
        lines.append(f"Delivered At: {order['delivered_at']}")
    if order["tracking_number"]:
        lines.append(f"Tracking    : {order['tracking_number']} via {order['courier']}")
    if order["notes"]:
        lines.append(f"Notes       : {order['notes']}")

    # Append return info if present
    for ret in order.get("returns", []):
        lines += ["", f"RETURN — {ret['return_id']}",
            f"  Status         : {RETURN_STATUS.get(ret['status'], ret['status'])}",
            f"  Reason         : {ret['reason']}",
            f"  Items Returned : {ret['items_returned']}",
            f"  Raised On      : {ret['created_at']}"]
        if ret["pickup_date"]:
            lines.append(f"  Pickup Date    : {ret['pickup_date']}")
        if ret["picked_up_at"]:
            lines.append(f"  Picked Up At   : {ret['picked_up_at']}")
        if ret["received_at"]:
            lines.append(f"  Received At WH : {ret['received_at']}")
        if ret["inspection_note"]:
            lines.append(f"  Inspection     : {ret['inspection_note']}")

    # Append refund info if present
    for ref in order.get("refunds", []):
        lines += ["", f"REFUND — {ref['refund_id']}",
            f"  Status      : {REFUND_STATUS.get(ref['status'], ref['status'])}",
            f"  Amount      : ₹{ref['amount']:.0f}",
            f"  Method      : {ref['method']}",
            f"  Reason      : {ref['reason']}",
            f"  Initiated   : {ref['initiated_at']}"]
        if ref["processed_at"]:
            lines.append(f"  Processed   : {ref['processed_at']}")
        if ref["utr_number"]:
            lines.append(f"  UTR Number  : {ref['utr_number']}")
        if ref["notes"]:
            lines.append(f"  Notes       : {ref['notes']}")

    return "\n".join(lines)


def format_return_context(ret: dict) -> str:
    lines = [
        f"RETURN DETAILS — {ret['return_id']}",
        f"Order       : {ret['order_id']}",
        f"Customer    : {ret['customer_name']} | {ret['customer_email']} | {ret['customer_phone']}",
        f"Status      : {RETURN_STATUS.get(ret['status'], ret['status'])}",
        f"Reason      : {ret['reason']}",
        f"Items       : {ret['items_returned']}",
        f"Raised On   : {ret['created_at']}",
    ]
    if ret["pickup_date"]:
        lines.append(f"Pickup Date : {ret['pickup_date']}")
    if ret["picked_up_at"]:
        lines.append(f"Picked Up   : {ret['picked_up_at']}")
    if ret["received_at"]:
        lines.append(f"Received WH : {ret['received_at']}")
    if ret["inspection_note"]:
        lines.append(f"Inspection  : {ret['inspection_note']}")
    if ret["updated_at"]:
        lines.append(f"Last Updated: {ret['updated_at']}")

    if ret.get("refund"):
        ref = ret["refund"]
        lines += ["", f"LINKED REFUND — {ref['refund_id']}",
            f"  Status    : {REFUND_STATUS.get(ref['status'], ref['status'])}",
            f"  Amount    : ₹{ref['amount']:.0f}",
            f"  Method    : {ref['method']}",
            f"  Initiated : {ref['initiated_at']}"]
        if ref["processed_at"]:
            lines.append(f"  Processed : {ref['processed_at']}")
        if ref["utr_number"]:
            lines.append(f"  UTR       : {ref['utr_number']}")

    return "\n".join(lines)


def format_refund_context(ref: dict) -> str:
    lines = [
        f"REFUND DETAILS — {ref['refund_id']}",
        f"Order       : {ref['order_id']}",
        f"Customer    : {ref['customer_name']} | {ref['customer_email']}",
        f"Status      : {REFUND_STATUS.get(ref['status'], ref['status'])}",
        f"Amount      : ₹{ref['amount']:.0f}",
        f"Method      : {ref['method']}",
        f"Reason      : {ref['reason']}",
        f"Initiated   : {ref['initiated_at']}",
    ]
    if ref["processed_at"]:
        lines.append(f"Processed   : {ref['processed_at']}")
    if ref["utr_number"]:
        lines.append(f"UTR Number  : {ref['utr_number']}")
    if ref["notes"]:
        lines.append(f"Notes       : {ref['notes']}")
    return "\n".join(lines)
