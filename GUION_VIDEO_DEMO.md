# 🎬 Guion del Video Sincronizado con `demo_runner.py` (3 a 5 Minutos)

Este guion está **diseñado exactamente en el mismo orden que imprime [`demo_runner.py`](demo_runner.py)** en pantalla. 
De esta forma, pueden ejecutar `python demo_runner.py` en la terminal (o ir lanzando los pasos) y cada integrante va leyendo y explicando lo que va apareciendo en la consola.

---

## 👥 Reparto de Roles (3 Integrantes)

* **Integrante 1 (0:00 - 1:20):** Introducción + Caso 1 (Flujo Exitoso) + Caso 2 (Idempotencia / Reenvío).
* **Integrante 2 (1:20 - 2:40):** Caso 3 (Timeout y Recuperación sin cobro a ciegas) -> *¡El caso más importante de la rúbrica!*
* **Integrante 3 (2:40 - 4:00):** Caso 4 (Pago Rechazado y Compensación) + Caso 5 (Stock Límite) + Inspección SQLite y Conclusión.

---

## 🖥️ Preparación antes de Grabar

1. Abre **Terminal 1**: `payment-api` corriendo en el puerto **5001**.
2. Abre **Terminal 2**: `order-api` corriendo en el puerto **5000**.
3. Abre **Terminal 3**: Donde van a ejecutar `python demo_runner.py`.
4. Inicien la grabación (Meet / Zoom / OBS) con las cámaras de los 3 encendidas.

---

# 📜 Guion Sincronizado Minuto a Minuto

### ⏱️ MINUTO 0:00 - 0:35 | INTRODUCCIÓN

> **INTEGRANTE 1 (habla):**
> *"Buenas tardes, profesor. Somos el equipo conformado por [Nombre 1], [Nombre 2] y [Nombre 3]. Hoy presentamos el reto técnico de **Sistemas Distribuidos: Pedidos, pagos simulados e idempotencia con Flask y SQLite**.*
> 
> *Como pueden observar en pantalla, tenemos dos servicios locales activos: `order-api` en el puerto 5000 y el mock `payment-api` en el puerto 5001. Ambos persisten sus datos de forma independiente en SQLite.*
> 
> *Vamos a ejecutar nuestro script automatizado `demo_runner.py` para demostrar los 5 casos obligatorios de la rúbrica."*

*(Acción: Integrante 1 escribe en Terminal 3: `python demo_runner.py` y da Enter)*.

---

### ⏱️ MINUTO 0:35 - 1:00 | CASO 1: FLUJO EXITOSO

*(En pantalla aparece el banner: `CASO 1 · Flujo exitoso (approved)` y la respuesta `HTTP 201 Created`)*

> **INTEGRANTE 1 (habla):**
> *"Iniciamos con el **Caso 1: Flujo exitoso**. El script envía un pedido con `scenario: approved`.*
> 
> *Vemos que responde `HTTP 201 Created`. El pedido se registró con `status: paid`, se reservó 1 unidad de stock y se le asignó su referencia de pago `payment_ref`.*
> 
> *Inmediatamente se consulta el inventario con `GET /inventory` y observamos que el stock disponible pasó de 1 a 0."*

---

### ⏱️ MINUTO 1:00 - 1:30 | CASO 2: IDEMPOTENCIA / REENVÍO

*(En pantalla aparece el banner: `CASO 2 · Idempotencia / Reenvío (misma clave)` y `[OK] Verificación: mismo pedido, no se duplicó`)*

> **INTEGRANTE 1 (habla):**
> *"Ahora el **Caso 2: Repetición de la misma solicitud**.*
> 
> *El script reenvía exactamente el mismo pedido con la misma `idempotency_key`. Como pueden observar, el backend reconoce la clave existente y responde `HTTP 200 OK` devolviendo la orden original previamente creada.*
> 
> *El script verifica que el `order_id` es el mismo y que el stock continúa en 0. Se garantiza la idempotencia: **no se duplicó pedido, ni reserva, ni cobro**. Le doy el paso a mi compañero [Nombre 2] para el Caso 3."*

---

### ⏱️ MINUTO 1:30 - 2:40 | CASO 3: TIMEOUT Y RECUPERACIÓN

*(En pantalla aparece el banner: `CASO 3 · Timeout y recuperación sin cobro a ciegas`)*

