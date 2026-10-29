from flask import Blueprint

from app.api.v1.payments import payments_bp

api_v1 = Blueprint("api_v1", __name__)

api_v1.register_blueprint(payments_bp, url_prefix="/payments")
