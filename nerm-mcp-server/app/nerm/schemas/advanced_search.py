from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _RuleBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    destroy: bool | None = Field(default=None, alias="_destroy")


class ProfileTypeRule(_RuleBase):
    type: Literal["ProfileTypeRule"] = Field(
        description="Rule type discriminator. Must be 'ProfileTypeRule'."
    )
    comparison_operator: Literal["==", "!="]
    value: UUID


class ProfileStatusRule(_RuleBase):
    type: Literal["ProfileStatusRule"] = Field(
        description="Rule type discriminator. Must be 'ProfileStatusRule'."
    )
    comparison_operator: Literal["==", "!="]
    value: Literal["Active", "Inactive", "Leave of absence", "Terminated"]


class ProfileAttributeRuleString(_RuleBase):
    type: Literal["ProfileAttributeRule"] = Field(
        description="Rule type discriminator. Must be 'ProfileAttributeRule' for attribute-based comparisons."
    )
    condition_object_type: Literal["TextFieldAttribute", "TextAreaAttribute"]
    condition_object_id: UUID = Field(description="UUID from ne_attribute.id for the target attribute.")
    comparison_operator: Literal["==", "!=", ">", "<", "start_with?", "end_with?", "include?"]
    value: str


class ProfileAttributeRuleDate(_RuleBase):
    type: Literal["ProfileAttributeRule"] = Field(
        description="Rule type discriminator. Must be 'ProfileAttributeRule' for date attribute comparisons."
    )
    condition_object_type: Literal["DateAttribute"]
    condition_object_id: UUID | None = Field(
        default=None,
        description="UUID from ne_attribute.id for the primary DateAttribute.",
    )
    secondary_attribute_type: Literal["DateAttribute"] | None = None
    secondary_attribute_id: UUID | None = Field(
        default=None,
        description="Optional UUID from ne_attribute.id for the secondary DateAttribute.",
    )
    comparison_operator: Literal["after", "before"]
    value: str
    secondary_value: Literal["after", "before"] | None = None
    tertiary_value: str | None = None


class ProfileAttributeRuleId(_RuleBase):
    type: Literal["ProfileAttributeRule"] = Field(
        description="Rule type discriminator. Must be 'ProfileAttributeRule' for ID-based attribute comparisons."
    )
    condition_object_type: Literal[
        "ProfileSelectAttribute",
        "ProfileSearchAttribute",
        "OwnerSelectAttribute",
        "OwnerSearchAttribute",
        "ContributorSelectAttribute",
        "ContributorSearchAttribute",
    ]
    condition_object_id: UUID = Field(description="UUID from ne_attribute.id for the target attribute.")
    comparison_operator: Literal["include?", "exclude?"]
    value: UUID


class RiskRule(_RuleBase):
    type: Literal["RiskRule"] = Field(
        description="Rule type discriminator. Must be 'RiskRule'."
    )
    comparison_operator: Literal["==", ">", "<"] | None = None
    value: UUID
    secondary_value: Literal["OverallRisk"]

AdvancedSearchRule = (
    ProfileTypeRule | ProfileStatusRule | ProfileAttributeRuleString | ProfileAttributeRuleDate | ProfileAttributeRuleId | RiskRule
)


class AdvancedSearchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = None
    condition_rules_attributes: list[AdvancedSearchRule] = Field(
        default_factory=list,
        description=(
            "List of advanced-search condition rules. Each rule requires a `type` discriminator: "
            "'ProfileTypeRule', 'ProfileStatusRule', 'ProfileAttributeRule', or 'RiskRule'. "
            "For 'ProfileAttributeRule', pair `type` with a valid `condition_object_type` "
            "to select the correct rule shape. Provide at least one selective rule to avoid broad profile listings."
        ),
    )

    @classmethod
    def validate_inner_payload(cls, payload: dict) -> dict:
        validated = cls.model_validate(payload)
        normalized: dict[str, object] = {
            "condition_rules_attributes": [
                rule.model_dump(exclude_none=True, mode="json", by_alias=True)
                for rule in validated.condition_rules_attributes
            ],
        }
        if validated.label is not None:
            normalized["label"] = validated.label
        return normalized
