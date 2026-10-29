from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.errors import APIError
from app.extensions import db
from app.models import Order

orders_bp = Blueprint("orders", __name__)


@orders_bp.get("")
def list_orders():
    orders = db.session.scalars(select(Order).order_by(Order.id)).all()
    return jsonify({"items": [order.to_dict() for order in orders]})


@orders_bp.post("")
def create_order():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise APIError("Request body must be a JSON object")

    customer_id = payload.get("customer_id")
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise APIError("customer_id is required and must be a non-empty string")

    currency = payload.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3:
        raise APIError("currency must be a 3-letter ISO code")

    try:
        total_amount = Decimal(str(payload.get("total_amount", "0")))
    except (InvalidOperation, ValueError):
        raise APIError("total_amount must be a number") from None

    if total_amount < 0:
        raise APIError("total_amount must be greater than or equal to 0")

    order = Order(
        customer_id=customer_id.strip(),
        status=payload.get("status", "pending"),
        total_amount=total_amount,
        currency=currency.upper(),
    )
    db.session.add(order)
    db.session.commit()

    return jsonify(order.to_dict()), 201


@orders_bp.get("/<int:order_id>")
def get_order(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        raise APIError("Order not found", status_code=404)
    return jsonify(order.to_dict())
