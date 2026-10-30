import requests


class PaymentClient:
    """Thin HTTP client for the Payment Mock API."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def pay(self, idempotency_key: str, amount, scenario: str) -> requests.Response:
        return requests.post(
            f"{self.base_url}/pay",
            json={
                "idempotency_key": idempotency_key,
                "amount": str(amount),
                "scenario": scenario,
            },
            timeout=self.timeout,
        )

    def get(self, path: str, **kwargs) -> requests.Response:
        return requests.get(
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
