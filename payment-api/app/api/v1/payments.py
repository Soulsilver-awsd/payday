from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.errors import APIError
from app.extensions import db
from app.models import Payment

payments_bp = Blueprint("payments", __name__)


@payments_bp.get("")
def list_payments():
    payments = db.session.scalars(select(Payment).order_by(Payment.id)).all()
    return jsonify({"items": [payment.to_dict() for payment in payments]})


@payments_bp.post("")
def create_payment():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise APIError("Request body must be a JSON object")

    order_id = payload.get("order_id")
    if not isinstance(order_id, str) or not order_id.strip():
        raise APIError("order_id is required and must be a non-empty string")

    currency = payload.get("currency", "USD")
    if not isinstance(currency, str) or len(currency) != 3:
        raise APIError("currency must be a 3-letter ISO code")

    try:
        amount = Decimal(str(payload.get("amount")))
    except (InvalidOperation, ValueError):
        raise APIError("amount is required and must be a number") from None

    if amount <= 0:
        raise APIError("amount must be greater than 0")

    payment = Payment(
        order_id=order_id.strip(),
        status=payload.get("status", "pending"),
        amount=amount,
        currency=currency.upper(),
        provider=payload.get("provider", "manual"),
        provider_reference=payload.get("provider_reference"),
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify(payment.to_dict()), 201


@payments_bp.get("/<int:payment_id>")
def get_payment(payment_id: int):
    payment = db.session.get(Payment, payment_id)
    if payment is None:
        raise APIError("Payment not found", status_code=404)
    return jsonify(payment.to_dict())
