import pytest

from app import create_app
from app.extensions import db
from tests.fakes import FakePaymentClient, FakeResponse


@pytest.fixture()
def app():
    application = create_app("testing")

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def payment_client(monkeypatch):
    fake = FakePaymentClient()
    fake.pay_responses = [FakeResponse(201, {"status": "approved", "payment_id": 1})]
    fake.status_responses = [FakeResponse(200, {"status": "approved", "payment_id": 1})]
    monkeypatch.setattr("app.api.orders.PaymentClient", lambda *args, **kwargs: fake)
    return fake
