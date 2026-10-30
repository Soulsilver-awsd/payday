# Payday

Monorepo con las APIs de Payday. Cada servicio es un proyecto Flask independiente
con su propio entorno virtual, dependencias y base de datos.

## Servicios

| Servicio      | Descripción                          | Puerto por defecto |
| ------------- | ------------------------------------ | ------------------ |
| `order-api`   | Gestión de órdenes + orquestación    | 5000               |
| `payment-api` | Gestión de pagos (mock)              | 5001               |

> `order-api` llama a `payment-api` mediante `PAYMENT_API_URL`
> (`http://localhost:5001` por defecto).

## Estructura de cada servicio

```
<service>/
├── app/
│   ├── __init__.py        # Application factory
│   ├── config.py          # Configuración por entorno
│   ├── extensions.py      # Extensiones (SQLAlchemy, Migrate)
│   ├── errors.py          # Manejo de errores JSON
│   ├── api/
│   │   ├── health.py      # /health y /health/ready
│   │   └── v1/            # Endpoints versionados
│   └── models/            # Modelos SQLAlchemy
├── tests/                 # Tests con pytest
├── wsgi.py                # Entrypoint para Flask CLI / Gunicorn
├── Dockerfile
└── Makefile
```

## Puesta en marcha

Cada servicio se configura por separado:

```bash
cd order-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
flask --app wsgi run --debug
```

Repite el proceso en `payment-api`, pero arráncalo en el puerto 5001:

```bash
cd payment-api
flask --app wsgi run --debug --port 5001
```

## Demo

Con ambos servicios levantados:

```bash
pip install requests
python demo_runner.py
```

El runner ejecuta los 5 escenarios y usa `POST /demo/reset` para partir de
stock inicial = 1 en cada caso.

## Endpoints base

| Método | Ruta                    | Descripción              |
| ------ | ----------------------- | ------------------------ |
| GET    | `/health`               | Liveness probe           |
| GET    | `/health/ready`         | Readiness probe (DB)     |
| GET    | `/api/v1/orders`        | Lista órdenes            |
| POST   | `/api/v1/orders`        | Crea una orden           |
| GET    | `/api/v1/orders/<id>`   | Obtiene una orden        |
| POST   | `/orders`               | Pedido con stock idempotente |
| GET    | `/api/v1/payments`      | Lista pagos              |
| POST   | `/api/v1/payments`      | Crea un pago             |
| GET    | `/api/v1/payments/<id>` | Obtiene un pago          |
| POST   | `/pay`                  | Cobro mock idempotente   |
| GET    | `/payments/status`      | Consulta pago por clave  |
| POST   | `/demo/reset`           | Reset de stock (demo)    |

## Tests

```bash
cd order-api && make test
cd payment-api && make test
```
