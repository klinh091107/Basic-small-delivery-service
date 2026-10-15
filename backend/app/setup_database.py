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
