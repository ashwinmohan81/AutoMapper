"""Run eval over cases and return accuracy + mismatches (for API and CLI)."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from sqlalchemy.orm import Session

from . import matching
from .schemas import MappingDirection


def run_eval_cases(
    cases: Sequence[Any],
    db: Session,
    top_k: int = 3,
    min_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Run suggest_mappings for each case and compute top-1/top-k accuracy.
    Each case must have: name, direction, source_terms, target_terms, expected_top1.
    """
    total_sources = 0
    correct_top1 = 0
    correct_topk = 0
    mismatches: List[Dict[str, Any]] = []

    for case in cases:
        direction = (
            case.direction
            if isinstance(case.direction, MappingDirection)
            else MappingDirection(case.direction)
        )
        suggestions = matching.suggest_mappings(
            db=db,
            direction=direction,
            source_terms=case.source_terms,
            target_terms=case.target_terms,
            top_k=top_k,
            min_score=min_score,
        )

        for i, src in enumerate(case.source_terms):
            total_sources += 1
            expected = case.expected_top1[i]
            sugg = next((s for s in suggestions if s.source_term == src), None)
            if not sugg or not sugg.candidates:
                mismatches.append(
                    {
                        "case_name": getattr(case, "name", "custom"),
                        "source_term": src,
                        "expected": expected,
                        "got_top_k": [],
                    }
                )
                continue
            top1 = sugg.candidates[0].target_term
            if top1 == expected:
                correct_top1 += 1
            if any(c.target_term == expected for c in sugg.candidates[:top_k]):
                correct_topk += 1
            if top1 != expected:
                topk_terms = [c.target_term for c in sugg.candidates[:top_k]]
                mismatches.append(
                    {
                        "case_name": getattr(case, "name", "custom"),
                        "source_term": src,
                        "expected": expected,
                        "got_top_k": topk_terms,
                    }
                )

    top1_accuracy = correct_top1 / total_sources if total_sources else 0.0
    top3_accuracy = correct_topk / total_sources if total_sources else 0.0

    return {
        "total": total_sources,
        "top1_accuracy": round(top1_accuracy, 4),
        "top3_accuracy": round(top3_accuracy, 4),
        "mismatches": mismatches,
    }