> **INTEGRANTE 2 (habla):**
> *"Continuamos con el **Caso 3: Respuesta perdida tras el cobro**, el escenario central de este reto.*
> 
> *Aquí el cliente envía un pedido con `scenario: timeout`. El servicio de pago simulado **alcanza a registrar el cobro en su base de datos**, pero simula una pérdida de respuesta de red arrojando un `HTTP 504 Timeout`.*
> 
> *¿Qué hace nuestro backend? Nuestro backend **no reintenta a ciegas**, porque generaría un doble cobro. En su lugar, ejecuta el algoritmo de recuperación: captura el error y consulta el estado del pago al mock mediante `GET /payments/status` usando la misma clave de idempotencia.*
> 
> *Como vemos en la consola, el mock confirma que el pago ya estaba `approved`. Por lo tanto, `order-api` reconcilia el pedido dejándolo en estado final `paid` y responde `HTTP 201 Created`.*
> 
> *Luego el runner reenvía la misma clave y el backend responde `HTTP 200 OK` con la orden ya resuelta. Hemos recuperado el estado incierto sin duplicar cobros. Le paso la palabra a [Nombre 3]."*

---

### ⏱️ MINUTO 2:40 - 3:15 | CASO 4: PAGO RECHAZADO Y COMPENSACIÓN

*(En pantalla aparece el banner: `CASO 4 · Pago rechazado y compensación de inventario`)*

> **INTEGRANTE 3 (habla):**
> *"En el **Caso 4: Pago rechazado**, forzamos el rechazo enviando `scenario: rejected`.*
> 
> *El backend recibe el rechazo de la pasarela y responde `HTTP 402 Payment Required`. La orden queda registrada con estado `payment_rejected`.*
> 
> *Lo fundamental aquí es la **compensación**: como el pago no prosperó, el backend libera la reserva. Vemos en la consulta `GET /inventory` que el stock vuelve automáticamente a `available = 1`."*

---

### ⏱️ MINUTO 3:15 - 3:45 | CASO 5: OTRA INTENCIÓN DE COMPRA (STOCK LÍMITE)

*(En pantalla aparece el banner: `CASO 5 · Stock límite` y luego el error `HTTP 409 Conflict`)*

> **INTEGRANTE 3 (habla):**
> *"En el **Caso 5: Otra intención de compra**, probamos dos pedidos con claves distintas cuando solo queda 1 unidad en stock.*
> 
> *El primer pedido con la Clave A se procesa con éxito (`HTTP 201`) y agota el stock a 0.*
> 
> *Inmediatamente llega el segundo pedido con la Clave B. Como es una clave diferente, representa otra intención de compra. El sistema intenta reservar, pero como no hay existencias, rechaza la operación con `HTTP 409 Conflict: Out of stock`.*
> 
> *Observen que el stock permanece en 0. Gracias a la restricción en SQLite, nunca se produce sobreventa ni stock negativo."*

---

### ⏱️ MINUTO 3:45 - 4:20 | INSPECCIÓN SQLITE Y CONCLUSIONES

*(En pantalla aparece el mensaje: `Demo finalizada con éxito`)*

*(Acción: Integrante 3 ejecuta en la misma terminal: `python inspect_db.py`)*

> **INTEGRANTE 3 (habla):**
> *"Para finalizar y verificar los estados persistidos, ejecutamos nuestro script `python inspect_db.py`.*
> 
> *(Señala la salida en consola)*:
> *Aquí pueden comprobar directamente las tablas SQLite:*
> 1. *En `order.db`, cada clave única generó como máximo un solo pedido y el inventario mantuvo su coherencia.*
> 2. *En `payment.db`, cada cobro está persistido con su clave correspondiente sin registros duplicados.*
> 
> *Para concluir:*
> *Persistimos en SQLite la orden con su clave única y estado transicional antes de invocar el cobro; y en el mock persistimos el cobro antes del timeout. Así, mediante restricciones `UNIQUE`, control de inventario y consulta previa de estado, demostramos cómo recuperar un sistema distribuido ante fallas de red sin generar efectos duplicados.*
> 
> *Muchas gracias por su atención."*

---

## ⏱️ Control de Tiempos
* Si leen a velocidad normal mientras `demo_runner.py` avanza, el video durará entre **3:45 y 4:15 minutos**, cumpliendo perfectamente la regla de **3 a 5 minutos**.
* Si terminan de hablar antes de que termine el script, pueden dejar correr el script y comentar las líneas que van saliendo.
