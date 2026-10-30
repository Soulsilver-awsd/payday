from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError

from app.errors import APIError
from app.extensions import db
from app.models import Inventory, Order

orders_api_bp = Blueprint("orders_api", __name__)

INVENTORY_ID = 1


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


def _get_by_key(idempotency_key: str) -> Order | None:
    return db.session.scalar(
        select(Order).where(Order.idempotency_key == idempotency_key)
    )


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

    total_amount = _parse_total_amount(payload.get("total_amount", "0"))

    _ensure_inventory()
    reserved = db.session.execute(
        update(Inventory)
        .where(Inventory.id == INVENTORY_ID, Inventory.available >= 1)
        .values(available=Inventory.available - 1)
    )

    if reserved.rowcount == 0:
        # A concurrent request may have consumed the stock for this same key.
        db.session.rollback()
        existing = _get_by_key(idempotency_key)
        if existing is not None:
            return jsonify(existing.to_dict()), 200
        raise APIError("Out of stock", status_code=409)

    order = Order(
        customer_id=customer_id.strip(),
        idempotency_key=idempotency_key,
        items_reserved=1,
        status="reserved",
        total_amount=total_amount,
        currency=currency.upper(),
    )
    db.session.add(order)

    try:
        db.session.commit()
    except IntegrityError:
        # The UNIQUE constraint won the race: undo the stock decrement and
        # return the order created by the other request.
        db.session.rollback()
        existing = _get_by_key(idempotency_key)
        if existing is None:
            raise
        return jsonify(existing.to_dict()), 200

    return jsonify(order.to_dict()), 201
