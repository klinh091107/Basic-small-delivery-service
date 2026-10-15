"""Shared business validation, independent of API routes."""
import re
from decimal import Decimal

import phonenumbers

from .config import MAX_ORDER_QUANTITY

PHONE_ERROR = "Enter a valid international phone number with a country code, e.g. +84 90 123 4567 or +44 20 7946 0018."


def normalize_phone(value):
    # Require an explicit country code; reject extensions and alphabetic text.
    value = value.strip()
    if not re.fullmatch(r"\+[0-9 () .-]+", value):
        raise ValueError(PHONE_ERROR)
    try:
        phone = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        raise ValueError(PHONE_ERROR) from None
    if not phonenumbers.is_valid_number(phone):
        raise ValueError(PHONE_ERROR)
    return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)


def validate_total_quantity(items):
    # Decimal avoids rejecting 49.9 + 0.1 because of binary floating-point error.
    total = sum((Decimal(str(item.quantity)) for item in items), Decimal(0))
    if total > MAX_ORDER_QUANTITY:
        raise ValueError(f"Total quantity across all products must not exceed {MAX_ORDER_QUANTITY}.")
    return items
