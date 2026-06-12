from __future__ import annotations

from datetime import date, datetime, timezone
import re
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, field_validator

_DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DelegationWritePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delegator_id: UUID = Field(
        validation_alias=AliasChoices("delegator_id", "delegator_user_id"),
        description="User ID (UUID) for the delegator. Must reference an existing /users id.",
    )
    delegate_id: UUID = Field(
        validation_alias=AliasChoices("delegate_id", "delegate_user_id", "delegatee_id"),
        description="User ID (UUID) for the delegate. Must reference an existing /users id.",
    )
    expiration: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("expiration", "expiration_date", "expires_at", "end_date"),
    )

    @field_validator("expiration", mode="before")
    @classmethod
    def _coerce_date_only_expiration(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not _DATE_ONLY_PATTERN.match(text):
            return value
        day = date.fromisoformat(text)
        now_utc = datetime.now(timezone.utc)
        return datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=now_utc.hour,
            minute=now_utc.minute,
            second=now_utc.second,
            microsecond=now_utc.microsecond,
            tzinfo=timezone.utc,
        )
    def to_api_payload(self) -> dict:
        payload = {
            "delegator_id": str(self.delegator_id),
            "delegate_id": str(self.delegate_id),
        }
        if self.expiration is not None:
            payload["expiration"] = self.expiration.isoformat()
        return payload


class DelegationUpdatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delegator_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("delegator_id", "delegator_user_id"),
    )
    delegate_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("delegate_id", "delegate_user_id", "delegatee_id"),
    )
    expiration: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("expiration", "expiration_date", "expires_at", "end_date"),
    )

    @field_validator("expiration", mode="before")
    @classmethod
    def _coerce_date_only_expiration(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not _DATE_ONLY_PATTERN.match(text):
            return value
        day = date.fromisoformat(text)
        now_utc = datetime.now(timezone.utc)
        return datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=now_utc.hour,
            minute=now_utc.minute,
            second=now_utc.second,
            microsecond=now_utc.microsecond,
            tzinfo=timezone.utc,
        )
    def to_api_payload(self) -> dict:
        payload: dict[str, str] = {}
        if self.delegator_id is not None:
            payload["delegator_id"] = str(self.delegator_id)
        if self.delegate_id is not None:
            payload["delegate_id"] = str(self.delegate_id)
        if self.expiration is not None:
            payload["expiration"] = self.expiration.isoformat()
        return payload


class DelegationRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    delegator_id: str | None = None
    delegate_id: str | None = None

    @field_validator("id", "delegator_id", "delegate_id", mode="before")
    @classmethod
    def _coerce_id_fields(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


def normalize_delegation_item(item: dict) -> dict:
    try:
        return DelegationRecord.model_validate(item).model_dump(exclude_none=True)
    except ValidationError:
        return item
