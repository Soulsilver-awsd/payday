#!/usr/bin/env python3
"""Script de utilidad para inspeccionar SQLite en vivo (orders, inventory y payments)."""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ORDER_DB = BASE_DIR / "order-api" / "order.db"
PAYMENT_DB = BASE_DIR / "payment-api" / "payment.db"


def inspect_orders() -> None:
    print("=" * 60)
    print(" [ORDER-API] -> order.db")
    print("=" * 60)

    if not ORDER_DB.exists():
        print(f"No existe el archivo {ORDER_DB} todavia.")
        return

    conn = sqlite3.connect(ORDER_DB)
    cursor = conn.cursor()

    # Inventario
    print("\n--- INVENTORY ---")
    try:
        rows = cursor.execute("SELECT id, available, updated_at FROM inventory").fetchall()
        if not rows:
            print("  (Sin registros en inventory)")
        for r in rows:
            print(f"  ID: {r[0]} | Stock disponible: {r[1]} | Actualizado: {r[2]}")
    except sqlite3.OperationalError as e:
        print(f"  Error consultando inventory: {e}")

    # Órdenes
    print("\n--- ORDERS ---")
    try:
        rows = cursor.execute(
            "SELECT id, idempotency_key, customer_id, total_amount, status, items_reserved, payment_ref, created_at FROM orders"
        ).fetchall()
        if not rows:
            print("  (Sin ordenes registradas)")
        for r in rows:
            print(
                f"  ID: {r[0]} | Clave: {r[1]} | Cliente: {r[2]} | Total: ${r[3]} | Estado: {r[4]} | Reserva: {r[5]} | Ref Pago: {r[6]}"
            )
    except sqlite3.OperationalError as e:
        print(f"  Error consultando orders: {e}")

    conn.close()


def inspect_payments() -> None:
    print("\n" + "=" * 60)
    print(" [PAYMENT-API] -> payment.db")
    print("=" * 60)

    if not PAYMENT_DB.exists():
        print(f"No existe el archivo {PAYMENT_DB} todavia.")
        return

    conn = sqlite3.connect(PAYMENT_DB)
    cursor = conn.cursor()

    print("\n--- PAYMENTS ---")
    try:
        rows = cursor.execute(
            "SELECT id, idempotency_key, amount, currency, status, provider, created_at FROM payments"
        ).fetchall()
        if not rows:
            print("  (Sin pagos registrados)")
        for r in rows:
            print(
                f"  ID: {r[0]} | Clave: {r[1]} | Monto: ${r[2]} {r[3]} | Estado: {r[4]} | Proveedor: {r[5]}"
            )
    except sqlite3.OperationalError as e:
        print(f"  Error consultando payments: {e}")

    conn.close()
    print("=" * 60 + "\n")


def main() -> None:
    inspect_orders()
    inspect_payments()


if __name__ == "__main__":
    main()
