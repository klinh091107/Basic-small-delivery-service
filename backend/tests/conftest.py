import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, make_engine
from app.main import app
from app.models import Product


@pytest.fixture
def database(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield engine, factory
    engine.dispose()


@pytest.fixture
def client(database):
    _, factory = database

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    # Tables for this fixture are initialized above; no production lifespan.
    client = TestClient(app)
    yield client
    client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def records(client, database):
    _, factory = database
    customer = client.post('/api/customers', json={
        'full_name': 'Test Customer', 'phone': '+84 123456789',
        'email': 'test@example.com', 'address': 'Original address',
    }).json()
    with factory() as db:
        products = [Product(name='Carrots', category='Vegetables', unit='kg'),
                    Product(name='Coriander', category='Herbs', unit='bunch')]
        db.add_all(products)
        db.commit()
        ids = [product.id for product in products]
    return customer, ids


@pytest.fixture
def order_payload(records):
    customer, products = records
    return {
        'customer_id': customer['id'], 'received_date': '2026-10-15',
        'scheduled_delivery_date': '2026-10-16', 'delivery_address': customer['address'],
        'responsible_staff_name': 'Alex',
        'items': [{'product_id': products[0], 'quantity': 2.5}, {'product_id': products[1], 'quantity': 1}],
    }
