import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from waitlist.db import Base, UTCDateTime, utcnow


def _new_id() -> str:
    return str(uuid.uuid4())


class Party(Base):
    __tablename__ = "parties"
    __table_args__ = (
        CheckConstraint("party_size >= 1", name="ck_parties_party_size_positive"),
        CheckConstraint(
            "quoted_minutes IS NULL OR quoted_minutes >= 0",
            name="ck_parties_quoted_minutes_non_negative",
        ),
        CheckConstraint(
            "(status = 'waiting' AND ended_at IS NULL) OR (status != 'waiting' AND ended_at IS NOT NULL)",
            name="ck_parties_waiting_iff_ended_at_null",
        ),
        Index("ix_parties_status_created_at", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    party_size: Mapped[int] = mapped_column(nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quoted_minutes: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
