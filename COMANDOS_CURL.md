# ⚡ Guía Rápida con Comandos cURL (Terminal)

Esta guía contiene **todos los comandos `curl` listos para copiar y pegar** para ejecutar y demostrar los **5 casos obligatorios** del reto técnico desde la terminal, sin necesidad de usar la interfaz de Postman.

> **💡 Nota importante para PowerShell en Windows:**
> Se usa `curl.exe` y las comillas de los JSON se escapan con barra invertida (`\"`) para que PowerShell no las elimine. Si usas **Git Bash**, **Linux** o **macOS**, puedes quitar la barra invertida.

---

## 🚀 Paso 0: Verificar que ambos servicios estén corriendo

Antes de empezar, asegúrate de tener los dos servicios levantados en terminales separadas:
* `payment-api` en el puerto **5001**: `http://localhost:5001/health`
* `order-api` en el puerto **5000**: `http://localhost:5000/health`

Comprueba que ambos respondan:
```powershell
curl.exe -i http://localhost:5000/health
curl.exe -i http://localhost:5001/health
```

---

## 🧪 CASO 1: Flujo Exitoso (Pago Aprobado)

### 1.1 Preparación (Reset de inventario a 1 unidad)
```powershell
curl.exe -i -X POST http://localhost:5000/demo/reset
```

### 1.2 Enviar pedido con pago aprobado
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case1-approved\", \"customer_id\": \"cliente-1\", \"total_amount\": \"49.90\", \"scenario\": \"approved\"}'
```
* **Respuesta esperada:** `HTTP/1.1 201 Created`
  * `status`: `"paid"`
  * `items_reserved`: `1`
  * `payment_ref`: `"1"`

### 1.3 Verificar en Base de Datos e Inventario
```powershell
curl.exe -s http://localhost:5000/inventory
python inspect_db.py
```
* **Comprobación:** Stock disponible = `0`, 1 orden `paid`, 1 pago `approved`.

---

## 🧪 CASO 2: Repetición de Misma Solicitud (Idempotencia)

### 2.1 Preparación
```powershell
curl.exe -i -X POST http://localhost:5000/demo/reset
```

### 2.2 Primer envío de la solicitud
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case2-replay\", \"customer_id\": \"cliente-2\", \"total_amount\": \"25.00\", \"scenario\": \"approved\"}'
```
* **Respuesta esperada:** `HTTP/1.1 201 Created` (crea la orden por primera vez).

### 2.3 Reenvío con EXACTAMENTE la misma clave de idempotencia
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case2-replay\", \"customer_id\": \"cliente-2-reintento\", \"total_amount\": \"25.00\", \"scenario\": \"approved\"}'
```
* **Respuesta esperada:** `HTTP/1.1 200 OK` (no 201). Devuelve la misma orden original previa.

### 2.4 Verificar en Base de Datos (No duplicación)
```powershell
python inspect_db.py
```
* **Comprobación:** En `order.db` existe **solo 1 orden** para esa clave, en `payment.db` hay **solo 1 cobro**, y el stock sigue en `0` (no se cobró ni reservó dos veces).

---

## 🧪 CASO 3: Falla Simulada (Timeout tras cobro) y Recuperación

### 3.1 Preparación (Reset en ambos servicios)
```powershell
curl.exe -i -X POST http://localhost:5000/demo/reset
curl.exe -i -X POST http://localhost:5001/demo/reset
```

### 3.2 Enviar pedido con timeout simulado en el cobro
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case3-timeout\", \"customer_id\": \"cliente-3\", \"total_amount\": \"35.50\", \"scenario\": \"timeout\"}'
```
* **¿Qué sucede internamente?:**
  1. El mock de pagos registra el cobro en su SQLite (`status: "approved"`) y simula una pérdida de respuesta (`504 Gateway Timeout`).
  2. `order-api` captura el 504. **No vuelve a cobrar a ciegas**.
  3. `order-api` consulta `/payments/status?idempotency_key=curl-case3-timeout`.
  4. Al confirmar que el pago sí fue registrado, reconcilia el pedido dejándolo en `paid`.
