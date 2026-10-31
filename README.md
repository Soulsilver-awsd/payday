# Payday

Monorepo con las APIs de Payday para el Reto Técnico de Sistemas Distribuidos: **pedidos, pagos simulados e idempotencia**.

Cada servicio es un proyecto Flask independiente con su propia base de datos persistida en SQLite.

## Servicios

| Servicio      | Descripción                          | Puerto por defecto | Base de datos SQLite |
| ------------- | ------------------------------------ | ------------------ | -------------------- |
| `order-api`   | Gestión de órdenes + orquestación    | 5000               | `order-api/order.db` |
| `payment-api` | Servicio simulado de pagos (mock)    | 5001               | `payment-api/payment.db` |

> `order-api` llama a `payment-api` mediante la variable `PAYMENT_API_URL` (`http://localhost:5001` por defecto).

---

## Estructura del Proyecto

```
payday/
├── demo_runner.py               # Script automático que ejecuta los 5 casos
├── postman/
│   ├── payday.postman_collection.json    # Colección completa para Postman / Bruno
│   └── payday.postman_environment.json   # Variables de entorno para Postman
├── order-api/                   # Servicio de Pedidos e Inventario
│   ├── app/
│   │   ├── api/                 # Endpoints (/orders, /inventory, /health)
│   │   ├── models/              # Modelos Order e Inventory (SQLite)
│   │   └── services/            # Cliente HTTP y reconciliación de timeouts
│   └── tests/                   # Pruebas unitarias y de integración
├── payment-api/                 # Mock de Pasarela de Pagos
│   ├── app/
│   │   ├── api/                 # Endpoints (/pay, /payments/status, /health)
│   │   └── models/              # Modelo Payment (SQLite)
│   └── tests/                   # Pruebas unitarias de idempotencia y cobro
└── README.md
```

---

## Puesta en Marcha

### Requisitos previos
- Python 3.10+
- `pip`

### 1. Iniciar `payment-api` (Puerto 5001)

Abre una primera terminal:

```bash
cd payment-api
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux / macOS:
# source .venv/bin/activate

pip install -r requirements-dev.txt
flask --app wsgi db upgrade
flask --app wsgi run --debug --port 5001
```

### 2. Iniciar `order-api` (Puerto 5000)

Abre una segunda terminal:

```bash
cd order-api
python -m venv .venv

# En Windows:
.venv\Scripts\activate
# En Linux / macOS:
# source .venv/bin/activate

pip install -r requirements-dev.txt
flask --app wsgi db upgrade
flask --app wsgi run --debug --port 5000
```

---

## Pruebas Obligatorias en Postman / Bruno

El repositorio incluye la colección lista para importar en el directorio `postman/`:
- `postman/payday.postman_collection.json`
- `postman/payday.postman_environment.json`

### Los 5 Escenarios Demostrados

| Caso | Escenario | Descripción y Demostración |
| ---- | --------- | -------------------------- |
| **1. Flujo exitoso** | `scenario: approved` | Crea un pedido, reserva inventario (`available: 1 -> 0`), cobra exitosamente y queda en estado `paid`. |
| **2. Repetición (Idempotencia)** | Reenvío misma clave | Reenviar el mismo pedido con la misma `idempotency_key` devuelve la orden previa (`HTTP 200 OK`) sin duplicar pedido, reserva ni cobro. |
| **3. Falla simulada y recuperación** | `scenario: timeout` | El mock registra el cobro (`status: approved`) y simula un timeout (`HTTP 504`). `order-api` consulta `/payments/status` por clave, confirma el pago y reconcilia a `paid` sin cobrar a ciegas. |
| **4. Pago rechazado y compensación** | `scenario: rejected` | El pago es rechazado (`HTTP 402`), el pedido queda en `payment_rejected` y la reserva de stock se libera (`available: 0 -> 1`) una sola vez. |
| **5. Otra intención de compra** | Clave distinta con stock = 0 | Un segundo pedido con **clave distinta** compite cuando no hay stock; recibe `HTTP 409 Conflict (Out of stock)`. El inventario nunca queda negativo gracias a la restricción en SQLite. |

---

## Ejecución Automática de Demostración

Con ambos servicios corriendo, puedes ejecutar la suite de demostración completa por consola:

```bash
python demo_runner.py
```

---

## Endpoints Principales

| Servicio | Método | Ruta | Descripción |
| -------- | ------ | ---- | ----------- |
| **Order API** | `POST` | `/orders` | Crea pedido con reserva de stock e idempotencia (`idempotency_key`, `scenario`) |
| **Order API** | `GET` | `/orders` | Lista todas las órdenes (o filtra con `?idempotency_key=...`) |
| **Order API** | `GET` | `/orders/<id>` | Obtiene el detalle de un pedido por ID |
| **Order API** | `GET` | `/inventory` | Consulta el stock disponible actual |
| **Order API** | `POST` | `/demo/reset` | Restaura stock inicial a 1 y limpia órdenes para pruebas |
| **Payment API** | `POST` | `/pay` | Procesa cobro mock idempotente (`approved`, `rejected`, `timeout`) |
| **Payment API** | `GET` | `/payments/status` | Consulta estado persistido de pago por `idempotency_key` |
| **Payment API** | `POST` | `/demo/reset` | Limpia los registros de pagos de prueba |

---

## Ejecutar Pruebas Automatizadas

```bash
# Pruebas de Order API (23 tests)
pytest order-api

# Pruebas de Payment API (11 tests)
pytest payment-api
```
