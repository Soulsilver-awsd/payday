from datetime import datetime, timezone

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Inventory(db.Model):
    """Single-row stock ledger for the demo (one unit available initially)."""

    __tablename__ = "inventory"
    __table_args__ = (
        db.CheckConstraint("available >= 0", name="ck_inventory_available_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    available = db.Column(db.Integer, nullable=False, default=1)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<Inventory {self.id} available={self.available}>"
