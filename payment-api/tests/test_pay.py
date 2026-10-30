from sqlalchemy import select

from app.extensions import db
from app.models import Payment


def test_pay_approved(client):
    response = client.post(
        "/pay",
        json={"idempotency_key": "key-approved", "amount": "10.50", "scenario": "approved"},
    )

    assert response.status_code == 201
    payment = response.get_json()
    assert payment["status"] == "approved"
    assert payment["idempotency_key"] == "key-approved"
    assert payment["payment_id"] == payment["id"]


def test_pay_is_idempotent(client, app):
    first = client.post(
        "/pay",
        json={"idempotency_key": "key-idem", "amount": 10, "scenario": "approved"},
    )
    second = client.post(
        "/pay",
        json={"idempotency_key": "key-idem", "amount": 999, "scenario": "rejected"},
    )

    assert second.status_code == 200
    assert second.get_json()["id"] == first.get_json()["id"]

    with app.app_context():
        payments = db.session.scalars(
            select(Payment).where(Payment.idempotency_key == "key-idem")
        ).all()
        assert len(payments) == 1


def test_pay_timeout_persists_charge_and_retry_returns_it(client, app):
    response = client.post(
        "/pay",
        json={"idempotency_key": "key-timeout", "amount": 20, "scenario": "timeout"},
    )

    assert response.status_code == 504
    assert response.get_json()["error"] == "timeout"

    with app.app_context():
        payment = db.session.scalar(
            select(Payment).where(Payment.idempotency_key == "key-timeout")
        )
        assert payment is not None
        assert payment.status == "timeout"

    retry = client.post(
        "/pay",
        json={"idempotency_key": "key-timeout", "amount": 20, "scenario": "timeout"},
    )

    assert retry.status_code == 200
    assert retry.get_json()["status"] == "timeout"


def test_pay_rejects_invalid_input(client):
    assert client.post("/pay", json={"amount": 10}).status_code == 400
    assert (
        client.post(
            "/pay",
            json={"idempotency_key": "k", "amount": 10, "scenario": "x"},
        ).status_code
        == 400
    )
    assert client.post("/pay", json={"idempotency_key": "k", "amount": 0}).status_code == 400


def test_payment_status_by_idempotency_key(client):
    client.post(
        "/pay",
        json={"idempotency_key": "key-status", "amount": 10, "scenario": "approved"},
    )

    response = client.get(
        "/payments/status",
        query_string={"idempotency_key": "key-status"},
    )

    assert response.status_code == 200
    payment = response.get_json()
    assert payment["status"] == "approved"
    assert payment["idempotency_key"] == "key-status"


def test_payment_status_unknown_key_returns_404(client):
    response = client.get(
        "/payments/status",
        query_string={"idempotency_key": "missing"},
    )

    assert response.status_code == 404

