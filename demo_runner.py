#!/usr/bin/env python3
"""Demo de idempotencia para Order API + Payment Mock."""

import json
import os
import time
import uuid

import requests

ORDER_API_URL = os.getenv("ORDER_API_URL", "http://localhost:5000").rstrip("/")
PAYMENT_API_URL = os.getenv("PAYMENT_API_URL", "http://localhost:5001").rstrip("/")
PAUSE_SECONDS = 1.5
REQUEST_TIMEOUT = 15


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def print_response(response: requests.Response) -> None:
    print(f"<< HTTP {response.status_code} {response.reason}")
    try:
        body = response.json()
    except ValueError:
        print(response.text or "<sin cuerpo>")
        return
    print(json.dumps(body, indent=2, ensure_ascii=False))


def post_order(session: requests.Session, payload: dict) -> requests.Response | None:
    url = f"{ORDER_API_URL}/orders"
    print(f">> POST {url}")
    print("   Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        response = session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"<< Sin respuesta HTTP (error de red/timeout): {exc}")
        return None

    print_response(response)
    return response


def order_id_from(response: requests.Response | None):
    if response is None:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("order_id", body.get("id"))


def check_inventory(session: requests.Session) -> None:
    url = f"{ORDER_API_URL}/inventory"
    print(f">> GET {url}")
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        print_response(response)
    except requests.RequestException as exc:
        print(f"<< Error consultando inventario: {exc}")


def check_payment_mock_status(session: requests.Session, idempotency_key: str) -> None:
    url = f"{PAYMENT_API_URL}/payments/status"
    print(f">> GET {url}?idempotency_key={idempotency_key}")
    try:
        response = session.get(url, params={"idempotency_key": idempotency_key}, timeout=REQUEST_TIMEOUT)
        print_response(response)
    except requests.RequestException as exc:
        print(f"<< Error consultando mock de pagos: {exc}")


def reset_demo(session: requests.Session) -> None:
    url = f"{ORDER_API_URL}/demo/reset"
    print(f">> POST {url}")

    try:
        response = session.post(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"<< Sin respuesta HTTP (error de red/timeout): {exc}")
        return

    print_response(response)


def main() -> None:
    run_id = uuid.uuid4().hex[:8]

    approved_request = {
        "idempotency_key": f"demo-{run_id}-approved",
        "customer_id": "demo-customer",
        "total_amount": "49.90",
        "currency": "USD",
        "scenario": "approved",
    }
    timeout_request = {
        "idempotency_key": f"demo-{run_id}-timeout",
        "customer_id": "demo-customer",
        "total_amount": "19.90",
        "currency": "USD",
        "scenario": "timeout",
    }
    rejected_request = {
        "idempotency_key": f"demo-{run_id}-rejected",
        "customer_id": "demo-customer",
        "total_amount": "29.90",
        "currency": "USD",
        "scenario": "rejected",
    }
    stock_request = {
        "idempotency_key": f"demo-{run_id}-stock",
        "customer_id": "demo-customer",
        "total_amount": "9.90",
        "currency": "USD",
        "scenario": "approved",
    }
    stock_guard_request = {
        "idempotency_key": f"demo-{run_id}-stock-guard",
        "customer_id": "demo-customer-2",
        "total_amount": "9.90",
        "currency": "USD",
        "scenario": "approved",
    }

    print("DEMO · Idempotencia de pedidos y pagos")
    print(f"Order API:   {ORDER_API_URL}")
    print(f"Payment API: {PAYMENT_API_URL}")
    print("Cada caso parte de stock inicial = 1.")

    with requests.Session() as session:
        banner("PREPARACIÓN · Reset de inventario")
        reset_demo(session)
        check_inventory(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 1 · Flujo exitoso (approved)")
        first_response = post_order(session, approved_request)
        check_inventory(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 2 · Idempotencia / Reenvío (misma clave)")
        replay_response = post_order(session, approved_request)

        first_id = order_id_from(first_response)
        replay_id = order_id_from(replay_response)
        if first_id is not None and first_id == replay_id:
            print(f"   [OK] Verificación: mismo pedido ({first_id}), no se duplicó.")
        elif first_id is not None:
            print(f"   [ERROR] Verificación: pedido distinto ({first_id} != {replay_id}).")

        check_inventory(session)
        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 3")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 3 · Timeout y recuperación sin cobro a ciegas")
        t_resp = post_order(session, timeout_request)
        print("   Verificación en Mock de Pago:")
        check_payment_mock_status(session, timeout_request["idempotency_key"])
        print("   Reenvío con la misma clave (debe retornar 200 con la orden ya pagada):")
        post_order(session, timeout_request)
        check_inventory(session)
        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 4")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 4 · Pago rechazado y compensación de inventario")
        post_order(session, rejected_request)
        print("   El inventario debe haberse liberado (available = 1):")
        check_inventory(session)
        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 5")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 5 · Otra intención de compra (Stock límite = 1)")
        print("1. Primer pedido con clave única (consume el único stock):")
        post_order(session, stock_request)
        check_inventory(session)
        print("2. Segundo pedido con OTRA clave distinta (debe recibir 409 Out of stock):")
        time.sleep(PAUSE_SECONDS)
        post_order(session, stock_guard_request)
        print("   El stock debe mantenerse en 0 (nunca negativo):")
        check_inventory(session)

    print()
    print("=" * 72)
    print("Demo finalizada con éxito. Todos los casos cubiertos.")
    print("=" * 72)


if __name__ == "__main__":
    main()
