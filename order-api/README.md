# order-api

API Flask para la gestión de órdenes de Payday.

## Requisitos

- Python 3.12+
- SQLite para desarrollo (o PostgreSQL vía `DATABASE_URL`)
- `payment-api` corriendo en `http://localhost:5001` (configurable con `PAYMENT_API_URL`)

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
- `POST /orders` — crea un pedido, reserva stock y orquesta el pago (idempotente)
- `POST /demo/reset` — reinicia stock y pedidos (solo con `DEMO_MODE`)
- `GET /api/v1/orders` — lista órdenes
- `POST /api/v1/orders` — crea una orden
- `GET /api/v1/orders/<id>` — obtiene una orden

### POST /orders

Reserva la única unidad de inventario disponible en SQLite y llama a
`POST /pay` del Payment Mock con la misma `idempotency_key`.

- `scenario=approved`: el pedido queda `paid` y el stock reservado.
- `scenario=rejected`: el pago se rechaza, se libera el stock y responde `402`.
- `scenario=timeout`: el pago queda incierto; antes de decidir, se consulta
  `GET /payments/status` con la misma clave. Si no hay confirmación, se libera
  el stock y responde `504`.

Si la `idempotency_key` ya existe, devuelve el pedido existente sin volver a
cobrar ni descontar stock. Si no hay stock, responde `409 Out of stock`.

```bash
curl -X POST http://localhost:5000/orders \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "order_001", "customer_id": "cus_123", "total_amount": 25.00, "scenario": "approved"}'
```

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
