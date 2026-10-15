"""Order writes stay together; callers commit only after every change succeeds."""
from fastapi import HTTPException
from sqlalchemy import select

from .config import STATUSES, STATUS_TRANSITIONS
from .models import Customer, Order, OrderItem, OrderStatusHistory, Product, utc_now
from .validation import validate_total_quantity


def get_or_404(db, model, record_id):
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(404, f"{model.__name__} not found.")
    return record


def validate_products(db, items):
    requested = {item.product_id for item in items}
    found = set(db.scalars(select(Product.id).where(Product.id.in_(requested))))
    if requested != found:
        raise HTTPException(422, f"Unknown product ID(s): {', '.join(map(str, sorted(requested - found)))}.")


def create_order(db, payload):
    get_or_404(db, Customer, payload.customer_id)
    validate_products(db, payload.items)
    order = Order(**payload.model_dump(exclude={"items"}), status=STATUSES[0])
    db.add(order)
    db.flush()
    order.order_number = f"ORD-{order.id:06d}"
    order.items = [OrderItem(**item.model_dump()) for item in payload.items]
    order.status_history.append(OrderStatusHistory(previous_status=None, new_status=STATUSES[0]))
    db.flush()
    return order


def update_order(db, order, payload):
    changes = payload.model_dump(exclude_unset=True)
    # Enforce the new limit even when a legacy order's items are omitted.
    try:
        validate_total_quantity(payload.items if "items" in changes else order.items)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    delivery_date = changes.get("scheduled_delivery_date", order.scheduled_delivery_date)
    if delivery_date < order.received_date:
        raise HTTPException(422, "Scheduled delivery date cannot precede received date.")
    status = changes.get("status", order.status)
    if status not in STATUSES:
        raise HTTPException(422, "Status must be one of: " + ", ".join(STATUSES) + ".")
    if status not in STATUS_TRANSITIONS[order.status]:
        raise HTTPException(422, f"Cannot change status from {order.status} to {status}. Keep the current status or advance to the next status.")
    if "items" in changes:
        validate_products(db, payload.items)
        order.items.clear()
        # Delete old lines before inserting replacements with the same products.
        # This flush is NOT a commit; any subsequent failure rolls it all back.
        db.flush()
        order.items = [OrderItem(**item.model_dump()) for item in payload.items]
    if status != order.status:
        order.status_history.append(OrderStatusHistory(previous_status=order.status, new_status=status))
    for field, value in changes.items():
        if field != "items":
            setattr(order, field, value)
    if changes:
        order.updated_at = utc_now()
    db.flush()
    return order
