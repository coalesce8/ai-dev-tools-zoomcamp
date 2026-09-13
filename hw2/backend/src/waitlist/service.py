"""Transition and enrichment logic, kept out of route handlers."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from waitlist.db import utcnow
from waitlist.models import Party
from waitlist.schemas import EditPartyInput, NewPartyInput, PartyOut, PartyStatus

TERMINAL_STATUSES: tuple[PartyStatus, ...] = ("seated", "no_show", "cancelled")


def _waiting_positions(db: Session) -> dict[str, int]:
    ids = db.scalars(select(Party.id).where(Party.status == "waiting").order_by(Party.created_at)).all()
    return {party_id: index + 1 for index, party_id in enumerate(ids)}


def enrich(db: Session, record: Party, positions: dict[str, int] | None = None) -> PartyOut:
    if record.status == "waiting":
        position = (positions if positions is not None else _waiting_positions(db)).get(record.id)
    else:
        position = None
    end = record.ended_at or utcnow()
    waiting_minutes = max(0, round((end - record.created_at).total_seconds() / 60))
    is_overdue = (
        record.status == "waiting"
        and record.quoted_minutes is not None
        and waiting_minutes > record.quoted_minutes
    )
    return PartyOut(
        id=record.id,
        name=record.name,
        party_size=record.party_size,
        phone=record.phone,
        quoted_minutes=record.quoted_minutes,
        status=record.status,
        created_at=record.created_at,
        ended_at=record.ended_at,
        position=position,
        waiting_minutes=waiting_minutes,
        is_overdue=is_overdue,
    )


def list_parties(db: Session, status: PartyStatus) -> list[PartyOut]:
    records = db.scalars(select(Party).where(Party.status == status).order_by(Party.created_at)).all()
    positions = _waiting_positions(db) if status == "waiting" else {}
    return [enrich(db, record, positions) for record in records]


def add_party(db: Session, payload: NewPartyInput) -> PartyOut:
    record = Party(
        name=payload.name,
        party_size=payload.party_size,
        phone=payload.phone,
        quoted_minutes=payload.quoted_minutes,
        status="waiting",
        created_at=utcnow(),
        ended_at=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return enrich(db, record)


def get_party_or_404(db: Session, party_id: str) -> Party:
    record = db.get(Party, party_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Party {party_id} not found")
    return record


def update_party(db: Session, party_id: str, payload: EditPartyInput) -> PartyOut:
    record = get_party_or_404(db, party_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return enrich(db, record)


def _transition(db: Session, party_id: str, next_status: PartyStatus) -> PartyOut:
    record = get_party_or_404(db, party_id)
    if record.status != "waiting":
        raise HTTPException(
            status_code=409,
            detail=f"Party {party_id} is not waiting (current status: {record.status}).",
        )
    record.status = next_status
    record.ended_at = utcnow()
    db.commit()
    db.refresh(record)
    return enrich(db, record)


def seat_party(db: Session, party_id: str) -> PartyOut:
    return _transition(db, party_id, "seated")


def no_show_party(db: Session, party_id: str) -> PartyOut:
    return _transition(db, party_id, "no_show")


def cancel_party(db: Session, party_id: str) -> PartyOut:
    return _transition(db, party_id, "cancelled")


def restore_party(db: Session, party_id: str) -> PartyOut:
    record = get_party_or_404(db, party_id)
    if record.status == "waiting":
        raise HTTPException(status_code=409, detail=f"Party {party_id} is already waiting.")
    record.status = "waiting"
    record.ended_at = None
    db.commit()
    db.refresh(record)
    return enrich(db, record)
