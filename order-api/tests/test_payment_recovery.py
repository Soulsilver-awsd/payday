import pytest

from app.services.payment_recovery import resolve_payment_after_timeout


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakePaymentClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, *args, **kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("approved", "confirm"),
        ("rejected", "cancel"),
        ("timeout", "cancel"),
        ("unknown", "cancel"),
    ],
)
def test_resolve_payment_status(status, expected):
    client = FakePaymentClient([FakeResponse(200, {"status": status})])

    assert resolve_payment_after_timeout("key-1", client) == expected


def test_missing_payment_allows_retry():
    client = FakePaymentClient([FakeResponse(404)])

    assert resolve_payment_after_timeout("key-1", client) == "retry"


def test_lookup_is_retried_after_network_error():
    client = FakePaymentClient(
        [TimeoutError("timeout"), FakeResponse(200, {"status": "approved"})]
    )

    assert resolve_payment_after_timeout("key-1", client) == "confirm"


def test_unreachable_payment_api_never_retries_the_charge():
    client = FakePaymentClient([TimeoutError("timeout")] * 3)

    assert resolve_payment_after_timeout("key-1", client) == "cancel"
