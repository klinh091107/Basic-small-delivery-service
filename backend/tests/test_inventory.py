from sqlalchemy import select

from app.models import Product


def stock(database, product_id):
    with database[1]() as db:
        return db.get(Product, product_id).stock_quantity


def create(client, payload, expect=201):
    response = client.post('/api/orders', json=payload)
    assert response.status_code == expect, response.text
    return response.json()


def set_stock(client, pid, qty):
    response = client.patch(f'/api/products/{pid}', json={'stock_quantity': qty})
    assert response.status_code == 200, response.text
    return response.json()


def test_create_deducts_stock(client, order_payload, records, database):
    ids = records[1]
    create(client, order_payload)
    assert stock(database, ids[0]) == 997.5
    assert stock(database, ids[1]) == 999


def test_insufficient_stock_blocks_order_and_names_products(client, order_payload, records, database):
    ids = records[1]
    set_stock(client, ids[0], 1)
    set_stock(client, ids[1], 0)
    response = client.post('/api/orders', json=order_payload)
    assert response.status_code == 409
    message = response.json()['error']['message']
    assert 'Carrots' in message and 'Coriander' in message
    assert stock(database, ids[0]) == 1 and stock(database, ids[1]) == 0
    assert client.get('/api/orders').json() == []


def test_edit_only_applies_difference(client, order_payload, records, database):
    ids = records[1]
    order = create(client, order_payload)
    items = [{'product_id': ids[0], 'quantity': 4}, {'product_id': ids[1], 'quantity': 0.5}]
    assert client.patch(f"/api/orders/{order['id']}", json={'items': items}).status_code == 200
    assert stock(database, ids[0]) == 996
    assert stock(database, ids[1]) == 999.5
    # Editing something else must not touch stock.
    client.patch(f"/api/orders/{order['id']}", json={'responsible_staff_name': 'Sam'})
    assert stock(database, ids[0]) == 996


def test_edit_cannot_exceed_stock(client, order_payload, records, database):
    ids = records[1]
    order = create(client, order_payload)
    set_stock(client, ids[0], 1)
    response = client.patch(f"/api/orders/{order['id']}", json={'items': [{'product_id': ids[0], 'quantity': 4}]})
    assert response.status_code == 409
    assert stock(database, ids[0]) == 1
    assert len(client.get(f"/api/orders/{order['id']}").json()['items']) == 2


def test_cancel_restores_once(client, order_payload, records, database):
    ids = records[1]
    order = create(client, order_payload)
    response = client.post(f"/api/orders/{order['id']}/cancel", json={'reason': 'Customer changed mind'})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'Cancelled' and body['cancellation_reason'] == 'Customer changed mind'
    assert stock(database, ids[0]) == 1000 and stock(database, ids[1]) == 1000
    again = client.post(f"/api/orders/{order['id']}/cancel", json={})
    assert again.status_code == 409
    assert stock(database, ids[0]) == 1000
    assert client.get('/api/orders').json()[0]['status'] == 'Cancelled'


def test_cancelled_order_is_locked(client, order_payload, records, database):
    order = create(client, order_payload)
    client.post(f"/api/orders/{order['id']}/cancel", json={})
    for body in ({'status': 'Packed'}, {'responsible_staff_name': 'X'}, {'items': [{'product_id': records[1][0], 'quantity': 1}]}):
        assert client.patch(f"/api/orders/{order['id']}", json=body).status_code == 422
    assert stock(database, records[1][0]) == 1000
    assert client.delete(f"/api/orders/{order['id']}").status_code == 200
    assert stock(database, records[1][0]) == 1000


def test_cannot_cancel_via_status_patch_or_after_courier(client, order_payload, records):
    order = create(client, order_payload)
    assert client.patch(f"/api/orders/{order['id']}", json={'status': 'Cancelled'}).status_code == 422
    for status in ('Packed', 'Handed to Courier'):
        client.patch(f"/api/orders/{order['id']}", json={'status': status})
    assert client.post(f"/api/orders/{order['id']}/cancel", json={}).status_code == 422


def test_delete_active_order_restores_stock(client, order_payload, records, database):
    order = create(client, order_payload)
    client.delete(f"/api/orders/{order['id']}")
    assert stock(database, records[1][0]) == 1000


def test_reorder_is_separate_order(client, order_payload, records, database):
    ids = records[1]
    original = create(client, order_payload)
    payload = {**order_payload, 'scheduled_delivery_date': '2026-10-20',
               'items': [{'product_id': ids[0], 'quantity': 3}]}
    copy = create(client, payload)
    assert copy['id'] != original['id'] and copy['order_number'] != original['order_number']
    assert stock(database, ids[0]) == 1000 - 2.5 - 3
    unchanged = client.get(f"/api/orders/{original['id']}").json()
    strip = lambda o: {**o, 'items': [{k: v for k, v in i.items() if k != 'product'} for i in o['items']]}
    assert strip(unchanged) == strip(original)


def test_legacy_orders_do_not_phantom_restore(client, order_payload, records, database):
    ids = records[1]
    order = create(client, order_payload)
    from app.models import Order
    with database[1]() as db:
        db.get(Order, order['id']).inventory_deducted = False
        db.commit()
    client.post(f"/api/orders/{order['id']}/cancel", json={})
    assert stock(database, ids[0]) == 997.5


def test_product_crud_and_validation(client):
    created = client.post('/api/products', json={'name': 'Kale', 'category': 'Leafy greens', 'unit': 'kg', 'stock_quantity': 8, 'low_stock_threshold': 10})
    assert created.status_code == 201
    assert client.post('/api/products', json={'name': 'kale', 'category': 'x', 'unit': 'kg'}).status_code == 409
    pid = created.json()['id']
    assert client.patch(f'/api/products/{pid}', json={'stock_quantity': -1}).status_code == 422
    assert client.patch(f'/api/products/{pid}', json={'stock_quantity': 20}).json()['stock_quantity'] == 20
    assert client.get('/api/products?search=kal').json()[0]['id'] == pid
