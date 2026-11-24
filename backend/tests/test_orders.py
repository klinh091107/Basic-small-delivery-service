from copy import deepcopy
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from app.config import STATUSES, WORKFLOW
from app.database import Base, make_engine
from app.models import Customer, Order, OrderItem, OrderStatusHistory, Product
from app.seed import seed


def create(client, payload):
    response = client.post('/api/orders', json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_creation_is_persisted_with_items_and_initial_history(client, order_payload, database):
    order = create(client, order_payload)
    assert order['order_number'] == f"ORD-{order['id']:06d}"
    assert order['status'] == 'Received'
    assert len(order['items']) == 2
    assert order['items'][0]['quantity'] == 2.5
    assert order['status_history'][0]['previous_status'] is None
    assert order['status_history'][0]['new_status'] == 'Received'
    assert order['created_at'].endswith('Z')
    assert client.get(f"/api/orders/{order['id']}").json() == order
    assert client.get('/api/orders').json()[0]['id'] == order['id']
    # A new engine/session models restarting the backend against the same file.
    old_engine, _ = database
    reopened = make_engine(str(old_engine.url))
    with reopened.connect() as connection:
        assert connection.scalar(select(func.count(Order.id))) == 1
        assert connection.scalar(select(func.count(OrderItem.id))) == 2
    reopened.dispose()


def test_patch_keeps_omitted_fields_and_replaces_items(client, order_payload, records):
    order = create(client, order_payload)
    response = client.patch(f"/api/orders/{order['id']}", json={
        'items': [{'product_id': records[1][0], 'quantity': 7.25}],
        'scheduled_delivery_date': '2026-10-19', 'delivery_address': 'Order address',
        'responsible_staff_name': 'Jamie', 'status': 'Packed',
    })
    assert response.status_code == 200, response.text
    saved = response.json()
    assert len(saved['items']) == 1 and saved['items'][0]['quantity'] == 7.25
    assert saved['received_date'] == order['received_date']
    assert saved['scheduled_delivery_date'] == '2026-10-19'
    assert saved['responsible_staff_name'] == 'Jamie'
    assert saved['customer_id'] == order['customer_id']
    assert saved['delivery_address'] == 'Order address'
    assert saved['customer']['address'] == 'Original address'
    assert len(saved['status_history']) == 2
    saved_again = client.patch(f"/api/orders/{order['id']}", json={'responsible_staff_name': 'Riley'}).json()
    assert saved_again['items'] == saved['items']
    assert saved_again['delivery_address'] == 'Order address'
    assert saved_again['status_history'] == saved['status_history']
    assert client.patch(f"/api/orders/{order['id']}", json={}).json() == saved_again


def test_customer_address_change_does_not_change_order_address(client, order_payload):
    order = create(client, order_payload)
    response = client.patch(f"/api/customers/{order['customer_id']}", json={'address': 'New profile address'})
    assert response.status_code == 200
    saved = client.get(f"/api/orders/{order['id']}").json()
    assert saved['customer']['address'] == 'New profile address'
    assert saved['delivery_address'] == 'Original address'


def test_status_sequence_and_history(client, order_payload):
    order = create(client, order_payload)
    path = f"/api/orders/{order['id']}"
    for index, status in enumerate(WORKFLOW):
        response = client.patch(path, json={'status': status})
        assert response.status_code == 200, response.text
        history = response.json()['status_history']
        assert len(history) == index + 1
        assert history[-1]['new_status'] == status
        if index:
            assert history[-1]['previous_status'] == WORKFLOW[index - 1]
        assert history[-1]['changed_at'].endswith('Z')
        # Saving the same status must not append another event.
        assert len(client.patch(path, json={'status': status}).json()['status_history']) == index + 1
    assert client.patch(path, json={'status': 'Received'}).status_code == 422


@pytest.mark.parametrize('status', ['Delivered', 'In Transit', 'Handed to Courier', 'Unknown'])
def test_skip_and_invalid_status_rejected(client, order_payload, status):
    order = create(client, order_payload)
    path = f"/api/orders/{order['id']}"
    response = client.patch(path, json={'status': status, 'responsible_staff_name': 'Should not save'})
    assert response.status_code == 422
    assert response.json()['error']['message']
    assert client.get(path).json() == order


@pytest.mark.parametrize('patch', [
    {'items': []}, {'items': [{'product_id': 1, 'quantity': 0}]},
    {'items': [{'product_id': 1, 'quantity': -1}]},
    {'items': [{'product_id': 1, 'quantity': 1}, {'product_id': 1, 'quantity': 2}]},
    {'items': [{'product_id': 999999, 'quantity': 1}]},
    {'items': [{'product_id': 1, 'quantity': 'Infinity'}]},
    {'delivery_address': '   '}, {'responsible_staff_name': ' '},
    {'scheduled_delivery_date': '2026-10-14'}, {'scheduled_delivery_date': 'bad-date'},
    {'customer_id': 999999}, {'received_date': None},
])
def test_invalid_creation_has_no_partial_writes(client, order_payload, database, patch):
    payload = {**deepcopy(order_payload), **patch}
    response = client.post('/api/orders', json=payload)
    assert response.status_code in (404, 422), response.text
    assert response.json()['error']['message']
    with database[1]() as db:
        for model in (Order, OrderItem, OrderStatusHistory):
            assert db.scalar(select(func.count(model.id))) == 0


@pytest.mark.parametrize('patch', [
    {'items': []}, {'items': None}, {'status': None}, {'delivery_address': None},
    {'responsible_staff_name': ''}, {'delivery_address': ' '},
    {'scheduled_delivery_date': '2026-10-14'},
    {'items': [{'product_id': 1, 'quantity': 0}]},
    {'items': [{'product_id': 1, 'quantity': 1}, {'product_id': 1, 'quantity': 2}]},
    {'items': [{'product_id': 99999, 'quantity': 1}]},
    {'customer_id': 1}, {'received_date': '2026-10-14'},
])
def test_invalid_patch_is_atomic(client, order_payload, patch):
    order = create(client, order_payload)
    path = f"/api/orders/{order['id']}"
    response = client.patch(path, json={**patch})
    assert response.status_code == 422, response.text
    assert client.get(path).json() == order


def test_database_failure_during_create_rolls_back_everything(client, order_payload, database):
    engine, factory = database

    def reject_history(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO order_status_history'):
            raise IntegrityError(statement, parameters, Exception('Simulated write failure'))

    event.listen(engine, 'before_cursor_execute', reject_history)
    try:
        assert client.post('/api/orders', json=order_payload).status_code == 409
    finally:
        event.remove(engine, 'before_cursor_execute', reject_history)
    with factory() as db:
        for model in (Order, OrderItem, OrderStatusHistory):
            assert db.scalar(select(func.count(model.id))) == 0


def test_database_failure_after_item_replacement_rolls_back(client, order_payload, database):
    order = create(client, order_payload)
    engine, _ = database

    def reject_history(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO order_status_history'):
            raise IntegrityError(statement, parameters, Exception('Simulated write failure'))

    event.listen(engine, 'before_cursor_execute', reject_history)
    try:
        response = client.patch(f"/api/orders/{order['id']}", json={
            'items': [{'product_id': order_payload['items'][0]['product_id'], 'quantity': 9}],
            'status': 'Packed', 'delivery_address': 'Must roll back',
        })
        assert response.status_code == 409
    finally:
        event.remove(engine, 'before_cursor_execute', reject_history)
    assert client.get(f"/api/orders/{order['id']}").json() == order


def test_status_counts_search_and_static_route(client, order_payload):
    first = create(client, order_payload)
    second = create(client, order_payload)
    client.patch(f"/api/orders/{second['id']}", json={'status': 'Packed'})
    result = client.get('/api/orders/status-counts').json()
    assert result['total'] == 2
    assert result['counts']['Received'] == result['counts']['Packed'] == 1
    assert client.get('/api/orders?status=Packed').json()[0]['id'] == second['id']
    result = client.get('/api/orders/status-counts', params={'search': first['order_number']}).json()
    assert result['total'] == 1 and result['counts']['Packed'] == 0
    assert len(client.get('/api/orders?search=test%20customer').json()) == 2
    assert client.get('/api/orders?search=absent').json() == []
    assert client.get('/api/orders?status=bad').status_code == 422


def test_deliveries_inclusive_range_and_delivered_orders(client, order_payload):
    later = create(client, {**order_payload, 'scheduled_delivery_date': '2026-10-18'})
    early = create(client, {**order_payload, 'scheduled_delivery_date': '2026-10-16'})
    same_day = create(client, {**order_payload, 'scheduled_delivery_date': '2026-10-16'})
    for status in WORKFLOW[1:]:
        client.patch(f"/api/orders/{early['id']}", json={'status': status})
    rows = client.get('/api/deliveries?date_from=2026-10-16').json()
    assert [row['id'] for row in rows] == [early['id'], same_day['id']]
    assert rows[0]['status'] == 'Delivered'
    rows = client.get('/api/deliveries?date_from=2026-10-16&date_to=2026-10-18').json()
    assert [row['id'] for row in rows] == [early['id'], same_day['id'], later['id']]
    assert client.get('/api/deliveries?date_from=2026-10-17').json() == []
    assert client.get('/api/deliveries?date_from=2026-10-18&date_to=2026-10-16').status_code == 422
    assert client.get('/api/deliveries?date_from=invalid').status_code == 422


@pytest.mark.parametrize('path', ['/api/orders/999', '/api/orders/-1', '/api/customers/999', '/api/customers/999/orders'])
def test_missing_ids_are_404(client, path):
    assert client.get(path).status_code == 404


def test_missing_patch_ids_and_customer_validation(client):
    assert client.patch('/api/orders/999', json={'status': 'Packed'}).status_code == 404
    assert client.patch('/api/customers/999', json={'full_name': 'Test'}).status_code == 404
    for field in ('full_name', 'phone', 'address'):
        payload = {'full_name': 'Test', 'phone': '123', 'address': 'A', field: ' '}
        assert client.post('/api/customers', json=payload).status_code == 422


def test_customer_search_edit_email_and_order_list(client, order_payload):
    order = create(client, order_payload)
    customer_id = order['customer_id']
    assert len(client.get('/api/customers?search=customer').json()) == 1
    assert len(client.get('/api/customers?search=901234567').json()) == 1
    assert client.get('/api/customers?search=absent').json() == []
    assert client.get(f'/api/customers/{customer_id}/orders').json()[0]['id'] == order['id']
    assert client.patch(f'/api/customers/{customer_id}', json={'email': None}).json()['email'] is None
    assert client.patch(f'/api/customers/{customer_id}', json={'email': 'not-email'}).status_code == 422
    assert client.patch(f'/api/customers/{customer_id}', json={'address': None}).status_code == 422
    assert client.delete(f'/api/customers/{customer_id}').status_code == 409


def test_products_search_and_category(client, records):
    assert client.get('/api/products?search=car').json()[0]['name'] == 'Carrots'
    assert client.get('/api/products?category=Herbs').json()[0]['name'] == 'Coriander'
    assert client.get('/api/products?search=car&category=Herbs').json() == []


def test_foreign_keys_enabled(database):
    engine, _ = database
    with engine.connect() as connection:
        assert connection.scalar(text('PRAGMA foreign_keys')) == 1
        with pytest.raises(IntegrityError):
            connection.execute(text('INSERT INTO order_items (order_id, product_id, quantity) VALUES (999, 999, 1)'))


def test_seed_idempotent_even_after_edit(database):
    _, factory = database
    with factory() as db:
        seed(db, today=date(2026, 10, 15))
        order = db.scalar(select(Order).order_by(Order.id))
        order.responsible_staff_name = 'Edited staff'
        db.commit()
        seed(db, today=date(2026, 10, 16))
        assert db.scalar(select(func.count(Customer.id))) == 5
        assert db.scalar(select(func.count(Product.id))) == 10
        assert db.scalar(select(func.count(Order.id))) == 10
        assert set(db.scalars(select(Order.status))) == set(WORKFLOW)
        dates = set(db.scalars(select(Order.scheduled_delivery_date)))
        assert dates == {date(2026, 10, 15), date(2026, 10, 16), date(2026, 10, 19)}


def test_concurrent_creation_uses_unique_database_ids(client, order_payload):
    with ThreadPoolExecutor(max_workers=4) as pool:
        orders = list(pool.map(lambda _: create(client, order_payload), range(8)))
    assert len({order['order_number'] for order in orders}) == 8


def test_config_is_central_status_source(client):
    result = client.get('/api/config').json()
    assert result['statuses'] == list(STATUSES)
    assert result['transitions']['Received'] == ['Received', 'Packed']
    assert result['transitions']['Delivered'] == ['Delivered']


def test_delete_order_removes_items_and_history(client, order_payload, database):
    order = create(client, order_payload)
    assert client.delete(f"/api/orders/{order['id']}").status_code == 200
    assert client.get(f"/api/orders/{order['id']}").status_code == 404
    with database[1]() as db:
        assert db.scalar(select(func.count(OrderItem.id))) == 0
        assert db.scalar(select(func.count(OrderStatusHistory.id))) == 0
    assert client.delete(f"/api/orders/{order['id']}").status_code == 404


def test_delete_customer_blocked_while_orders_exist(client, order_payload, records):
    customer = records[0]
    order = create(client, order_payload)
    assert client.delete(f"/api/customers/{customer['id']}").status_code == 409
    client.delete(f"/api/orders/{order['id']}")
    assert client.delete(f"/api/customers/{customer['id']}").status_code == 200
    assert client.get(f"/api/customers/{customer['id']}").status_code == 404
