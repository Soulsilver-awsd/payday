import requests
from sqlalchemy import select

from app.extensions import db
from app.models import Inventory, Order
from tests.fakes import FakeResponse


def test_create_order_reserves_the_only_unit(client, app):
    response = client.post(
        "/orders",
        json={
            "idempotency_key": "order-key-1",
            "customer_id": "cus_1",
            "total_amount": "25.00",
        },
    )

    assert response.status_code == 201
    order = response.get_json()
    assert order["status"] == "paid"
    assert order["items_reserved"] == 1
    assert order["idempotency_key"] == "order-key-1"
    assert order["payment_ref"] == "1"

    with app.app_context():
        inventory = db.session.get(Inventory, 1)
        assert inventory is not None
        assert inventory.available == 0


def test_same_idempotency_key_does_not_reserve_stock_twice(client, app):
    first = client.post(
        "/orders",
        json={"idempotency_key": "order-key-idem", "customer_id": "cus_1"},
    )
    second = client.post(
        "/orders",
        json={"idempotency_key": "order-key-idem", "customer_id": "cus_2"},
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.get_json()["id"] == first.get_json()["id"]

    with app.app_context():
        orders = db.session.scalars(
            select(Order).where(Order.idempotency_key == "order-key-idem")
        ).all()
        inventory = db.session.get(Inventory, 1)

        assert len(orders) == 1
        assert inventory.available == 0


def test_second_order_is_rejected_when_stock_is_exhausted(client, app):
    first = client.post("/orders", json={"idempotency_key": "order-key-a"})
    second = client.post("/orders", json={"idempotency_key": "order-key-b"})

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.get_json()["error"] == "Out of stock"

    with app.app_context():
        order_b = db.session.scalar(
            select(Order).where(Order.idempotency_key == "order-key-b")
        )
        assert order_b is None
        assert db.session.get(Inventory, 1).available == 0


def test_create_order_requires_idempotency_key(client):
    response = client.post("/orders", json={"customer_id": "cus_1"})

    assert response.status_code == 400
    assert "idempotency_key" in response.get_json()["error"]


def test_rejected_payment_releases_stock(client, app, payment_client):
    payment_client.pay_responses = [
        FakeResponse(201, {"status": "rejected", "payment_id": 7})
    ]

    response = client.post(
        "/orders",
        json={"idempotency_key": "order-rejected", "total_amount": "10.00"},
    )

    assert response.status_code == 402
    order = response.get_json()
    assert order["status"] == "payment_rejected"
    assert order["items_reserved"] == 0
    assert order["payment_ref"] == "7"

    with app.app_context():
        assert db.session.get(Inventory, 1).available == 1


def test_timeout_is_recovered_as_approved(client, app, payment_client):
    payment_client.pay_responses = [
        FakeResponse(504, {"error": "timeout", "payment_id": 9})
    ]
    payment_client.status_responses = [
        FakeResponse(200, {"status": "approved", "payment_id": 9}),
        FakeResponse(200, {"status": "approved", "payment_id": 9}),
    ]

    response = client.post(
        "/orders",
        json={"idempotency_key": "order-timeout-ok", "scenario": "timeout"},
    )

    assert response.status_code == 201
    order = response.get_json()
    assert order["status"] == "paid"
    assert order["payment_ref"] == "9"

    with app.app_context():
        assert db.session.get(Inventory, 1).available == 0


def test_timeout_without_confirmation_releases_stock(client, app, payment_client):
    payment_client.pay_responses = [
        FakeResponse(504, {"error": "timeout", "payment_id": 10})
    ]
    payment_client.status_responses = [
        FakeResponse(200, {"status": "timeout", "payment_id": 10})
    ]

    response = client.post(
        "/orders",
        json={"idempotency_key": "order-timeout", "scenario": "timeout"},
    )

    assert response.status_code == 504
    order = response.get_json()
    assert order["status"] == "payment_timeout"
    assert order["items_reserved"] == 0

    with app.app_context():
        assert db.session.get(Inventory, 1).available == 1


def test_timeout_retries_when_payment_does_not_exist(client, app, payment_client):
    payment_client.pay_responses = [
        FakeResponse(504, {"error": "timeout"}),
        FakeResponse(201, {"status": "approved", "payment_id": 11}),
    ]
    payment_client.status_responses = [FakeResponse(404)]

    response = client.post(
        "/orders",
        json={"idempotency_key": "order-retry", "scenario": "approved"},
    )

    assert response.status_code == 201
    assert response.get_json()["status"] == "paid"
    assert len(payment_client.pay_calls) == 2


def test_network_error_is_recovered_as_approved(client, app, payment_client):
    payment_client.pay_responses = [requests.ConnectionError("payment down")]
    payment_client.status_responses = [
        FakeResponse(200, {"status": "approved", "payment_id": 12}),
        FakeResponse(200, {"status": "approved", "payment_id": 12}),
    ]

    response = client.post("/orders", json={"idempotency_key": "order-network"})

    assert response.status_code == 201
    assert response.get_json()["status"] == "paid"
    assert response.get_json()["payment_ref"] == "12"


def test_unreachable_payment_api_releases_stock(client, app, payment_client):
    payment_client.pay_responses = [requests.ConnectionError("payment down")]
    payment_client.status_responses = [requests.ConnectionError("payment down")] * 3

    response = client.post("/orders", json={"idempotency_key": "order-unreachable"})

    assert response.status_code == 504
    assert response.get_json()["status"] == "payment_timeout"

    with app.app_context():
        assert db.session.get(Inventory, 1).available == 1


def test_demo_reset_restores_stock_and_clears_orders(client, app):
    client.post("/orders", json={"idempotency_key": "order-before-reset"})

    response = client.post("/demo/reset")

    assert response.status_code == 200
    assert response.get_json() == {"status": "reset", "available": 1}

    with app.app_context():
        assert db.session.get(Inventory, 1).available == 1
        assert db.session.scalar(select(Order)) is None
