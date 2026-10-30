from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.errors import APIError
from app.extensions import db
from app.models import Payment

pay_bp = Blueprint("pay", __name__)

SCENARIOS = {"approved", "rejected", "timeout"}


def _parse_amount(raw) -> Decimal:
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise APIError("amount is required and must be a number") from None

    if amount <= 0:
        raise APIError("amount must be greater than 0")
    return amount


@pay_bp.post("/pay")
def pay():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise APIError("Request body must be a JSON object")

    idempotency_key = payload.get("idempotency_key")
    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise APIError("idempotency_key is required and must be a non-empty string")
    idempotency_key = idempotency_key.strip()

    existing = db.session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return jsonify(existing.to_dict()), 200

    scenario = payload.get("scenario", "approved")
    if scenario not in SCENARIOS:
        raise APIError("scenario must be one of: approved, rejected, timeout")

    payment = Payment(
        idempotency_key=idempotency_key,
        status=scenario,
        amount=_parse_amount(payload.get("amount")),
        currency="USD",
        provider="mock",
    )
    db.session.add(payment)

    try:
        db.session.commit()
    except IntegrityError:
        # A concurrent request inserted the same key; return that payment.
        db.session.rollback()
        existing = db.session.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        return jsonify(existing.to_dict()), 200

    if scenario == "timeout":
        # The charge is already persisted, but the client sees a network failure.
        return jsonify({"error": "timeout", "payment_id": payment.id}), 504

    return jsonify(payment.to_dict()), 201
