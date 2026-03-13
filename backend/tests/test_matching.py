from __future__ import annotations

import pytest

from app import matching
from app.schemas import MappingDirection


class DummySession:
    """Minimal stand-in so matching.suggest_mappings can be called without DB."""

    def execute(self, *_, **__):  # type: ignore[no-untyped-def]
        class R:
            approvals = 0
            rejections = 0

        class C:
            def one_or_none(self):  # type: ignore[no-untyped-def]
                return R()

        return C()

    def query(self, *_, **__):  # type: ignore[no-untyped-def]
        class Q:
            def all(self):  # type: ignore[no-untyped-def]
                return []

        return Q()


def test_acronym_expansion_account():
    assert matching.normalize_term("Act") == "account"
    assert matching.normalize_term("Acct") == "account"


def test_semantic_like_similarity_for_account_balance():
    src = "ACT_BAL"
    tgt = "Account Balance"
    score = matching.lexical_similarity(src, tgt)
    assert score > 0.6


def test_suggest_mappings_orders_by_score():
    db = DummySession()
    suggestions = matching.suggest_mappings(
        db=db,
        direction=MappingDirection.physical_to_glossary,
        source_terms=["ACT_BAL"],
        target_terms=["Customer Name", "Account Balance", "Account Number"],
        top_k=2,
        min_score=0.0,
    )
    assert len(suggestions) == 1
    top = suggestions[0].candidates
    assert len(top) == 2
    # Best match should be Account Balance
    assert top[0].target_term == "Account Balance"


def test_eval_dataset_acronym_coverage():
    """
    Every short token (2–4 char alpha) in eval source terms must be in ACRONYM_MAP.
    Run backend/scripts/mine_acronyms.py to find missing acronyms and add them to
    backend/config/acronyms.yml (or in-code ACRONYM_MAP).
    """
    from tests.run_eval import DATASET

    all_sources: list[str] = []
    for case in DATASET:
        all_sources.extend(case.source_terms)
    short = matching.short_tokens_from_terms(all_sources)
    missing = short - set(matching.ACRONYM_MAP)
    assert not missing, (
        f"Eval source terms contain short tokens not in ACRONYM_MAP: {sorted(missing)}. "
        "Add them to backend/config/acronyms.yml and restart, or run: python backend/scripts/mine_acronyms.py"
    )
