from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from waitlist import service
from waitlist.db import get_db
from waitlist.schemas import EditPartyInput, NewPartyInput, PartyOut, PartyStatus

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/parties", response_model=list[PartyOut])
def list_parties(status: PartyStatus = "waiting", db: Session = Depends(get_db)) -> list[PartyOut]:
    return service.list_parties(db, status)


@router.post("/parties", response_model=PartyOut, status_code=201)
def add_party(payload: NewPartyInput, db: Session = Depends(get_db)) -> PartyOut:
    return service.add_party(db, payload)


@router.patch("/parties/{party_id}", response_model=PartyOut)
def update_party(party_id: str, payload: EditPartyInput, db: Session = Depends(get_db)) -> PartyOut:
    return service.update_party(db, party_id, payload)


@router.post("/parties/{party_id}/seat", response_model=PartyOut)
def seat_party(party_id: str, db: Session = Depends(get_db)) -> PartyOut:
    return service.seat_party(db, party_id)


@router.post("/parties/{party_id}/no-show", response_model=PartyOut)
def no_show_party(party_id: str, db: Session = Depends(get_db)) -> PartyOut:
    return service.no_show_party(db, party_id)


@router.post("/parties/{party_id}/cancel", response_model=PartyOut)
def cancel_party(party_id: str, db: Session = Depends(get_db)) -> PartyOut:
    return service.cancel_party(db, party_id)


@router.post("/parties/{party_id}/restore", response_model=PartyOut)
def restore_party(party_id: str, db: Session = Depends(get_db)) -> PartyOut:
    return service.restore_party(db, party_id)
