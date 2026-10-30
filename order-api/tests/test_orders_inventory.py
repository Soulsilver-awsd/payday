from sqlalchemy import select

from app.extensions import db
from app.models import Inventory, Order


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
    assert order["status"] == "reserved"
    assert order["items_reserved"] == 1
    assert order["idempotency_key"] == "order-key-1"

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
