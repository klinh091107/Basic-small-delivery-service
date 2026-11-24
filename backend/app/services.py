"""Order writes stay together; callers commit only after every change succeeds."""
from fastapi import HTTPException
from sqlalchemy import select, update

from .config import CANCELLABLE, CANCELLED, STATUSES, STATUS_TRANSITIONS, WORKFLOW
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


def _number(value):
    return f"{value:g}"


def adjust_stock(db, changes):
    """Apply {product_id: delta} atomically. Negative deltas consume stock.

    Each deduction is a single guarded UPDATE, so concurrent requests can never push a
    product below zero. Any shortage raises 409 and the caller's transaction rolls back.
    """
    changes = {pid: round(delta, 6) for pid, delta in changes.items() if abs(delta) > 1e-9}
    if not changes:
        return
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(changes)))}
    short = [f"{products[pid].name} (needs {_number(-delta)} {products[pid].unit}, available {_number(max(products[pid].stock_quantity, 0))})"
             for pid, delta in sorted(changes.items()) if delta < 0 and products[pid].stock_quantity + delta < -1e-9]
    if short:
        raise HTTPException(409, "Insufficient stock for: " + "; ".join(short) + ".")
    for pid, delta in sorted(changes.items()):
        statement = update(Product).where(Product.id == pid).values(
            stock_quantity=Product.stock_quantity + delta, stock_updated_at=utc_now())
        if delta < 0:
            statement = statement.where(Product.stock_quantity + delta >= -1e-9)
        if db.execute(statement).rowcount != 1:
            raise HTTPException(409, f"Stock for {products[pid].name} changed while saving. Refresh and try again.")
        db.expire(products[pid])


def item_totals(items):
    totals = {}
    for item in items:
        totals[item.product_id] = totals.get(item.product_id, 0) + item.quantity
    return totals


def create_order(db, payload, track_inventory=True):
    get_or_404(db, Customer, payload.customer_id)
    validate_products(db, payload.items)
    if track_inventory:
        adjust_stock(db, {pid: -qty for pid, qty in item_totals(payload.items).items()})
    order = Order(**payload.model_dump(exclude={"items"}), status=WORKFLOW[0], inventory_deducted=track_inventory)
    db.add(order)
    db.flush()
    order.order_number = f"ORD-{order.id:06d}"
    order.items = [OrderItem(**item.model_dump()) for item in payload.items]
    order.status_history.append(OrderStatusHistory(previous_status=None, new_status=WORKFLOW[0]))
    db.flush()
    return order


def update_order(db, order, payload):
    changes = payload.model_dump(exclude_unset=True)
    if order.status == CANCELLED:
        raise HTTPException(422, "Cancelled orders cannot be edited or processed.")
    if changes.get("status") == CANCELLED:
        raise HTTPException(422, "Use Cancel Order to cancel an order so stock is restored.")
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
        if order.inventory_deducted:
            # Only the difference touches stock: increases deduct, decreases restore.
            old, new = item_totals(order.items), item_totals(payload.items)
            adjust_stock(db, {pid: old.get(pid, 0) - new.get(pid, 0) for pid in old.keys() | new.keys()})
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


def cancel_order(db, order, reason=None):
    if order.status == CANCELLED:
        raise HTTPException(409, "This order is already cancelled. Stock was restored when it was first cancelled.")
    if order.status not in CANCELLABLE:
        raise HTTPException(422, f"An order that is {order.status} can no longer be cancelled.")
    previous, restore = order.status, order.inventory_deducted
    # Guarded transition: a repeated or concurrent cancel matches zero rows and cannot restore stock twice.
    claimed = db.execute(update(Order).where(Order.id == order.id, Order.status == previous).values(
        status=CANCELLED, inventory_deducted=False, cancellation_reason=(reason or "").strip() or None,
        cancelled_at=utc_now(), updated_at=utc_now())).rowcount
    if claimed != 1:
        raise HTTPException(409, "This order was changed or cancelled by someone else. Refresh and try again.")
    if restore:
        adjust_stock(db, item_totals(order.items))
    db.add(OrderStatusHistory(order_id=order.id, previous_status=previous, new_status=CANCELLED))
    db.flush()
    db.refresh(order)
    return order


def delete_order(db, order):
    if order.inventory_deducted:
        adjust_stock(db, item_totals(order.items))
    db.delete(order)
    db.flush()
