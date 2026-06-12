from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError, field_validator

from nerm.spec_contract import AUDIT_EVENT_TYPES, AUDIT_SUBJECT_TYPES


class AuditQueryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_type: str | None = Field(
        default=None,
        description=(
            "Subject type string from API audit domain. "
            f"Common values: {', '.join(AUDIT_SUBJECT_TYPES)}"
        ),
    )
    type: str | None = Field(
        default=None,
        description=(
            "Audit event type string from API audit domain. "
            f"Common values: {', '.join(AUDIT_EVENT_TYPES)}"
        ),
    )
    subject_id: str | None = None
    workflow_name: str | None = None
    workflow_uid: str | None = None
    workflow_profile_type: str | None = None
    profile_type: str | None = None


class AuditQueryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1)
    offset: int = Field(default=0, ge=0)
    filters: AuditQueryFilters | None = None


class AuditEventRecord(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


def normalize_audit_event_item(item: dict) -> dict:
    try:
        return AuditEventRecord.model_validate(item).model_dump(exclude_none=True)
    except ValidationError:
        return item
