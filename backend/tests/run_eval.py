from __future__ import annotations

"""
Ad-hoc evaluation script for the semantic mapper.

Run from project root:

    python3 backend/tests/run_eval.py

This prints top-1 and top-3 accuracy over a small synthetic dataset that
covers acronyms, synonyms, and different mapping directions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import random

import sys


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import matching  # type: ignore  # noqa: E402
from app.schemas import MappingDirection  # type: ignore  # noqa: E402


class DummySession:
    """Stand-in so suggest_mappings can be exercised without a DB."""

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


@dataclass
class EvalCase:
    name: str
    direction: MappingDirection
    source_terms: List[str]
    target_terms: List[str]
    # For each source term, the expected best target term
    expected_top1: List[str]


DATASET: List[EvalCase] = [
    EvalCase(
        name="account_balance_acronym",
        direction=MappingDirection.physical_to_glossary,
        source_terms=["ACT_BAL"],
        target_terms=["Account Balance", "Customer Name", "Account Number"],
        expected_top1=["Account Balance"],
    ),
    EvalCase(
        name="customer_identifier_synonym",
        direction=MappingDirection.physical_to_glossary,
        source_terms=["CUST_ID"],
        target_terms=["Client Identifier", "Customer Name"],
        expected_top1=["Client Identifier"],
    ),
    EvalCase(
        name="customer_vs_client",
        direction=MappingDirection.glossary_to_glossary,
        source_terms=["Customer"],
        target_terms=["Client", "Product"],
        expected_top1=["Client"],
    ),
    EvalCase(
        name="facility_vs_account",
        direction=MappingDirection.glossary_to_glossary,
        source_terms=["Facility"],
        target_terms=["Account", "Customer"],
        expected_top1=["Account"],
    ),
    EvalCase(
        name="postal_code_synonyms",
        direction=MappingDirection.physical_to_glossary,
        source_terms=["CUST_POST_CD"],
        target_terms=["Customer Postal Code", "Customer City"],
        expected_top1=["Customer Postal Code"],
    ),
    EvalCase(
        name="date_open_synonyms",
        direction=MappingDirection.physical_to_glossary,
        source_terms=["ACT_OPEN_DT"],
        target_terms=["Account Open Date", "Account Close Date"],
        expected_top1=["Account Open Date"],
    ),
    EvalCase(
        name="physical_to_physical_close",
        direction=MappingDirection.physical_to_physical,
        source_terms=["ACT_BAL", "ACT_BALANCE"],
        target_terms=["ACCT_BAL", "CUSTOMER_ID"],
        expected_top1=["ACCT_BAL", "ACCT_BAL"],
    ),
    EvalCase(
        name="product_vs_instrument",
        direction=MappingDirection.glossary_to_glossary,
        source_terms=["Financial Instrument Type"],
        target_terms=["Product Type", "Customer Segment"],
        expected_top1=["Product Type"],
    ),
    EvalCase(
        name="asset_wealth_large",
        direction=MappingDirection.physical_to_glossary,
        source_terms=[
            "ACCT_ID",
            "ACCT_OPEN_DT",
            "ACCT_CLOSE_DT",
            "ACCT_BAL",
            "ACCT_AVG_BAL",
            "CUST_ID",
            "CUST_SEG_CD",
            "CUST_RISK_RTNG",
            "CUST_CTRY_CD",
            "CUST_CITY",
            "PORT_ID",
            "PORT_NAME",
            "PORT_AUM_AMT",
            "PORT_NAV_AMT",
            "PORT_RET_YTD",
            "PORT_RET_1Y",
            "PORT_RET_3Y",
            "PORT_VOL_1Y",
            "PORT_BENCH_ID",
            "POSN_ID",
            "POSN_QTY",
            "POSN_MV_AMT",
            "POSN_PRC",
            "FUND_ID",
            "FUND_TYPE_CD",
            "FUND_AUM_AMT",
            "FUND_NAV_PX",
            "FUND_TNA_AMT",
            "ETF_ID",
            "ETF_AUM_AMT",
            "ETF_DUR",
            "ETF_TE",
            "TX_ID",
            "TX_DT",
            "TX_AMT",
            "TX_FEE_AMT",
            "RM_ID",
            "RM_SEG_CD",
            "BENCH_ID",
            "BENCH_NAME",
            "BRANCH_ID",
            "BRANCH_CITY",
            "PROD_ID",
            "PROD_TYPE_CD",
            "PROD_SECTOR_CD",
            "RISK_SRRI_CD",
            "RISK_LIMIT_AMT",
            "CASH_BAL_AMT",
            "FEE_MGMT_AMT",
            "FEE_PERF_AMT",
        ],
        target_terms=[
            # Primary expected matches for the 50 physicals above (first 50 entries)
            "Account Identifier",
            "Account Open Date",
            "Account Close Date",
            "Account Balance",
            "Account Average Balance",
            "Customer Identifier",
            "Customer Segment Code",
            "Customer Risk Rating",
            "Customer Country Code",
            "Customer City",
            "Portfolio Identifier",
            "Portfolio Name",
            "Portfolio Assets Under Management Amount",
            "Portfolio Net Asset Value Amount",
            "Portfolio Return Year To Date",
            "Portfolio Return One Year",
            "Portfolio Return Three Years",
            "Portfolio Volatility One Year",
            "Portfolio Benchmark Identifier",
            "Position Identifier",
            "Position Quantity",
            "Position Market Value Amount",
            "Position Price",
            "Fund Identifier",
            "Fund Type Code",
            "Fund Assets Under Management Amount",
            "Fund Net Asset Value Price",
            "Fund Total Net Assets Amount",
            "Exchange Traded Fund Identifier",
            "Exchange Traded Fund Assets Under Management Amount",
            "Exchange Traded Fund Duration",
            "Exchange Traded Fund Tracking Error",
            "Transaction Identifier",
            "Transaction Date",
            "Transaction Amount",
            "Transaction Fee Amount",
            "Relationship Manager Identifier",
            "Relationship Manager Segment Code",
            "Benchmark Identifier",
            "Benchmark Name",
            "Branch Identifier",
            "Branch City",
            "Product Identifier",
            "Product Type Code",
            "Product Sector Code",
            "Risk SRRI Code",
            "Risk Limit Amount",
            "Cash Balance Amount",
            "Management Fee Amount",
            "Performance Fee Amount",
            # Additional glossary terms (decoys / richness)
            "Customer Email Address",
            "Customer Phone Number",
            "Customer Postal Code",
            "Customer Region",
            "Customer Onboarding Date",
            "Customer Age",
            "Customer Income Band",
            "Customer Gender",
            "Customer Marital Status",
            "Customer Occupation",
            "Portfolio Strategy Description",
            "Portfolio Currency",
            "Portfolio Inception Date",
            "Portfolio Liquidity Profile",
            "Portfolio SRRI Level",
            "Portfolio Risk Budget",
            "Fund Legal Name",
            "Fund Domicile Country",
            "Fund Currency",
            "Fund Inception Date",
            "Fund Share Class",
            "Fund ISIN Code",
            "Fund Management Company",
            "Fund Depositary Bank",
            "Benchmark Ticker",
            "Benchmark Currency",
            "Benchmark Provider",
            "Instrument Identifier",
            "Instrument ISIN",
            "Instrument Asset Class",
            "Instrument Sector",
            "Instrument Country",
            "Instrument Duration",
            "Instrument Coupon Rate",
            "Instrument Maturity Date",
            "Instrument Liquidity Score",
            "Risk Appetite Category",
            "Limit Breach Flag",
            "Limit Breach Date",
            "Cash Currency",
            "Cash Account Identifier",
            "Management Fee Percentage",
            "Performance Fee Percentage",
            "Total Expense Ratio",
            "Ongoing Charges Figure",
            "Assets Under Management Amount",
            "Total Net Assets Amount",
            "Net Asset Value Amount",
            "Gross Asset Value Amount",
        ],
        expected_top1=[
            "Account Identifier",
            "Account Open Date",
            "Account Close Date",
            "Account Balance",
            "Account Average Balance",
            "Customer Identifier",
            "Customer Segment Code",
            "Customer Risk Rating",
            "Customer Country Code",
            "Customer City",
            "Portfolio Identifier",
            "Portfolio Name",
            "Portfolio Assets Under Management Amount",
            "Portfolio Net Asset Value Amount",
            "Portfolio Return Year To Date",
            "Portfolio Return One Year",
            "Portfolio Return Three Years",
            "Portfolio Volatility One Year",
            "Portfolio Benchmark Identifier",
            "Position Identifier",
            "Position Quantity",
            "Position Market Value Amount",
            "Position Price",
            "Fund Identifier",
            "Fund Type Code",
            "Fund Assets Under Management Amount",
            "Fund Net Asset Value Price",
            "Fund Total Net Assets Amount",
            "Exchange Traded Fund Identifier",
            "Exchange Traded Fund Assets Under Management Amount",
            "Exchange Traded Fund Duration",
            "Exchange Traded Fund Tracking Error",
            "Transaction Identifier",
            "Transaction Date",
            "Transaction Amount",
            "Transaction Fee Amount",
            "Relationship Manager Identifier",
            "Relationship Manager Segment Code",
            "Benchmark Identifier",
            "Benchmark Name",
            "Branch Identifier",
            "Branch City",
            "Product Identifier",
            "Product Type Code",
            "Product Sector Code",
            "Risk SRRI Code",
            "Risk Limit Amount",
            "Cash Balance Amount",
            "Management Fee Amount",
            "Performance Fee Amount",
        ],
    ),
]


def evaluate(
    cases: Sequence[EvalCase],
    top_k: int = 3,
    min_score: float = 0.0,
) -> None:
    db = DummySession()
    total_sources = 0
    correct_top1 = 0
    correct_topk = 0
    mismatches: list[tuple[str, str, str, list[str]]] = []

    for case in cases:
        suggestions = matching.suggest_mappings(
            db=db,
            direction=case.direction,
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
                continue
            top1 = sugg.candidates[0].target_term
            if top1 == expected:
                correct_top1 += 1
            if any(c.target_term == expected for c in sugg.candidates[:top_k]):
                correct_topk += 1
            if top1 != expected:
                topk_terms = [c.target_term for c in sugg.candidates[:top_k]]
                mismatches.append((case.name, src, expected, topk_terms))

    if total_sources == 0:
        print("No sources in dataset.")
        return

    top1_acc = correct_top1 / total_sources
    topk_acc = correct_topk / total_sources

    print(f"Total source terms evaluated: {total_sources}")
    print(f"Top-1 accuracy: {top1_acc:.3f}")
    print(f"Top-{top_k} accuracy: {topk_acc:.3f}")

    if mismatches:
        print("\nMismatches (case, source, expected, top_k_candidates):")
        for case_name, src, expected, topk_terms in mismatches:
            print(f"- {case_name}: {src!r} -> expected {expected!r}, got {topk_terms!r}")


if __name__ == "__main__":
    evaluate(DATASET)

    # Randomized trials over the asset_wealth_large case.
    asset_case = next(c for c in DATASET if c.name == "asset_wealth_large")
    max_trials = 100
    required_streak = 3
    streak = 0
    trial = 0

    print("\nRandomized trials over asset_wealth_large (50 physical / 100 glossary)")
    while streak < required_streak and trial < max_trials:
        trial += 1
        idxs = list(range(len(asset_case.source_terms)))
        random.shuffle(idxs)
        src_terms = [asset_case.source_terms[i] for i in idxs]
        expected = [asset_case.expected_top1[i] for i in idxs]

        db = DummySession()
        suggestions = matching.suggest_mappings(
            db=db,
            direction=asset_case.direction,
            source_terms=src_terms,
            target_terms=asset_case.target_terms,
            top_k=3,
            min_score=0.0,
        )

        total = len(src_terms)
        correct = 0
        for s, exp in zip(src_terms, expected):
            sug = next((x for x in suggestions if x.source_term == s), None)
            if not sug or not sug.candidates:
                continue
            if sug.candidates[0].target_term == exp:
                correct += 1

        acc = correct / total if total else 0.0
        print(f"Trial {trial}: top-1 accuracy = {acc:.3f}")

        if acc >= 0.95:
            streak += 1
        else:
            streak = 0

    if streak >= required_streak:
        print(f"\nSuccess: achieved {required_streak} consecutive trials with accuracy >= 0.95")
    else:
        print("\nDid not achieve required accuracy streak; consider inspecting mismatches further.")
