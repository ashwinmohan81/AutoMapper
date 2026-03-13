from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MappingDirection(str, Enum):
    physical_to_glossary = "physical_to_glossary"
    glossary_to_physical = "glossary_to_physical"
    physical_to_physical = "physical_to_physical"
    glossary_to_glossary = "glossary_to_glossary"


class MappingRequest(BaseModel):
    direction: MappingDirection
    source_terms: List[str] = Field(..., min_length=1)
    target_terms: List[str] = Field(..., min_length=1)
    acronym_overrides: Dict[str, str] = Field(default_factory=dict)
    synonym_overrides: Dict[str, str] = Field(default_factory=dict)


class MappingCandidate(BaseModel):
    target_term: str
    score: float = Field(..., ge=0.0, le=1.0)
    boosted_by_feedback: bool = False


class SourceSuggestion(BaseModel):
    source_term: str
    candidates: List[MappingCandidate]


class MappingResponse(BaseModel):
    direction: MappingDirection
    suggestions: List[SourceSuggestion]


class FeedbackRequest(BaseModel):
    direction: MappingDirection
    source_term: str
    chosen_target: Optional[str] = None
    approved: bool
    rejected_targets: List[str] = []
    candidate_scores: Dict[str, float] = {}


class MappingRecord(BaseModel):
    id: int
    source_term: str
    target_term: str
    direction: MappingDirection

    class Config:
        from_attributes = True


class EvalPair(BaseModel):
    source_term: str
    expected_target: str


class EvalRequest(BaseModel):
    use_builtin: bool = False
    direction: Optional[MappingDirection] = None
    pairs: List[EvalPair] = []
    target_terms: List[str] = []


class EvalResult(BaseModel):
    total: int
    top1_accuracy: float
    top3_accuracy: float
    mismatches: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True

