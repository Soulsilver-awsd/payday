from flask import Flask

from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import db, migrate


def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so they are registered on the SQLAlchemy metadata.
    from app import models  # noqa: F401

    from app.api.health import health_bp
    from app.api.orders import orders_api_bp
    from app.api.v1 import api_v1

    app.register_blueprint(health_bp)
    app.register_blueprint(orders_api_bp)
    app.register_blueprint(api_v1, url_prefix="/api/v1")

    register_error_handlers(app)

    return app
