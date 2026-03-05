from __future__ import annotations

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
