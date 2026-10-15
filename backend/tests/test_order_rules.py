import pytest
from app.validation import normalize_phone


@pytest.mark.parametrize('method', ['cash', 'qr_banking', 'credit_card'])
def test_payment_methods(client, order_payload, method):
    order_payload['payment_method'] = method
    response = client.post('/api/orders', json=order_payload)
    assert response.status_code == 201
    assert response.json()['payment_method'] == method


@pytest.mark.parametrize('method', ['bitcoin', '', None])
def test_invalid_payment(client, order_payload, method):
    order_payload['payment_method'] = method
    assert client.post('/api/orders', json=order_payload).status_code == 422


def test_payment_required(client, order_payload):
    del order_payload['payment_method']
    assert client.post('/api/orders', json=order_payload).status_code == 422


@pytest.mark.parametrize('quantities,status', [([49, 1], 201), ([49.9, .1], 201), ([50, 1], 422), ([25, 25.01], 422)])
def test_total_limit(client, order_payload, quantities, status):
    for item, quantity in zip(order_payload['items'], quantities):
        item['quantity'] = quantity
    assert client.post('/api/orders', json=order_payload).status_code == status


def test_failed_update_preserves_order(client, order_payload):
    saved = client.post('/api/orders', json=order_payload).json()
    items = order_payload['items']
    items[0]['quantity'] = 50
    response = client.patch(f"/api/orders/{saved['id']}", json={'items': items, 'payment_method': 'credit_card'})
    assert response.status_code == 422
    current = client.get(f"/api/orders/{saved['id']}").json()
    assert current['payment_method'] == 'cash'
    assert current['items'][0]['quantity'] == 2.5


@pytest.mark.parametrize('raw,expected', [('+84 90 123 4567', '+84901234567'), ('+44 20 7946 0018', '+442079460018'), ('+1 (202) 555-0123', '+12025550123')])
def test_international_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize('phone', ['0901234567', '+123', '+84abc901234567', '+1 202 555 0123 ext 2'])
def test_invalid_customer_phone(client, phone):
    assert client.post('/api/customers', json={'full_name': 'Phone Test', 'phone': phone, 'address': 'Test address'}).status_code == 422


def test_customer_patch_phone(client, records):
    customer, _ = records
    route = f"/api/customers/{customer['id']}"
    response = client.patch(route, json={'phone': '+44 20 7946 0018'})
    assert response.status_code == 200
    assert response.json()['phone'] == '+442079460018'
    assert client.patch(route, json={'phone': 'invalid'}).status_code == 422
    assert client.get(route).json()['phone'] == '+442079460018'


def test_legacy_schema_migration_is_idempotent(tmp_path):
    from sqlalchemy import create_engine
    from app.setup_database import initialize_database
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE orders (id INTEGER PRIMARY KEY, order_number TEXT)')
        connection.exec_driver_sql("INSERT INTO orders VALUES (1, 'LEGACY-001')")
    initialize_database(engine)
    initialize_database(engine)
    with engine.connect() as connection:
        row = connection.exec_driver_sql('SELECT order_number, payment_method FROM orders').one()
        assert tuple(row) == ('LEGACY-001', None)
    engine.dispose()
