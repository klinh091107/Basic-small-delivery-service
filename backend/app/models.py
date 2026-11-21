from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AuditFields:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Customer(AuditFields, Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    address: Mapped[str] = mapped_column(String(1000))


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(40), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StaffSession(Base):
    __tablename__ = "staff_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(30))


class Order(AuditFields, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("scheduled_delivery_date >= received_date"),
        CheckConstraint("payment_method IN ('cash', 'qr_banking', 'credit_card')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL exists only inside the creation transaction, before the ID is assigned.
    order_number: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    received_date: Mapped[date] = mapped_column(Date)
    scheduled_delivery_date: Mapped[date] = mapped_column(Date, index=True)
    delivery_address: Mapped[str] = mapped_column(String(1000))
    responsible_staff_name: Mapped[str] = mapped_column(String(150))
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    customer: Mapped[Customer] = relationship(lazy="joined")
    items: Mapped[list["OrderItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="OrderItem.id")
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="OrderStatusHistory.id")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (UniqueConstraint("order_id", "product_id"), CheckConstraint("quantity > 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Float)
    product: Mapped[Product] = relationship(lazy="joined")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SeedState(Base):
    __tablename__ = "seed_state"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
