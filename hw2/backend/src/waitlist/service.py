"""Transition and enrichment logic, kept out of route handlers."""

from fastapi import HTTPException

from waitlist.schemas import EditPartyInput, NewPartyInput, PartyOut, PartyStatus
from waitlist.store import PartyRecord, PartyStore, utcnow

TERMINAL_STATUSES: tuple[PartyStatus, ...] = ("seated", "no_show", "cancelled")


def enrich(store: PartyStore, record: PartyRecord) -> PartyOut:
    position = store.waiting_positions().get(record.id) if record.status == "waiting" else None
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


def list_parties(store: PartyStore, status: PartyStatus) -> list[PartyOut]:
    return [enrich(store, record) for record in store.by_status(status)]


def add_party(store: PartyStore, payload: NewPartyInput) -> PartyOut:
    record = store.add(
        name=payload.name,
        party_size=payload.party_size,
        phone=payload.phone,
        quoted_minutes=payload.quoted_minutes,
    )
    return enrich(store, record)


def get_party_or_404(store: PartyStore, party_id: str) -> PartyRecord:
    record = store.get(party_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Party {party_id} not found")
    return record


def update_party(store: PartyStore, party_id: str, payload: EditPartyInput) -> PartyOut:
    record = get_party_or_404(store, party_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    return enrich(store, record)


def _transition(store: PartyStore, party_id: str, next_status: PartyStatus) -> PartyOut:
    record = get_party_or_404(store, party_id)
    if record.status != "waiting":
        raise HTTPException(
            status_code=409,
            detail=f"Party {party_id} is not waiting (current status: {record.status}).",
        )
    record.status = next_status
    record.ended_at = utcnow()
    return enrich(store, record)


def seat_party(store: PartyStore, party_id: str) -> PartyOut:
    return _transition(store, party_id, "seated")


def no_show_party(store: PartyStore, party_id: str) -> PartyOut:
    return _transition(store, party_id, "no_show")


def cancel_party(store: PartyStore, party_id: str) -> PartyOut:
    return _transition(store, party_id, "cancelled")


def restore_party(store: PartyStore, party_id: str) -> PartyOut:
    record = get_party_or_404(store, party_id)
    if record.status == "waiting":
        raise HTTPException(status_code=409, detail=f"Party {party_id} is already waiting.")
    record.status = "waiting"
    record.ended_at = None
    return enrich(store, record)
