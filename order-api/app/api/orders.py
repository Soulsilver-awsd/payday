from decimal import Decimal, InvalidOperation

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from app.errors import APIError
from app.extensions import db
from app.models import Inventory, Order
from app.services.payment_client import PaymentClient
from app.services.payment_recovery import resolve_payment_after_timeout

orders_api_bp = Blueprint("orders_api", __name__)

INVENTORY_ID = 1
PAYMENT_SCENARIOS = {"approved", "rejected", "timeout"}
MAX_PAYMENT_ATTEMPTS = 2


def _parse_total_amount(raw) -> Decimal:
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise APIError("total_amount must be a number") from None

    if amount < 0:
        raise APIError("total_amount must be greater than or equal to 0")
    return amount


def _ensure_inventory() -> None:
    """Create the initial stock row once, without resetting consumed stock."""
    db.session.execute(
        sqlite_insert(Inventory)
        .values(id=INVENTORY_ID, available=1)
        .on_conflict_do_nothing(index_elements=["id"])
    )


def _reserve_stock() -> bool:
    _ensure_inventory()
    result = db.session.execute(
        update(Inventory)
        .where(Inventory.id == INVENTORY_ID, Inventory.available >= 1)
        .values(available=Inventory.available - 1)
    )
    return result.rowcount == 1


def _release_stock() -> None:
    db.session.execute(
        update(Inventory)
        .where(Inventory.id == INVENTORY_ID, Inventory.available < 1)
        .values(available=Inventory.available + 1)
    )


def _get_by_key(idempotency_key: str) -> Order | None:
    return db.session.scalar(
        select(Order).where(Order.idempotency_key == idempotency_key)
    )


def _payment_body(response) -> dict:
    if response is None:
        return {}
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _fetch_payment_status(client: PaymentClient, idempotency_key: str) -> dict:
    try:
        response = client.get(
            "/payments/status",
            params={"idempotency_key": idempotency_key},
        )
    except requests.RequestException:
        return {}

    if response.status_code != 200:
        return {}
    return _payment_body(response)


def _charge_with_recovery(
    client: PaymentClient,
    idempotency_key: str,
    amount: Decimal,
    scenario: str,
) -> tuple[str, dict]:
    """Charge the Payment Mock and reconcile uncertain responses by key."""
    last_response = None

    for _ in range(MAX_PAYMENT_ATTEMPTS):
        try:
            response = client.pay(idempotency_key, amount, scenario)
        except requests.RequestException:
            response = None

        if response is not None:
            last_response = response
            if response.status_code in {200, 201}:
                body = _payment_body(response)
                status = body.get("status")
                if status in PAYMENT_SCENARIOS:
                    return status, body
                return "error", body

            if response.status_code != 504:
                return "error", _payment_body(response)

        # Timeout or network failure: always query by idempotency_key first.
        decision = resolve_payment_after_timeout(idempotency_key, client)

        if decision == "confirm":
            return "approved", _fetch_payment_status(client, idempotency_key)

        if decision == "cancel":
            return "timeout", _payment_body(last_response)

        # "retry": the Payment Mock has no record, so retrying is safe.

    return "timeout", _payment_body(last_response)


def _payment_ref(payment: dict) -> str | None:
    value = payment.get("payment_id") or payment.get("id")
    return str(value) if value is not None else None


@orders_api_bp.post("/orders")
def create_order():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise APIError("Request body must be a JSON object")

    idempotency_key = payload.get("idempotency_key")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise APIError("idempotency_key is required and must be a non-empty string")
    idempotency_key = idempotency_key.strip()

    existing = _get_by_key(idempotency_key)
    if existing is not None:
        return jsonify(existing.to_dict()), 200

    customer_id = payload.get("customer_id", "guest")
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise APIError("customer_id must be a non-empty string")

    currency = payload.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3:
        raise APIError("currency must be a 3-letter ISO code")

    scenario = payload.get("scenario", "approved")
    if scenario not in PAYMENT_SCENARIOS:
        raise APIError("scenario must be one of: approved, rejected, timeout")

    total_amount = _parse_total_amount(payload.get("total_amount", "0"))

    if not _reserve_stock():
        db.session.rollback()
        existing = _get_by_key(idempotency_key)
        if existing is not None:
            return jsonify(existing.to_dict()), 200
        raise APIError("Out of stock", status_code=409)

    order = Order(
        customer_id=customer_id.strip(),
        idempotency_key=idempotency_key,
        items_reserved=1,
        status="payment_pending",
        total_amount=total_amount,
        currency=currency.upper(),
    )
    db.session.add(order)

    try:
        db.session.commit()
    except IntegrityError:
        # The UNIQUE constraint won the race: undo the reservation and return
        # the order created by the other request.
        db.session.rollback()
        existing = _get_by_key(idempotency_key)
        if existing is not None:
            return jsonify(existing.to_dict()), 200
        raise

    client = PaymentClient(
        current_app.config["PAYMENT_API_URL"],
        current_app.config["PAYMENT_TIMEOUT"],
    )
    outcome, payment = _charge_with_recovery(
        client,
        idempotency_key,
        total_amount,
        scenario,
    )

    order.payment_ref = _payment_ref(payment)

    if outcome == "approved":
        order.status = "paid"
        order.items_reserved = 1
        db.session.commit()
        return jsonify(order.to_dict()), 201

    # Payment rejected, timed out or failed: compensate the reservation.
    _release_stock()
    order.items_reserved = 0

    if outcome == "rejected":
        order.status = "payment_rejected"
        status_code = 402
    elif outcome == "timeout":
        order.status = "payment_timeout"
        status_code = 504
    else:
        order.status = "payment_error"
        status_code = 502

    db.session.commit()
    return jsonify(order.to_dict()), status_code


@orders_api_bp.get("/orders/<int:order_id>")
def get_order_by_id(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        raise APIError("Order not found", status_code=404)
    return jsonify(order.to_dict()), 200


@orders_api_bp.get("/orders")
def get_orders():
    idempotency_key = request.args.get("idempotency_key")
    if idempotency_key:
        order = _get_by_key(idempotency_key.strip())
        if order is None:
            raise APIError("Order not found", status_code=404)
        return jsonify(order.to_dict()), 200

    orders = db.session.scalars(select(Order).order_by(Order.id)).all()
    return jsonify({"items": [order.to_dict() for order in orders]}), 200


@orders_api_bp.get("/inventory")
def get_inventory():
    _ensure_inventory()
    inv = db.session.get(Inventory, INVENTORY_ID)
    return jsonify({"available": inv.available if inv else 0}), 200


@orders_api_bp.post("/demo/reset")
def demo_reset():
    if not current_app.config.get("DEMO_MODE", False):
        raise APIError("Not found", status_code=404)

    db.session.execute(delete(Order))
    _ensure_inventory()
    db.session.execute(
        update(Inventory)
        .where(Inventory.id == INVENTORY_ID)
        .values(available=1)
    )
    db.session.commit()

    return jsonify({"status": "reset", "available": 1})
