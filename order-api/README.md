# order-api

API Flask para la gestión de órdenes de Payday.

## Requisitos

- Python 3.12+
- SQLite para desarrollo (o PostgreSQL vía `DATABASE_URL`)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade

flask --app wsgi run --debug
```

La API queda disponible en `http://localhost:5000`.

## Endpoints

- `GET /health` — liveness
- `GET /health/ready` — readiness (incluye chequeo de base de datos)
- `POST /orders` — crea un pedido reservando 1 unidad de stock (idempotente)
- `GET /api/v1/orders` — lista órdenes
- `POST /api/v1/orders` — crea una orden
- `GET /api/v1/orders/<id>` — obtiene una orden

### POST /orders

Reserva la única unidad de inventario disponible en SQLite. La clave
`idempotency_key` tiene una restricción `UNIQUE`: si se repite, devuelve el
pedido existente sin descontar stock ni duplicarlo.

```bash
curl -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "order_001", "customer_id": "cus_123", "total_amount": 25.00}'
```

Si el stock ya fue consumido, responde `409 Out of stock`.

Ejemplo:

```bash
curl -X POST http://localhost:5000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_123", "total_amount": "49.90", "currency": "USD"}'
```

## Tests

```bash
make test
```
