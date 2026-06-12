from pydantic import BaseModel, ConfigDict


class ChartArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = "image/png"
    path: str | None = None
    markdown: str | None = None
    base64: str | None = None
    data_uri: str | None = None
