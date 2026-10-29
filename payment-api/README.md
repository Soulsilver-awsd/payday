# payment-api

API Flask para la gestión de pagos de Payday.

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
- `GET /api/v1/payments` — lista pagos
- `POST /api/v1/payments` — crea un pago
- `GET /api/v1/payments/<id>` — obtiene un pago

Ejemplo:

```bash
curl -X POST http://localhost:5000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_123", "amount": "49.90", "currency": "USD", "provider": "stripe"}'
```

## Tests

```bash
make test
```
