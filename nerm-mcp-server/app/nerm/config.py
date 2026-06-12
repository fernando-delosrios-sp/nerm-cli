from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    nerm_base_url: str = Field(default="", alias="NERM_BASE_URL", validation_alias=AliasChoices("NERM_BASE_URL", "NERM_TENANT"))
    nerm_bearer_token: str = Field(
        default="",
        alias="NERM_BEARER_TOKEN",
        validation_alias=AliasChoices("NERM_BEARER_TOKEN", "NERM_API_TOKEN"),
    )
    nerm_static_reference_cache_ttl_sec: int = Field(default=3600, alias="NERM_STATIC_REFERENCE_CACHE_TTL_SEC")
    nerm_api_base_path: str = Field(default="/api", alias="NERM_API_BASE_PATH")
    nerm_add_location_workflow_id: str = Field(default="", alias="NERM_ADD_LOCATION_WORKFLOW_ID")
    nerm_add_department_workflow_id: str = Field(default="", alias="NERM_ADD_DEPARTMENT_WORKFLOW_ID")
    nerm_add_organization_workflow_id: str = Field(default="", alias="NERM_ADD_ORGANIZATION_WORKFLOW_ID")
    nerm_transport: str = Field(default="stdio", alias="NERM_TRANSPORT")
    nerm_http_host: str = Field(default="0.0.0.0", alias="NERM_HTTP_HOST")
    nerm_http_port: int = Field(default=8080, alias="NERM_HTTP_PORT")
    nerm_embed_charts_in_response: bool = Field(default=True, alias="NERM_EMBED_CHARTS_IN_RESPONSE")
    nerm_chart_include_base64: bool = Field(default=False, alias="NERM_CHART_INCLUDE_BASE64")
    nerm_debug_log_bodies: bool = Field(default=False, alias="NERM_DEBUG_LOG_BODIES")
    nerm_trace_max_bytes: int = Field(default=4096, alias="NERM_TRACE_MAX_BYTES")
    nerm_verbose_trace: bool = Field(default=False, alias="NERM_VERBOSE_TRACE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
