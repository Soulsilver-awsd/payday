# 📘 Guía Paso a Paso para la Entrega: Reto Técnico de Idempotencia y Pagos

Esta guía contiene **todo lo necesario "masticadito"** para que el equipo pueda:
1. Levantar y probar los servicios en local.
2. Ejecutar los 5 casos obligatorios en Postman y tomar las capturas requeridas.
3. Consultar e inspeccionar SQLite antes y después de cada prueba.
4. Grabar el video demostrativo de 3 a 5 minutos siguiendo un guion minuto a minuto.
5. Armar el documento PDF final listo para subir a Moodle.

---

## 📋 Checklist de Entregables (Rúbrica 100 Puntos)

- [ ] **Código y Persistencia SQLite (20 pts):** Ambos servicios corriendo en puertos 5000 y 5001, con datos persistidos en `order.db` y `payment.db`.
- [ ] **Idempotencia (25 pts):** Misma clave devuelve el resultado conocido sin duplicar pedidos, reservas ni cobros.
- [ ] **Falla Simulada y Recuperación (25 pts):** Mock persiste cobro antes de timeout y el backend reconcilia sin cobrar a ciegas.
- [ ] **Inventario y Rechazo (15 pts):** Inventario no queda negativo y la reserva se libera si hay rechazo.
- [ ] **Entregables Finales (15 pts):** Colección en repo, README, PDF con tabla y capturas, y video accesible (3–5 min).

---

## 🛠️ Paso 0: Preparación y Puesta en Marcha

Abre **3 terminales** en tu máquina (PowerShell en Windows o Bash en Linux/Mac).

### Terminal 1: Iniciar `payment-api` (Puerto 5001)
```powershell
cd C:\Users\OMEN\Documents\sistema_distribuidos\payday\payment-api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
flask --app wsgi db upgrade
flask --app wsgi run --debug --port 5001
```
> Verifica en navegador o Postman: `http://localhost:5001/health` debe responder `{"status":"ok"}`.

---

### Terminal 2: Iniciar `order-api` (Puerto 5000)
```powershell
cd C:\Users\OMEN\Documents\sistema_distribuidos\payday\order-api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
flask --app wsgi db upgrade
flask --app wsgi run --debug --port 5000
```
> Verifica en navegador o Postman: `http://localhost:5000/health` debe responder `{"status":"ok"}`.

---

### Terminal 3: Consultas Rápidas a SQLite
Para inspeccionar las bases de datos en cualquier momento sin necesidad de software adicional, puedes usar la terminal ejecutando consultas SQLite.

**Para ver órdenes e inventario (`order-api/order.db`):**
```powershell
python -c "import sqlite3; c=sqlite3.connect('order-api/order.db'); print('--- ORDERS ---'); print(c.execute('SELECT id, idempotency_key, status, items_reserved, payment_ref FROM orders').fetchall()); print('--- INVENTORY ---'); print(c.execute('SELECT id, available FROM inventory').fetchall())"
```

**Para ver cobros registrados (`payment-api/payment.db`):**
```powershell
python -c "import sqlite3; c=sqlite3.connect('payment-api/payment.db'); print('--- PAYMENTS ---'); print(c.execute('SELECT id, idempotency_key, status, amount FROM payments').fetchall())"
```
*(También puedes usar la herramienta visual gratuita **DB Browser for SQLite** si prefieres ver tablas con interfaz gráfica).*

---

## 🧪 Paso 1: Ejecución de los 5 Casos en Postman y Evidencias

Abre **Postman** e importa:
1. `postman/payday.postman_collection.json`
2. `postman/payday.postman_environment.json` (selecciona el entorno *Payday Local Environment* en la esquina superior derecha).

A continuación tienes el paso a paso exacto para cada caso, con lo que debes enviar, lo que debes recibir y la captura que debes guardar.

---

### 🔹 Caso 1: Flujo Exitoso (Pago Aprobado)
* **Objetivo:** Demostrar que un pedido nuevo reserva stock, procesa el cobro con éxito y pasa a estado `paid`.

1. **Preparación (Reset):**
   * Petición: `POST http://localhost:5000/demo/reset`
   * Respuesta esperada: `HTTP 200 OK`, `{"available": 1, "status": "reset"}`.
