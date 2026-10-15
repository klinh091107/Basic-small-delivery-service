from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator
from pydantic import AfterValidator

from .config import PAYMENT_METHODS
from .validation import normalize_phone, validate_total_quantity

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40), AfterValidator(normalize_phone)]


def valid_payment_method(value):
    if value not in PAYMENT_METHODS:
        raise ValueError("Choose a payment method: Cash, QR Banking, or Credit Card.")
    return value


PaymentMethod = Annotated[str, AfterValidator(valid_payment_method)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerCreate(InputModel):
    full_name: Name
    phone: Phone
    email: EmailStr | None = None
    address: Address


class CustomerPatch(InputModel):
    full_name: Name | None = None
    phone: Phone | None = None
    email: EmailStr | None = None
    address: Address | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key != "email" and value is None:
                    raise ValueError(f"{key.replace('_', ' ')} cannot be null.")
        return data


class ItemInput(InputModel):
    product_id: int = Field(gt=0)
    quantity: float = Field(gt=0, allow_inf_nan=False)


class ItemValidation(InputModel):
    @field_validator("items", check_fields=False)
    @classmethod
    def unique_products(cls, items):
        if items is not None and len({item.product_id for item in items}) != len(items):
            raise ValueError("Duplicate product lines are not allowed. Combine their quantities into one line.")
        return validate_total_quantity(items) if items is not None else items


class OrderCreate(ItemValidation):
    customer_id: int = Field(gt=0)
    received_date: date
    scheduled_delivery_date: date
    delivery_address: Address
    responsible_staff_name: Name
    payment_method: PaymentMethod
    items: list[ItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.scheduled_delivery_date < self.received_date:
            raise ValueError("Scheduled delivery date cannot precede received date.")
        return self


class OrderPatch(ItemValidation):
    scheduled_delivery_date: date | None = None
    delivery_address: Address | None = None
    responsible_staff_name: Name | None = None
    payment_method: PaymentMethod | None = None
    status: Name | None = None
    items: list[ItemInput] | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, data):
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("Order fields cannot be null. Omit a field to leave it unchanged.")
        return data


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "updated_at", "changed_at", mode="before", check_fields=False)
    @classmethod
    def utc_timestamps(cls, value):
        # SQLite returns naive datetimes; every stored audit value is UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class CustomerOut(OutputModel):
    id: int
    full_name: str
    phone: str
    email: str | None
    address: str
    created_at: datetime
    updated_at: datetime


class ProductOut(OutputModel):
    id: int
    name: str
    category: str
    unit: str


class ItemOut(OutputModel):
    id: int
    product_id: int
    quantity: float
    product: ProductOut


class HistoryOut(OutputModel):
    id: int
    previous_status: str | None
    new_status: str
    changed_at: datetime


class OrderSummary(OutputModel):
    id: int
    order_number: str
    customer_id: int
    customer: CustomerOut
    received_date: date
    scheduled_delivery_date: date
    delivery_address: str
    responsible_staff_name: str
    payment_method: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class OrderOut(OrderSummary):
    items: list[ItemOut]
    status_history: list[HistoryOut]
