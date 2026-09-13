from fastapi import APIRouter, Depends

from waitlist import service
from waitlist.schemas import EditPartyInput, NewPartyInput, PartyOut, PartyStatus
from waitlist.store import PartyStore
from waitlist.store import store as default_store

router = APIRouter(prefix="/api")


def get_store() -> PartyStore:
    return default_store


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/parties", response_model=list[PartyOut])
def list_parties(status: PartyStatus = "waiting", store: PartyStore = Depends(get_store)) -> list[PartyOut]:
    return service.list_parties(store, status)


@router.post("/parties", response_model=PartyOut, status_code=201)
def add_party(payload: NewPartyInput, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.add_party(store, payload)


@router.patch("/parties/{party_id}", response_model=PartyOut)
def update_party(party_id: str, payload: EditPartyInput, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.update_party(store, party_id, payload)


@router.post("/parties/{party_id}/seat", response_model=PartyOut)
def seat_party(party_id: str, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.seat_party(store, party_id)


@router.post("/parties/{party_id}/no-show", response_model=PartyOut)
def no_show_party(party_id: str, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.no_show_party(store, party_id)


@router.post("/parties/{party_id}/cancel", response_model=PartyOut)
def cancel_party(party_id: str, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.cancel_party(store, party_id)


@router.post("/parties/{party_id}/restore", response_model=PartyOut)
def restore_party(party_id: str, store: PartyStore = Depends(get_store)) -> PartyOut:
    return service.restore_party(store, party_id)