2. **Ejecutar Pedido:**
   * Petición: `POST http://localhost:5000/orders`
   * Body JSON:
     ```json
     {
       "idempotency_key": "idem-case1-approved-001",
       "customer_id": "cliente-caso-1",
       "total_amount": "49.90",
       "currency": "USD",
       "scenario": "approved"
     }
     ```
   * Respuesta esperada: `HTTP 201 Created`
     ```json
     {
       "id": 1,
       "idempotency_key": "idem-case1-approved-001",
       "items_reserved": 1,
       "payment_ref": "1",
       "status": "paid",
       "total_amount": "49.90"
     }
     ```
3. **Consultar Inventario:**
   * Petición: `GET http://localhost:5000/inventory`
   * Respuesta: `HTTP 200 OK`, `{"available": 0}` (el stock bajó de 1 a 0).
4. **📸 Capturas para el PDF:**
   * Captura de Postman mostrando la respuesta `HTTP 201 Created` con status `"paid"`.
   * Captura de SQLite mostrando 1 fila en `orders` (`status: paid`), 1 fila en `payments` (`status: approved`) y `available = 0` en `inventory`.

---

### 🔹 Caso 2: Repetición de la Misma Solicitud (Idempotencia)
* **Objetivo:** Demostrar que reenviar exactamente la misma petición con la misma clave devuelve el pedido original sin duplicar orden, reserva ni cobro.

1. **Preparación (Reset):**
   * Petición: `POST http://localhost:5000/demo/reset`
2. **Primer Envío:**
   * Petición: `POST http://localhost:5000/orders`
   * Body JSON:
     ```json
     {
       "idempotency_key": "idem-case2-replay-002",
       "customer_id": "cliente-caso-2",
       "total_amount": "25.00",
       "currency": "USD",
       "scenario": "approved"
     }
     ```
   * Respuesta esperada: `HTTP 201 Created`, orden con ID 1.
3. **Segundo Envío (Reintento con misma clave):**
   * Petición: `POST http://localhost:5000/orders` (con el mismo body anterior).
   * Respuesta esperada: `HTTP 200 OK` (no 201), devuelve la **misma orden ID 1**.
4. **Verificación en Base de Datos:**
   * Ejecuta la consulta SQL:
     ```sql
     SELECT COUNT(*) FROM orders WHERE idempotency_key = 'idem-case2-replay-002';
     SELECT COUNT(*) FROM payments WHERE idempotency_key = 'idem-case2-replay-002';
     ```
   * Ambas consultas deben devolver exactamente `1`.
5. **📸 Capturas para el PDF:**
   * Captura de Postman con el segundo envío mostrando `HTTP 200 OK` y el mismo `id` y `payment_ref`.
   * Captura de SQLite demostrando que solo existe 1 orden y 1 cobro en las tablas.

---

### 🔹 Caso 3: Falla Simulada y Recuperación (Timeout tras Cobro)
* **Objetivo:** El mock registra el cobro en su BD, pero simula una pérdida de respuesta (`504 Gateway Timeout`). El backend detecta la falla, consulta el estado persistido por clave (`GET /payments/status`), recupera el cobro aprobado y confirma el pedido como `paid` sin cobrar dos veces a ciegas.

1. **Preparación (Reset):**
   * Petición: `POST http://localhost:5000/demo/reset`
   * Petición: `POST http://localhost:5001/demo/reset`
2. **Enviar Pedido con Timeout:**
   * Petición: `POST http://localhost:5000/orders`
   * Body JSON:
     ```json
     {
       "idempotency_key": "idem-case3-timeout-003",
       "customer_id": "cliente-caso-3",
       "total_amount": "35.50",
       "currency": "USD",
       "scenario": "timeout"
     }
     ```
   * **Qué ocurre tras bambalinas:**
     1. `order-api` reserva el stock (`available: 1 -> 0`).
     2. `order-api` llama a `payment-api`.
     3. `payment-api` guarda el pago en SQLite como `status: "approved"` y devuelve `504 Gateway Timeout`.
     4. `order-api` captura el 504. No cobra de nuevo a ciegas.
     5. `order-api` consulta `GET http://localhost:5001/payments/status?idempotency_key=idem-case3-timeout-003`.
     6. Al confirmar que está `approved`, reconcilia la orden marcándola como `paid`.
   * Respuesta esperada en Postman: `HTTP 201 Created` con `status: "paid"`.
3. **Verificar el Estado en el Mock:**
   * Petición: `GET http://localhost:5001/payments/status?idempotency_key=idem-case3-timeout-003`
   * Respuesta: `HTTP 200 OK`, `{"status": "approved", "payment_id": ...}`.
