from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class IdentityProofingResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


def normalize_identity_proofing_item(item: dict) -> dict:
    try:
        return IdentityProofingResult.model_validate(item).model_dump(exclude_none=True)
    except ValidationError:
        return item
