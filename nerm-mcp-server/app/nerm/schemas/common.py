from pydantic import BaseModel, ConfigDict, Field, ValidationError


class PaginatedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1)
    offset: int = Field(default=0, ge=0)


class CatalogSliceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=0)
    offset: int = Field(default=0, ge=0)


def normalize_pagination(limit: int, offset: int) -> tuple[int, int]:
    payload = PaginatedRequest.model_validate({"limit": limit, "offset": offset})
    return payload.limit, payload.offset


def normalize_catalog_slice(limit: int, offset: int) -> tuple[int, int]:
    payload = CatalogSliceRequest.model_validate({"limit": limit, "offset": offset})
    return payload.limit, payload.offset


def pagination_validation_error(exc: ValidationError) -> dict:
    return {
        "error": "invalid_pagination_spec",
        "message": "Invalid pagination values for limit/offset.",
        "details": exc.errors(include_url=False),
    }
