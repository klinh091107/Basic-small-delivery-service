"""Run with `python -m app.seed` from backend/. Existing records are never reset."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .auth import hash_password
from .config import STATUSES, STAFF_EXAMPLES, PAYMENT_METHODS
from .database import Base, SessionLocal, engine
from .models import Customer, Employee, Order, Product
from .schemas import OrderCreate, OrderPatch
from .services import create_order, update_order
from .setup_database import initialize_database
from .validation import normalize_phone

CUSTOMERS = [
    ("Mai Nguyen", "+84 90 100 0001", "mai@example.com", "18 Lotus Lane, Tay Ho, Hanoi"),
    ("Oliver Bennett", "+84 90 100 0002", "oliver@example.com", "42 Garden Street, Hoan Kiem, Hanoi"),
    ("Linh Tran", "+84 90 100 0003", None, "7 Riverside Road, Ecopark, Hung Yen"),
    ("Sophie Clarke", "+84 90 100 0004", "sophie@example.com", "25 Orchard Lane, Ba Dinh, Hanoi"),
    ("Minh Pham", "+84 90 100 0005", "minh@example.com", "9 Market Street, Cau Giay, Hanoi"),
]
PRODUCTS = [
    ("Carrots", "Vegetables", "kg"), ("Tomatoes", "Vegetables", "kg"),
    ("Baby spinach", "Leafy greens", "bunch"), ("Broccoli", "Vegetables", "kg"),
    ("Bananas", "Fruit", "kg"), ("Mangoes", "Fruit", "box"),
    ("Coriander", "Herbs", "bunch"), ("Potatoes", "Vegetables", "kg"),
    ("Limes", "Fruit", "kg"), ("Spring onions", "Herbs", "bunch"),
]


def seed(db, today=None):
    # Add demo login even when the business dataset was seeded before auth existed.
    # Never reset an existing account's password when seeding again.
    if not db.scalar(select(Employee).where(Employee.employee_code == "NV001")):
        db.add(Employee(employee_code="NV001", full_name=STAFF_EXAMPLES[0],
                        password_hash=hash_password("Produce@123")))
        db.commit()
    employee = db.scalar(select(Employee).where(Employee.employee_code == "NV001"))
    if employee and employee.full_name == "Demo Staff":
        employee.full_name = STAFF_EXAMPLES[0]
    # Upgrade only untouched demo placeholders; preserve staff edits.
    for index in range(10):
        old = db.scalar(select(Order).where(Order.responsible_staff_name == f"Demo staff {index + 1:02d}"))
        if old:
            old.responsible_staff_name = STAFF_EXAMPLES[index % len(STAFF_EXAMPLES)]
    db.commit()
    # SQLite's persistent user_version is our demo-seed marker. No migration
    # framework is used in this MVP. It survives edits to all seeded records.
    if db.connection().exec_driver_sql("PRAGMA user_version").scalar() >= 1:
        return
    today = today or datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    customers, products = [], []
    for name, phone, email, address in CUSTOMERS:
        phone = normalize_phone(phone)
        customer = db.scalar(select(Customer).where(Customer.phone == phone))
        if customer is None:
            customer = Customer(full_name=name, phone=phone, email=email, address=address)
            db.add(customer)
            db.flush()
        customers.append(customer)
    for name, category, unit in PRODUCTS:
        product = db.scalar(select(Product).where(Product.name == name, Product.unit == unit))
        if product is None:
            product = Product(name=name, category=category, unit=unit)
            db.add(product)
            db.flush()
        products.append(product)
    # Dates are assigned only on first seed, so re-running does not move real data.
    for index in range(10):
        customer = customers[index % len(customers)]
        order = create_order(db, OrderCreate(
            customer_id=customer.id,
            received_date=today - timedelta(days=2),
            scheduled_delivery_date=today + timedelta(days=[0, 0, 1, 1, 4][index % 5]),
            delivery_address=customer.address,
            responsible_staff_name=STAFF_EXAMPLES[index % len(STAFF_EXAMPLES)],
            payment_method=list(PAYMENT_METHODS)[index % len(PAYMENT_METHODS)],
            items=[{"product_id": products[index].id, "quantity": 2.5 if products[index].unit == "kg" else 2},
                   {"product_id": products[(index + 3) % len(products)].id, "quantity": 1}],
        ))
        for status in STATUSES[1:index % len(STATUSES) + 1]:
            update_order(db, order, OrderPatch(status=status))
    db.connection().exec_driver_sql("PRAGMA user_version = 1")
    db.commit()


if __name__ == "__main__":
    initialize_database(engine)
    with SessionLocal() as db:
        seed(db)
    print("Demo seed complete. Existing records and dates preserved.")
