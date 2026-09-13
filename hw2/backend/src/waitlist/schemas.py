from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PartyStatus = Literal["waiting", "seated", "no_show", "cancelled"]


class PartyOut(BaseModel):
    id: str
    name: str
    party_size: int
    phone: str | None
    quoted_minutes: int | None
    status: PartyStatus
    created_at: datetime
    ended_at: datetime | None
    position: int | None
    waiting_minutes: int
    is_overdue: bool


class NewPartyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=80)
    party_size: int = Field(ge=1)
    phone: str | None = Field(default=None, max_length=32)
    quoted_minutes: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def name_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name is required.")
        return stripped

    @field_validator("phone")
    @classmethod
    def phone_blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class EditPartyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=80)
    party_size: int | None = Field(default=None, ge=1)
    phone: str | None = Field(default=None, max_length=32)
    quoted_minutes: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def name_non_empty(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Name is required.")
        return stripped

    @field_validator("phone")
    @classmethod
    def phone_blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