4. **Reenviar Pedido con Misma Clave:**
   * Petición: `POST http://localhost:5000/orders` con la misma clave `idem-case3-timeout-003`.
   * Respuesta: `HTTP 200 OK`, devuelve la orden ya pagada sin reintentar cobro.
5. **📸 Capturas para el PDF:**
   * Captura de Postman mostrando la respuesta de la orden recuperada (`paid`).
   * Captura de `GET /payments/status` mostrando el pago aprobado en el mock.
   * Captura de SQLite mostrando 1 solo cobro y 1 sola orden asociada.

---

### 🔹 Caso 4: Pago Rechazado y Compensación de Inventario
* **Objetivo:** Demostrar que si la pasarela rechaza el cobro, la orden queda en `payment_rejected` y la reserva de inventario se libera automáticamente (compensación de stock).

1. **Preparación (Reset):**
   * Petición: `POST http://localhost:5000/demo/reset`
2. **Enviar Pedido con Rechazo:**
   * Petición: `POST http://localhost:5000/orders`
   * Body JSON:
     ```json
     {
       "idempotency_key": "idem-case4-rejected-004",
       "customer_id": "cliente-caso-4",
       "total_amount": "15.00",
       "currency": "USD",
       "scenario": "rejected"
     }
     ```
   * Respuesta esperada: `HTTP 402 Payment Required`
     ```json
     {
       "id": 1,
       "idempotency_key": "idem-case4-rejected-004",
       "items_reserved": 0,
       "status": "payment_rejected"
     }
     ```
3. **Verificar Compensación de Inventario:**
   * Petición: `GET http://localhost:5000/inventory`
   * Respuesta esperada: `HTTP 200 OK`, `{"available": 1}`.
   * *¡Demostrado!:* La reserva temporal se canceló y el stock regresó a 1.
4. **Reenvío de la misma clave:**
   * Al reenviar la misma solicitud rechazada devuelve `HTTP 200 OK` con `status: "payment_rejected"`, sin volver a descontar stock.
5. **📸 Capturas para el PDF:**
   * Captura de Postman con `HTTP 402` y status `"payment_rejected"`.
   * Captura de `GET /inventory` mostrando `available: 1`.

---

### 🔹 Caso 5: Otra Intención de Compra (Stock Límite)
* **Objetivo:** Demostrar que una clave de idempotencia diferente representa a otro cliente/intención. Cuando el stock se agota (0), la nueva solicitud es rechazada con `409 Conflict`, y el stock nunca desciende a números negativos.

1. **Preparación (Reset):**
   * Petición: `POST http://localhost:5000/demo/reset` (stock = 1).
2. **Pedido A (Cliente A con Clave A):**
   * Petición: `POST http://localhost:5000/orders` con `idempotency_key: "idem-case5-stock-ok-005a"`.
   * Respuesta: `HTTP 201 Created`, status `"paid"`.
   * El stock queda en 0.
3. **Pedido B (Cliente B con Clave B distinta):**
   * Petición: `POST http://localhost:5000/orders` con `idempotency_key: "idem-case5-stock-exhausted-005b"`.
   * Respuesta esperada: `HTTP 409 Conflict`
     ```json
     {
       "error": "Out of stock"
     }
     ```
4. **Verificar Stock en Base de Datos:**
   * Petición: `GET http://localhost:5000/inventory` -> `{"available": 0}`.
   * En SQLite: `SELECT available FROM inventory;` -> Devuelve `0`.
   * *¡Demostrado!:* Gracias al `CheckConstraint("available >= 0")`, nunca se permite sobreventa ni stock negativo.
5. **📸 Capturas para el PDF:**
   * Captura de Postman mostrando `HTTP 409 Conflict - Out of stock`.
   * Captura de SQLite mostrando `available = 0`.

---

## 🎬 Paso 2: Guion Detallado para el Video (3 a 5 Minutos)

> **Regla de la rúbrica:** El video debe durar entre 3 y 5 minutos. Asegúrense de que el enlace en Google Drive / YouTube esté configurado como **"Cualquiera con el enlace puede ver"** (Público / No listado).

### Estructura Minuto a Minuto:

* **0:00 - 0:45 | Introducción:**
  * Presentación de los integrantes del equipo.
  * Breve explicación de la arquitectura: Dos servicios Flask locales (`order-api` en :5000 y `payment-api` en :5001), cada uno con su base de datos SQLite independiente.
  * Muestran en pantalla las dos terminales activas y los healthchecks respondiendo.

