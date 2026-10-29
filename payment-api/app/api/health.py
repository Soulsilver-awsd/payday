from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__)

SERVICE_NAME = "payment-api"


@health_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": SERVICE_NAME})


@health_bp.get("/health/ready")
def readiness():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify({"status": "unavailable", "database": "down"}), 503
    return jsonify({"status": "ok", "database": "up"})
