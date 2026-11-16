# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NUMBER_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*%?\s*$")


def _coerce_score(value: Any) -> Any:
    """Accept 85, 84.6, "85", "85%". Reject bool, NaN/inf and non-numeric strings."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("score must be a number, not a boolean")
    if isinstance(value, str):
        match = _NUMBER_RE.match(value)
        if not match:
            raise ValueError(f"score is not numeric: {value!r}")
        value = float(match.group(1))
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("score must be a finite number")
        return round(value)
    return value


def _coerce_str_list(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return value


class EvaluationResult(BaseModel):
    """Structured output expected from the Evaluator agent."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    overall_score: int = Field(ge=0, le=100, description="Overall quality score, integer 0-100.")
    technical_accuracy_score: int | None = Field(default=None, ge=0, le=100)
    clarity_score: int | None = Field(default=None, ge=0, le=100)
    structure_score: int | None = Field(default=None, ge=0, le=100)
    verdict: Literal["PASS", "REJECT"] | None = Field(
        default=None,
        description="Model's own verdict. Informational only; the app recomputes it from overall_score.",
    )
    key_strengths: list[str] = Field(default_factory=list, description="Short list of strengths.")
    critical_flaws: list[str] = Field(default_factory=list, description="Short list of revision items.")
    actionable_feedback: str = Field(default="", description="Markdown feedback for the content writer.")

    @field_validator(
        "overall_score",
        "technical_accuracy_score",
        "clarity_score",
        "structure_score",
        mode="before",
    )
    @classmethod
    def _score_before(cls, value: Any) -> Any:
        return _coerce_score(value)

    @field_validator("verdict", mode="before")
    @classmethod
    def _verdict_before(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip().upper()
            return value or None
        return value

    @field_validator("key_strengths", "critical_flaws", mode="before")
    @classmethod
    def _list_before(cls, value: Any) -> Any:
        return _coerce_str_list(value)

    @field_validator("actionable_feedback", mode="before")
    @classmethod
    def _feedback_before(cls, value: Any) -> Any:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value)
        return value

    def verdict_for(self, passing_score: int) -> Literal["PASS", "REJECT"]:
        return "PASS" if self.overall_score >= passing_score else "REJECT"
