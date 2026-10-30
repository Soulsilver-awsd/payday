from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"
    __table_args__ = (
        db.CheckConstraint("items_reserved IN (0, 1)", name="ck_orders_items_reserved"),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(64), nullable=False, index=True)
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True, index=True)
    items_reserved = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(32), nullable=False, default="pending")
    payment_ref = db.Column(db.String(128), nullable=True)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.id,
            "customer_id": self.customer_id,
            "idempotency_key": self.idempotency_key,
            "items_reserved": self.items_reserved,
            "status": self.status,
            "payment_ref": self.payment_ref,
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Order {self.id} {self.status}>"
