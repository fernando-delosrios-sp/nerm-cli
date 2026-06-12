from typing import get_args

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
from nerm.tools.param_specs import (
    AttributeDataType,
    IdentityProofingResult,
    IscAccountCategory,
    IscAccountStatus,
    ProfileStatus,
    ProfileTypeSyncedFilter,
    RelationshipType,
    RiskScoreObjectType,
    RoleType,
    UserStatus,
    UserType,
    WorkflowSessionStatus,
)


def test_param_specs_literals_match_spec_contract_constants() -> None:
    assert get_args(WorkflowSessionStatus) == WORKFLOW_SESSION_STATUSES
    assert get_args(ProfileStatus) == PROFILE_STATUSES
    assert get_args(UserStatus) == USER_STATUSES
    assert get_args(UserType) == USER_TYPES
    assert get_args(RoleType) == ROLE_TYPES
    assert get_args(RelationshipType) == RELATIONSHIP_TYPES
    assert get_args(IdentityProofingResult) == IDENTITY_PROOFING_RESULTS
    assert get_args(AttributeDataType) == ATTRIBUTE_DATA_TYPES
    assert get_args(IscAccountCategory) == ISC_ACCOUNT_CATEGORIES
    assert get_args(IscAccountStatus) == ISC_ACCOUNT_STATUSES
    assert get_args(ProfileTypeSyncedFilter) == PROFILE_TYPE_SYNCED_FILTERS
    assert get_args(RiskScoreObjectType) == RISK_SCORE_OBJECT_TYPES