* **0:45 - 2:00 | Demostración Obligatoria 1: Timeout posterior al cobro y recuperación (Caso 3):**
  * Mostrar la petición en Postman con `scenario: timeout`.
  * Explicar qué ocurrió: *"El Payment Mock registró el cobro en su BD y luego simuló un 504. Nuestra Order API detectó la incertidumbre, consultó `/payments/status` por clave de idempotencia, vio que el cobro estaba aprobado y reconcilió el pedido a `paid` sin reintentar a ciegas."*
  * Mostrar la consulta a `payment-api/payment.db` comprobando que el pago está guardado.
  * Mostrar `order-api/order.db` comprobando que la orden está `paid` con su `payment_ref`.

* **2:00 - 3:00 | Demostración Obligatoria 2: Idempotencia y Reintento (Caso 2):**
  * Enviar un pedido en Postman (`201 Created`).
  * Reenviar inmediatamente la misma solicitud con la misma clave de idempotencia.
  * Mostrar que Postman responde `200 OK` con la misma orden.
  * Abrir terminal/SQLite y ejecutar: `SELECT COUNT(*) FROM orders WHERE idempotency_key = ...` y demostrar que solo existe 1 registro y no se duplicó el inventario.

* **3:00 - 3:45 | Demostración Rápida: Rechazo y Stock (Casos 4 y 5):**
  * Enviar pedido con `scenario: rejected` -> Mostrar que responde 402 y el stock regresa a 1.
  * Enviar pedido cuando no hay stock -> Mostrar el error `409 Out of stock` y verificar que el stock nunca queda negativo.

* **3:45 - 4:15 | Conclusiones Técnicas:**
  * Responder brevemente:
    1. *¿Qué estado persistieron?* Se persistió el estado transicional `payment_pending`, la reserva de stock y la `idempotency_key` única antes de invocar el cobro; y en el mock se persistió el cobro con su clave única.
    2. *¿Cómo evitaron duplicados?* Con la restricción de unicidad (`UNIQUE`) en SQLite y consultando el estado del pago antes de tomar decisiones.

---

## 📄 Paso 3: Plantilla para el PDF Final de Entrega

Copia el contenido siguiente en Google Docs o Word, inserta las capturas de pantalla que tomaste y descárgalo como PDF para subirlo a Moodle.

---

### [PORTADA]
**UNIVERSIDAD ESTATAL PENÍNSULA DE SANTA ELENA**  
**FACULTAD DE SISTEMAS Y TELECOMUNICACIONES**  
**ASIGNATURA:** Sistemas Distribuidos  
**TEMA:** Reto Técnico: Pedidos, Pagos Simulados e Idempotencia  

**Integrantes del Equipo (3 integrantes):**
1. [Nombre Integrante 1] - [Cédula/Matrícula]
2. [Nombre Integrante 2] - [Cédula/Matrícula]
3. [Nombre Integrante 3] - [Cédula/Matrícula]

* **Enlace al Repositorio de GitHub:** `https://github.com/Soulsilver-awsd/payday`
* **Enlace al Video de Demostración (3–5 min):** `[INSERTAR ENLACE DE YOUTUBE / DRIVE PÚBLICO AQUÍ]`
* **Ubicación de la Colección Postman:** `postman/payday.postman_collection.json` (dentro del repositorio)

---

### 1. Tabla Resumen de los 5 Casos de Prueba

| Caso | Qué se hace | Resultado Esperado | Resultado Obtenido | Estado |
| :--- | :--- | :--- | :--- | :---: |
| **1. Flujo exitoso** | Enviar `POST /orders` con `scenario: approved` y stock = 1. | Orden en `paid`, stock en 0, 1 cobro generado (`HTTP 201`). | Orden creada con `status: paid`, reserva consumida (`available: 0`) y cobro asociado. | ✅ Cumplido |
| **2. Repetición de solicitud** | Reenviar `POST /orders` con la misma `idempotency_key`. | Devuelve la orden original (`HTTP 200`), sin crear otra orden, reserva ni cobro. | Responde `HTTP 200 OK` con el mismo ID de pedido. Las tablas SQLite muestran exactamente 1 pedido y 1 cobro. | ✅ Cumplido |
| **3. Timeout tras cobro** | Enviar `POST /orders` con `scenario: timeout`. El mock registra cobro y simula pérdida de respuesta. | Backend reconcilia estado consultando `/payments/status` y confirma orden como `paid` sin duplicar cobro. | El backend captura el 504, consulta el pago persistido, reconcilia la orden a `paid` y mantiene el stock reservado. | ✅ Cumplido |
| **4. Pago rechazado** | Enviar `POST /orders` con `scenario: rejected`. | Orden en `payment_rejected` (`HTTP 402`) y la reserva de stock se libera (`available: 1`). | Responde `HTTP 402`. El inventario vuelve a estar disponible (`available: 1`) demostrando compensación. | ✅ Cumplido |
| **5. Otra intención de compra** | Enviar orden con clave B cuando el stock ya quedó en 0 por una orden previa. | Solicitud tratada como distinta; rechazada con `HTTP 409 Conflict (Out of stock)` sin stock negativo. | Responde `HTTP 409 Out of stock`. La restricción de SQLite garantiza que `available` nunca baja de 0. | ✅ Cumplido |

