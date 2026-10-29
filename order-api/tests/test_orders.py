def test_create_and_get_order(client):
    response = client.post(
        "/api/v1/orders",
        json={
            "customer_id": "cus_123",
            "total_amount": "49.90",
            "currency": "usd",
        },
    )

    assert response.status_code == 201
    created = response.get_json()
    assert created["customer_id"] == "cus_123"
    assert created["status"] == "pending"
    assert created["currency"] == "USD"

    response = client.get(f"/api/v1/orders/{created['id']}")
    assert response.status_code == 200
    assert response.get_json()["id"] == created["id"]


def test_list_orders(client):
    client.post("/api/v1/orders", json={"customer_id": "cus_1", "total_amount": 10})
    client.post("/api/v1/orders", json={"customer_id": "cus_2", "total_amount": 20})

    response = client.get("/api/v1/orders")

    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 2


def test_create_order_requires_customer_id(client):
    response = client.post("/api/v1/orders", json={"total_amount": 10})

    assert response.status_code == 400
    assert "customer_id" in response.get_json()["error"]


def test_get_unknown_order_returns_404(client):
    response = client.get("/api/v1/orders/999")

    assert response.status_code == 404
