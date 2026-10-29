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
- `GET /api/v1/orders` — lista órdenes
- `POST /api/v1/orders` — crea una orden
- `GET /api/v1/orders/<id>` — obtiene una orden

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