---

### 2. Evidencias de Ejecución (Capturas de Postman y SQLite)

#### Caso 1: Flujo Exitoso
* `[PEGAR AQUÍ CAPTURA DE POSTMAN CON HTTP 201 Y STATUS PAID]`
* `[PEGAR AQUÍ CAPTURA DE SQLITE MOSTRANDO LA TABLA ORDERS Y PAYMENTS]`

#### Caso 2: Repetición de Misma Solicitud (Idempotencia)
* `[PEGAR AQUÍ CAPTURA DE POSTMAN CON HTTP 200 OK Y EL MISMO ID]`
* `[PEGAR AQUÍ CAPTURA DE SQLITE MOSTRANDO COUNT(*) = 1]`

#### Caso 3: Respuesta Perdida tras Cobro y Recuperación
* `[PEGAR AQUÍ CAPTURA DE POSTMAN DE LA ORDEN RECUPERADA]`
* `[PEGAR AQUÍ CAPTURA DE POSTMAN DE GET /payments/status]`
* `[PEGAR AQUÍ CAPTURA DE SQLITE MOSTRANDO EL COBRO PERSISTIDO]`

#### Caso 4: Pago Rechazado y Compensación
* `[PEGAR AQUÍ CAPTURA DE POSTMAN CON HTTP 402]`
* `[PEGAR AQUÍ CAPTURA DE GET /inventory CON available = 1]`

#### Caso 5: Otra Intención de Compra (Stock Límite)
* `[PEGAR AQUÍ CAPTURA DE POSTMAN CON HTTP 409 OUT OF STOCK]`
* `[PEGAR AQUÍ CAPTURA DE SQLITE MOSTRANDO available = 0]`

---

### 3. Conclusiones Técnicas

#### ¿Qué estado persistieron para recuperarse?
Se implementó un patrón de persistencia en dos fases utilizando SQLite tanto en `order-api` como en `payment-api`:
1. **En Order API:** Antes de comunicarse con la pasarela de pagos, se reserva el inventario de forma transaccional y se persiste el pedido en estado inicial `payment_pending`, registrando la clave de idempotencia (`idempotency_key`) con restricción de unicidad (`UNIQUE`).
2. **En Payment Mock API:** Al recibir el intento de cobro bajo el escenario de timeout, el servicio mock persiste primero el registro del cobro con estado `approved` y su propia clave de idempotencia única antes de emitir la falla de red simulada (`HTTP 504 Gateway Timeout`).
3. **Reconciliación:** Gracias a esta persistencia previa, cuando ocurre una pérdida de respuesta, el backend de órdenes no asume el fracaso ni reintenta a ciegas, sino que consulta el endpoint idempotente `/payments/status?idempotency_key=...`. Al leer el cobro confirmado, transiciona el pedido a estado final `paid`.

#### ¿Cómo comprobaron que no hubo efectos duplicados?
La comprobación de ausencia de efectos duplicados se validó en tres niveles:
1. **A nivel de Base de Datos (Restricciones):** Las columnas `idempotency_key` en las tablas `orders` y `payments` cuentan con índices únicos (`UNIQUE`). Cualquier intento concurrente o repetido de insertar la misma clave es interceptado a nivel de motor SQLite, evitando duplicados a nivel físico.
2. **A nivel de Lógica de Aplicación:** Antes de ejecutar cualquier mutación o reserva de inventario, ambos servicios consultan si la clave ya existe. Si existe, devuelven la entidad previamente almacenada (`HTTP 200 OK`) con los mismos datos originales.
3. **A nivel de Inventario:** La tabla `inventory` cuenta con una restricción `CHECK (available >= 0)`. Tras repetir solicitudes con la misma clave y ejecutar compras competidoras con claves distintas, se demostró mediante consultas SQL que el stock nunca bajó de cero ni se reservó más de una unidad física por cada producto.
