"""In-memory mock database. Swap for a real persistence layer later.

Keeps the same shape a SQLAlchemy-backed store would have: records addressed by id,
mutated in place, nothing ever deleted.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from waitlist.schemas import PartyStatus


@dataclass
class PartyRecord:
    id: str
    name: str
    party_size: int
    phone: str | None
    quoted_minutes: int | None
    status: PartyStatus
    created_at: datetime
    ended_at: datetime | None


def utcnow() -> datetime:
    return datetime.now(UTC)


class PartyStore:
    def __init__(self) -> None:
        self._records: dict[str, PartyRecord] = {}

    def reset(self) -> None:
        self._records.clear()

    def add(
        self, *, name: str, party_size: int, phone: str | None, quoted_minutes: int | None
    ) -> PartyRecord:
        record = PartyRecord(
            id=str(uuid4()),
            name=name,
            party_size=party_size,
            phone=phone,
            quoted_minutes=quoted_minutes,
            status="waiting",
            created_at=utcnow(),
            ended_at=None,
        )
        self._records[record.id] = record
        return record

    def get(self, party_id: str) -> PartyRecord | None:
        return self._records.get(party_id)

    def all(self) -> list[PartyRecord]:
        return list(self._records.values())

    def by_status(self, status: PartyStatus) -> list[PartyRecord]:
        return sorted(
            (r for r in self._records.values() if r.status == status),
            key=lambda r: r.created_at,
        )

    def waiting_positions(self) -> dict[str, int]:
        waiting = self.by_status("waiting")
        return {record.id: index + 1 for index, record in enumerate(waiting)}


store = PartyStore()
