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

flask --app wsgi run --debug --port 5001
```

La API queda disponible en `http://localhost:5001`.

## Endpoints

- `GET /health` — liveness
- `GET /health/ready` — readiness (incluye chequeo de base de datos)
- `POST /pay` — cobro mock idempotente (`idempotency_key`, `amount`, `scenario`)
- `GET /payments/status` — consulta un pago por `idempotency_key`
- `GET /api/v1/payments` — lista pagos
- `POST /api/v1/payments` — crea un pago
- `GET /api/v1/payments/<id>` — obtiene un pago

### POST /pay

Escenarios disponibles: `approved`, `rejected`, `timeout`.

- Una `idempotency_key` existente devuelve el pago previo sin volver a cobrar.
- `timeout` persiste el cobro en SQLite y responde `504`; un reintento con la misma
  clave devuelve el pago almacenado.

```bash
curl -X POST http://localhost:5001/pay \
  -H "Content-Type: application/json" \
  -d '{"idempotency_key": "pay_001", "amount": 49.90, "scenario": "approved"}'
```

Ejemplo:

```bash
curl -X POST http://localhost:5001/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order_123", "amount": "49.90", "currency": "USD", "provider": "stripe"}'
```

## Tests

```bash
make test
```
