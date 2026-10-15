"""The single source of truth for proposed status names and transitions."""

STATUSES = ("Received", "Packed", "Handed to Courier", "In Transit", "Delivered")
STATUS_TRANSITIONS = {
    status: list(STATUSES[index:index + 2])
    for index, status in enumerate(STATUSES)
}

PAYMENT_METHODS = {
    "cash": "Cash",
    "qr_banking": "QR Banking",
    "credit_card": "Credit Card",
}
MAX_ORDER_QUANTITY = 50
STAFF_EXAMPLES = (
    "Lan Nguyen — Sales Coordinator",
    "Minh Tran — Order Processing Clerk",
    "Hoa Le — Packing Supervisor",
    "Anh Pham — Dispatch Coordinator",
    "Linh Vu — Customer Service Representative",
)
