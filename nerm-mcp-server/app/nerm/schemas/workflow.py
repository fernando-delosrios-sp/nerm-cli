from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class WorkflowSubmission(BaseModel):
    model_config = ConfigDict(extra="allow")

    workflow_session_full_id: str | None = None
    status: str | None = None

    @field_validator("workflow_session_full_id", mode="before")
    @classmethod
    def _coerce_session_id(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


class WorkflowSession(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    workflow_session_id: str | None = None
    workflow_session_full_id: str | None = None
    status: str | None = None

    @field_validator("id", "workflow_session_id", "workflow_session_full_id", mode="before")
    @classmethod
    def _coerce_id_fields(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


def normalize_workflow_submission(payload: dict) -> dict:
    try:
        return WorkflowSubmission.model_validate(payload).model_dump(exclude_none=True)
    except ValidationError:
        return payload


def normalize_workflow_session_item(item: dict) -> dict:
    try:
        return WorkflowSession.model_validate(item).model_dump(exclude_none=True)
    except ValidationError:
        return item


class JobStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    requested_job_id: str | None = None
    status: str | None = None

    @field_validator("id", "requested_job_id", mode="before")
    @classmethod
    def _coerce_job_id_fields(cls, value: object) -> object:
        if value is None:
            return None
        return str(value)


def normalize_job_status_payload(payload: dict) -> dict:
    try:
        return JobStatus.model_validate(payload).model_dump(exclude_none=True)
    except ValidationError:
        return payload
