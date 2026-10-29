def test_create_and_get_payment(client):
    response = client.post(
        "/api/v1/payments",
        json={
            "order_id": "order_123",
            "amount": "49.90",
            "currency": "usd",
            "provider": "stripe",
        },
    )

    assert response.status_code == 201
    created = response.get_json()
    assert created["order_id"] == "order_123"
    assert created["status"] == "pending"
    assert created["currency"] == "USD"
    assert created["provider"] == "stripe"

    response = client.get(f"/api/v1/payments/{created['id']}")
    assert response.status_code == 200
    assert response.get_json()["id"] == created["id"]


def test_list_payments(client):
    client.post("/api/v1/payments", json={"order_id": "order_1", "amount": 10})
    client.post("/api/v1/payments", json={"order_id": "order_2", "amount": 20})

    response = client.get("/api/v1/payments")

    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 2


def test_create_payment_requires_positive_amount(client):
    response = client.post("/api/v1/payments", json={"order_id": "order_1", "amount": 0})

    assert response.status_code == 400
    assert "amount" in response.get_json()["error"]


def test_get_unknown_payment_returns_404(client):
    response = client.get("/api/v1/payments/999")

    assert response.status_code == 404
