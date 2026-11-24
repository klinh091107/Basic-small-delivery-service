"""The single source of truth for proposed status names and transitions."""

STATUSES = ("Received", "Packed", "Handed to Courier", "In Transit", "Delivered")
CANCELLED = "Cancelled"
WORKFLOW = STATUSES
STATUSES = WORKFLOW + (CANCELLED,)
# Cancelled is never reachable through a plain status edit; it has its own endpoint
# so stock is restored exactly once.
STATUS_TRANSITIONS = {
    status: list(WORKFLOW[index:index + 2])
    for index, status in enumerate(WORKFLOW)
}
STATUS_TRANSITIONS[CANCELLED] = [CANCELLED]
# Orders can only be cancelled before they leave the warehouse.
CANCELLABLE = ("Received", "Packed")

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
