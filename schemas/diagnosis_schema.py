"""Structured-output schemas for the two AI tasks, validated with Pydantic after the call."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class AIDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosed_reason_code: str          # catalog code or "UNKNOWN"; checked against catalog
    evidence_quote: str                 # must be an exact substring of the reviewer text
    explanation: str
    needs_human_review: bool
    sensitive_case: bool


class NudgeDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str                        # in the merchant's language
    english_back_translation: str       # lets a reviewer who can't read the language check meaning

    @field_validator("message", "english_back_translation")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


def diagnosis_json_schema(allowed_codes: list[str]) -> dict:
    """JSON schema sent to the API; the code enum is built from the live catalog."""
    return {
        "type": "object",
        "properties": {
            "diagnosed_reason_code": {"type": "string", "enum": [*allowed_codes, "UNKNOWN"]},
            "evidence_quote": {"type": "string"},
            "explanation": {"type": "string"},
            "needs_human_review": {"type": "boolean"},
            "sensitive_case": {"type": "boolean"},
        },
        "required": ["diagnosed_reason_code", "evidence_quote", "explanation",
                     "needs_human_review", "sensitive_case"],
        "additionalProperties": False,
    }


NUDGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "english_back_translation": {"type": "string"},
    },
    "required": ["message", "english_back_translation"],
    "additionalProperties": False,
}
