class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakePaymentClient:
    def __init__(self):
        self.pay_responses = []
        self.status_responses = []
        self.pay_calls = []
        self.get_calls = []

    def pay(self, idempotency_key, amount, scenario):
        self.pay_calls.append(
            {
                "idempotency_key": idempotency_key,
                "amount": amount,
                "scenario": scenario,
            }
        )
        response = self.pay_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get(self, path, **kwargs):
        self.get_calls.append((path, kwargs))
        response = self.status_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
