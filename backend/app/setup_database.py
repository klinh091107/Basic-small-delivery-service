"""Small, idempotent schema upgrade for existing local SQLite databases."""
from sqlalchemy import inspect

from .database import Base
from . import models  # Register tables before create_all.


def initialize_database(engine):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("orders")}
        if "payment_method" not in columns:
            # Unknown legacy payment information stays NULL; do not invent Cash.
            connection.exec_driver_sql(
                "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(20) "
                "CHECK (payment_method IN ('cash', 'qr_banking', 'credit_card'))"
            )
        # Additive, idempotent upgrades for inventory and cancellation.
        for table, column, ddl in (
            ("products", "stock_quantity", "FLOAT NOT NULL DEFAULT 0"),
            ("products", "low_stock_threshold", "FLOAT NOT NULL DEFAULT 5"),
            ("products", "stock_updated_at", "TIMESTAMP"),
            ("orders", "inventory_deducted", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("orders", "cancellation_reason", "VARCHAR(500)"),
            ("orders", "cancelled_at", "TIMESTAMP"),
        ):
            existing = {c["name"] for c in inspect(connection).get_columns(table)}
            if column not in existing:
                connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