* **Respuesta esperada en consola:** `HTTP/1.1 201 Created` con `status: "paid"`.

### 3.3 Consultar directamente el mock de pagos para evidenciar la persistencia
```powershell
curl.exe -i "http://localhost:5001/payments/status?idempotency_key=curl-case3-timeout"
```
* **Respuesta esperada:** `HTTP/1.1 200 OK`, `{"status": "approved", "id": 1, ...}`.

### 3.4 Reenviar con la misma clave (Idempotente)
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case3-timeout\", \"customer_id\": \"cliente-3\", \"total_amount\": \"35.50\", \"scenario\": \"timeout\"}'
```
* **Respuesta esperada:** `HTTP/1.1 200 OK` con la orden ya pagada.

### 3.5 Verificar en Base de Datos
```powershell
python inspect_db.py
```
* **Comprobación:** Exactamente 1 orden `paid` y 1 cobro `approved`.

---

## 🧪 CASO 4: Pago Rechazado y Compensación de Inventario

### 4.1 Preparación
```powershell
curl.exe -i -X POST http://localhost:5000/demo/reset
```

### 4.2 Enviar pedido con rechazo forzado
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case4-rejected\", \"customer_id\": \"cliente-4\", \"total_amount\": \"15.00\", \"scenario\": \"rejected\"}'
```
* **Respuesta esperada:** `HTTP/1.1 402 Payment Required`
  * `status`: `"payment_rejected"`
  * `items_reserved`: `0`

### 4.3 Verificar Compensación (Stock liberado a 1)
```powershell
curl.exe -s http://localhost:5000/inventory
python inspect_db.py
```
* **Comprobación:** `available = 1`. La reserva inicial se liberó automáticamente al fallar el cobro.

---

## 🧪 CASO 5: Otra Intención de Compra (Stock Límite)

### 5.1 Preparación
```powershell
curl.exe -i -X POST http://localhost:5000/demo/reset
```

### 5.2 Pedido A con Clave A (Consume la única unidad)
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case5-clave-A\", \"customer_id\": \"cliente-A\", \"total_amount\": \"50.00\", \"scenario\": \"approved\"}'
```
* **Respuesta esperada:** `HTTP/1.1 201 Created` (stock pasa de 1 a 0).

### 5.3 Pedido B con Clave B distinta (Intenta comprar sin stock disponible)
```powershell
curl.exe -i -X POST http://localhost:5000/orders -H "Content-Type: application/json" -d '{\"idempotency_key\": \"curl-case5-clave-B\", \"customer_id\": \"cliente-B\", \"total_amount\": \"50.00\", \"scenario\": \"approved\"}'
```
* **Respuesta esperada:** `HTTP/1.1 409 Conflict`
  ```json
  {
    "error": "Out of stock"
  }
  ```

### 5.4 Verificar Stock Nunca Negativo
```powershell
curl.exe -s http://localhost:5000/inventory
python inspect_db.py
```
* **Comprobación:** `available = 0`. Gracias al `CHECK (available >= 0)` en SQLite, nunca se produce sobreventa ni stock negativo.

---

## 📋 Resumen de Comandos Rápidos de Consulta

| Acción | Comando |
| :--- | :--- |
| **Ver stock disponible** | `curl.exe -s http://localhost:5000/inventory` |
| **Listar órdenes** | `curl.exe -s http://localhost:5000/orders` |
| **Consultar orden por ID** | `curl.exe -s http://localhost:5000/orders/1` |
| **Consultar orden por Clave** | `curl.exe -s "http://localhost:5000/orders?idempotency_key=CLAVE"` |
| **Consultar pago en Mock** | `curl.exe -s "http://localhost:5001/payments/status?idempotency_key=CLAVE"` |
| **Ver tablas en SQLite** | `python inspect_db.py` |
| **Ejecutar demo completa** | `python demo_runner.py` |
