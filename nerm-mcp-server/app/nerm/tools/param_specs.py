from typing import Annotated
from typing import Literal

from pydantic import Field
from nerm.spec_contract import (
    ATTRIBUTE_DATA_TYPES,
    IDENTITY_PROOFING_RESULTS,
    ISC_ACCOUNT_CATEGORIES,
    ISC_ACCOUNT_STATUSES,
    PROFILE_STATUSES,
    PROFILE_TYPE_SYNCED_FILTERS,
    RELATIONSHIP_TYPES,
    RISK_SCORE_OBJECT_TYPES,
    ROLE_TYPES,
    USER_STATUSES,
    USER_TYPES,
    WORKFLOW_SESSION_STATUSES,
)

Int32Positive = Annotated[
    int,
    Field(
        ge=1,
        le=2_147_483_647,
        description="Positive integer (int32).",
        json_schema_extra={"format": "int32"},
    ),
]

Int32NonNegative = Annotated[
    int,
    Field(
        ge=0,
        le=2_147_483_647,
        description="Non-negative integer (int32).",
        json_schema_extra={"format": "int32"},
    ),
]

CatalogLimitInt32 = Annotated[
    int,
    Field(
        ge=0,
        le=2_147_483_647,
        description="Catalog page size (int32).",
        json_schema_extra={"format": "int32"},
    ),
]

ForceAllFlag = Annotated[
    bool,
    Field(
        description="When true, bypass pagination circuit-breaker safeguards and keep fetching pages.",
    ),
]

ResourceId = Annotated[
    str,
    Field(
        min_length=1,
        description="Resource identifier string.",
    ),
]

OptionalBaseUrl = Annotated[
    str | None,
    Field(
        default=None,
        description="Optional NERM tenant base URL override.",
    ),
]

OptionalBearerToken = Annotated[
    str | None,
    Field(
        default=None,
        description="Optional NERM bearer token override.",
    ),
]

WorkflowSessionStatus = Literal[*WORKFLOW_SESSION_STATUSES]

WorkflowStatusFilter = Annotated[
    WorkflowSessionStatus | None,
    Field(
        default=None,
        description="Workflow status filter; constrained to values documented in the OpenAPI description.",
    ),
]

OrderBy = Annotated[
    str | None,
    Field(default=None, description="Optional sort field name."),
]

MetadataFlag = Annotated[
    bool | None,
    Field(default=None, description="Include metadata block in response when true."),
]

ProfileStatus = Literal[*PROFILE_STATUSES]
UserStatus = Literal[*USER_STATUSES]
UserType = Literal[*USER_TYPES]
RoleType = Literal[*ROLE_TYPES]
RelationshipType = Literal[*RELATIONSHIP_TYPES]
IdentityProofingResult = Literal[*IDENTITY_PROOFING_RESULTS]
AttributeDataType = Literal[*ATTRIBUTE_DATA_TYPES]

# Additional documented enum-like values found in OpenAPI descriptions
# for endpoints that are not currently exposed as MCP tools.
IscAccountCategory = Literal[*ISC_ACCOUNT_CATEGORIES]
IscAccountStatus = Literal[*ISC_ACCOUNT_STATUSES]
ProfileTypeSyncedFilter = Literal[*PROFILE_TYPE_SYNCED_FILTERS]
RiskScoreObjectType = Literal[*RISK_SCORE_OBJECT_TYPES]
