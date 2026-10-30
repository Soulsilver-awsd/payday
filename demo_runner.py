#!/usr/bin/env python3
"""Demo de idempotencia para Order API + Payment Mock."""

import json
import os
import time
import uuid

import requests

ORDER_API_URL = os.getenv("ORDER_API_URL", "http://localhost:5000").rstrip("/")
PAUSE_SECONDS = 2.0
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
        "customer_id": "demo-customer",
        "total_amount": "9.90",
        "currency": "USD",
        "scenario": "approved",
    }

    print("DEMO · Idempotencia de pedidos y pagos")
    print(f"Order API: {ORDER_API_URL}")
    print("Cada caso parte de stock inicial = 1.")

    with requests.Session() as session:
        banner("PREPARACIÓN · Reset de inventario")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 1 · Flujo exitoso (approved)")
        first_response = post_order(session, approved_request)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 2 · Idempotencia / Reenvío (misma clave)")
        replay_response = post_order(session, approved_request)

        first_id = order_id_from(first_response)
        replay_id = order_id_from(replay_response)
        if first_id is not None and first_id == replay_id:
            print(f"   Verificación: mismo pedido ({first_id}), no se duplicó.")
        elif first_id is not None:
            print(f"   Verificación: pedido distinto ({first_id} != {replay_id}).")

        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 3")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 3 · Timeout y recuperación")
        post_order(session, timeout_request)
        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 4")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 4 · Pago rechazado y compensación")
        post_order(session, rejected_request)
        time.sleep(PAUSE_SECONDS)

        banner("PREPARACIÓN · Reset de inventario para el caso 5")
        reset_demo(session)
        time.sleep(PAUSE_SECONDS)

        banner("CASO 5 · Stock límite")
        post_order(session, stock_request)
        print("   El stock quedó en 0; la siguiente clave debe recibir 409.")
        time.sleep(PAUSE_SECONDS)
        post_order(session, stock_guard_request)

    print()
    print("Demo finalizada.")


if __name__ == "__main__":
    main()
