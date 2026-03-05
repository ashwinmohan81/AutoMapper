from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Tuple

from difflib import SequenceMatcher
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .schemas import MappingDirection, MappingCandidate, SourceSuggestion


ACRONYM_MAP: Dict[str, str] = {
    # Account / agreement / facility
    "act": "account",
    "acct": "account",
    "acnt": "account",
    "agr": "agreement",
    "agrmt": "agreement",
    "cntr": "contract",
    "cont": "contract",
    "fac": "facility",

    # Transaction / payment / fee
    "tx": "transaction",
    "txn": "transaction",
    "trn": "transaction",
    "trxn": "transaction",
    "trns": "transaction",
    "pmt": "payment",
    "pymt": "payment",
    "paymt": "payment",
    "chq": "cheque",
    "chk": "cheque",
    "fee": "fee",

    # Party / customer / counterparty
    "cust": "customer",
    "cstmr": "customer",
    "cst": "customer",
    "cli": "client",
    "clnt": "client",
    "ctrpty": "counterparty",
    "cppty": "counterparty",
    "pty": "party",
    "posn": "position",

    # Generic identifiers / references
    "id": "identifier",
    "ident": "identifier",
    "no": "number",
    "nbr": "number",
    "num": "number",
    "seq": "sequence",
    "seqno": "sequence",
    "ref": "reference",
    "refno": "reference",
    "key": "key",
    "ph": "phone",
    "tel": "telephone",
    "mob": "mobile",
    "ccy": "currency",
    "cur": "currency",
    "curr": "currency",

    # Monetary amounts / balances / prices
    "amt": "amount",
    "amnt": "amount",
    "bal": "balance",
    "balc": "balance",
    "mv": "market_value",
    "mtm": "mark_to_market",
    "prc": "price",
    "px": "price",

    # Quantities / counts
    "qty": "quantity",
    "qnty": "quantity",
    "cnt": "count",
    "ctr": "counter",

    # Dates / times
    "dt": "date",
    "dte": "date",
    "dtm": "datetime",
    "ts": "timestamp",
    "tm": "time",

    # Postal / codes / geo
    "post": "postal",
    "pcd": "postal",
    "pcode": "postal",
    "zip": "postal",
    "cd": "code",
    "ctry": "country",
    "cntry": "country",
    "cty": "city",

    # Organisation / department / branch
    "dept": "department",
    "div": "division",
    "bunit": "business_unit",
    "bu": "business_unit",
    "org": "organisation",
    "br": "branch",
    "brnch": "branch",

    # Asset & wealth management domain
    "aum": "assets_under_management",
    "tna": "total_net_assets",
    "ta": "total_assets",
    "nav": "net_asset_value",
    "gav": "gross_asset_value",
    "rv": "relative_value",
    "ir": "interest_rate",
    "irr": "internal_rate_of_return",
    "roi": "return_on_investment",
    "ytd": "year_to_date",
    "qtd": "quarter_to_date",
    "mtd": "month_to_date",
    "ttm": "trailing_twelve_months",
    "1y": "horizon_1y",
    "3y": "horizon_3y",
    "mf": "mutual_fund",
    "etf": "exchange_traded_fund",
    "ucits": "ucits",
    "sicav": "sicav",
    "sicaf": "sicaf",
    "fof": "fund_of_funds",
    "pm": "portfolio_manager",
    "rm": "relationship_manager",
    "bm": "benchmark",
    "idx": "index",
    "bmk": "benchmark",
    # Index / benchmark tickers & shorthand
    "ix": "index",
    "spx": "sp_500_index",
    "sp500": "sp_500_index",
    "sx5e": "euro_stoxx_50_index",
    "stoxx": "stoxx_index",
    "ftse": "ftse_index",
    "dow": "dow_jones_index",
    "djia": "dow_jones_index",
    "msci": "msci_index",
    "pe": "price_earnings",
    "pb": "price_book",
    "dy": "dividend_yield",
    "dur": "duration",
    "dv01": "dv01",
    "te": "tracking_error",
    "tna_fee": "total_net_assets_fee",
    "ocf": "ongoing_charges_figure",
    "ter": "total_expense_ratio",
    "srri": "synthetic_risk_reward_indicator",
    "saa": "strategic_asset_allocation",
    "taa": "tactical_asset_allocation",
    "ltd": "limited",
    "lp": "limited_partner",
    "gp": "general_partner",
    "bench": "benchmark",
    "mgmt": "management_fee",

    # ABOR / IBOR / accounting & PnL
    "abor": "accounting_book_of_record",
    "ibor": "investment_book_of_record",
    "gl": "general_ledger",
    "pnl": "profit_and_loss",
    "pl": "profit_and_loss",
    "eod": "end_of_day",
    "bod": "beginning_of_day",

    # Transaction / settlement styles
    "stp": "straight_through_processing",
    "dvp": "delivery_versus_payment",
    "rvp": "receive_versus_payment",
    "fop": "free_of_payment",
    "div": "dividend",
    "int": "interest",
    "sub": "subscription",
    "red": "redemption",
    "trd": "trade",
    "fx": "foreign_exchange",
    "otc": "over_the_counter",

    # Instrument / security domain
    "eq": "equity",
    "eqty": "equity",
    "stk": "equity",
    "sh": "share",
    "shr": "share",
    "fi": "fixed_income",
    "bd": "bond",
    "bnd": "bond",
    "nt": "note",
    "ntn": "note",
    "frn": "floating_rate_note",
    "cpn": "coupon",
    "ytm": "yield_to_maturity",
    "ytw": "yield_to_worst",
    "ytc": "yield_to_call",
    "fut": "future",
    "fwd": "forward",
    "swp": "swap",
    "irs": "interest_rate_swap",
    "cds": "credit_default_swap",
    "cln": "credit_linked_note",
    "cdo": "collateralised_debt_obligation",
    "clo": "collateralised_loan_obligation",
    "cmo": "collateralised_mortgage_obligation",
    "abs": "asset_backed_security",
    "mbs": "mortgage_backed_security",
    "tba": "to_be_announced",
    "wrt": "warrant",
    "warr": "warrant",
    "opt": "option",
    "call": "call_option",
    "put": "put_option",
}

# Domain-oriented synonym map.
# Left side = observed token, right side = canonical token we compare on.
SYNONYM_MAP: Dict[str, str] = {
    # Parties / customers
    "customer": "customer",
    "client": "customer",
    "consumer": "customer",
    "party": "customer",
    "account_holder": "customer",
    "accountholder": "customer",
    # Accounts / contracts
    "account": "account",
    "agreement": "account",
    "arrangement": "account",
    "contract": "account",
    "facility": "account",
    # Monetary amounts / balances
    "balance": "balance",
    "amount": "balance",
    "exposure": "balance",
    "outstanding": "balance",
    # Identifiers / codes
    "id": "identifier",
    "identifier": "identifier",
    "number": "identifier",
    "code": "identifier",
    "key": "identifier",
    # Dates
    "date": "date",
    "open": "date_open",
    "opening": "date_open",
    "inception": "date_open",
    "start": "date_open",
    "close": "date_close",
    "closing": "date_close",
    "maturity": "date_close",
    "end": "date_close",
    # Products / instruments
    "product": "product",
    "instrument": "product",
    "sku": "product",
    "item": "product",
    # Geography / address
    "address": "address",
    "street": "address",
    "city": "city",
    "town": "city",
    "postal": "postal_code",
    "postcode": "postal_code",
    "zipcode": "postal_code",

    # Asset & wealth management concepts
    "asset": "asset",
    "assets": "asset",
    "holding": "asset",
    "holdings": "asset",
    "position": "position",
    "portfolio": "portfolio",
    "book": "portfolio",
    "fund": "fund",
    "mutual": "fund",
    "scheme": "fund",
    "benchmark": "benchmark",
    "index": "benchmark",
    "sp_500_index": "benchmark",
    "euro_stoxx_50_index": "benchmark",
    "stoxx_index": "benchmark",
    "ftse_index": "benchmark",
    "dow_jones_index": "benchmark",
    "msci_index": "benchmark",
    # Books of record
    "accounting_book_of_record": "book_of_record",
    "investment_book_of_record": "book_of_record",
    "book_of_record": "book_of_record",
    # PnL
    "profit_and_loss": "pnl",
    "pnl": "pnl",
    # Transaction types / settlement styles
    "transaction": "transaction",
    "trade": "transaction",
    "dividend": "transaction",
    "interest": "transaction",
    "subscription": "transaction",
    "redemption": "transaction",
    "straight_through_processing": "stp",
    "delivery_versus_payment": "settlement_type",
    "receive_versus_payment": "settlement_type",
    "free_of_payment": "settlement_type",
    "foreign_exchange": "fx",
    "over_the_counter": "otc",
    "aum": "assets_under_management",
    "assets_under_management": "assets_under_management",
    "total_assets": "total_assets",
    "total_net_assets": "total_net_assets",
    "net_asset_value": "net_asset_value",
    "nav": "net_asset_value",
    "return": "return",
    "performance": "return",
    "yield": "return",
    "volatility": "risk",
    "vol": "risk",
    "risk": "risk",
    "srri": "risk",
    "duration": "duration",
    "tracking": "tracking_error",
    "alpha": "alpha",
    "beta": "beta",
    "liquidity": "liquidity",
    "redemption": "liquidity",
    "subscription": "liquidity",
    "management_fee": "management_fee",
    # Contact details
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    # Currencies
    "currency": "currency",
    # Contact details
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    # Instruments
    "equity": "equity",
    "stock": "equity",
    "share": "equity",
    "shares": "equity",
    "fixed_income": "fixed_income",
    "bond": "fixed_income",
    "note": "fixed_income",
    "debenture": "fixed_income",
    "floating_rate_note": "fixed_income",
    "asset_backed_security": "securitised_product",
    "mortgage_backed_security": "securitised_product",
    "collateralised_debt_obligation": "securitised_product",
    "collateralised_loan_obligation": "securitised_product",
    "collateralised_mortgage_obligation": "securitised_product",
    "future": "derivative",
    "forward": "derivative",
    "swap": "derivative",
    "interest_rate_swap": "derivative",
    "fx_swap": "derivative",
    "option": "derivative",
    "call_option": "derivative",
    "put_option": "derivative",
    "warrant": "derivative",
    "credit_default_swap": "derivative",
    # Tenor / horizon
    "one": "horizon_1y",
    "three": "horizon_3y",
}


_token_split_re = re.compile(r"[^a-z0-9]+")


def _raw_tokens(term: str) -> List[str]:
    """Tokenise a raw term without applying acronym/synonym maps."""
    term = term.strip()
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", term)
    lowered = spaced.lower()
    return [t for t in _token_split_re.split(lowered) if t]


def build_dynamic_acronym_map(
    source_terms: Iterable[str],
    target_terms: Iterable[str],
) -> Dict[str, str]:
    """
    Infer likely acronym expansions from the concrete source/target sets.

    Example: if we see source tokens like "tx" and target tokens frequently
    containing "transaction", we learn tx -> transaction for this request.
    """
    source_counts: Counter[str] = Counter()
    for term in source_terms:
        for tok in _raw_tokens(term):
            if 2 <= len(tok) <= 4 and tok.isalpha():
                source_counts[tok] += 1

    target_counts: Counter[str] = Counter()
    for term in target_terms:
        for tok in _raw_tokens(term):
            if len(tok) >= 5 and tok.isalpha():
                target_counts[tok] += 1

    if not target_counts:
        return {}

    by_initial: Dict[str, List[str]] = {}
    for tok in target_counts:
        by_initial.setdefault(tok[0], []).append(tok)

    dynamic: Dict[str, str] = {}
    max_freq = max(target_counts.values())

    for acronym, _count in source_counts.items():
        if acronym in ACRONYM_MAP:
            # Already covered by static dictionary.
            continue

        candidates = by_initial.get(acronym[0], [])
        if not candidates:
            continue

        best_tok: str | None = None
        best_score = 0.0
        for full in candidates:
            # Simple lexical similarity between acronym and candidate token.
            base = SequenceMatcher(None, acronym, full).ratio()
            freq_weight = 0.5 + 0.5 * (target_counts[full] / max_freq)
            score = base * freq_weight
            if score > best_score:
                best_score = score
                best_tok = full

        # Require a reasonably strong signal and that the candidate appears
        # in multiple target terms, so "transaction" wins when many targets
        # contain it.
        if best_tok and best_score >= 0.4 and target_counts[best_tok] >= 2:
            dynamic[acronym] = best_tok

    return dynamic


def learn_acronyms_from_feedback(
    db: Session,
    source_term: str,
    target_term: str,
    approved: bool,
) -> None:
    """
    Use an approved mapping to infer long-lived acronym expansions.

    Example: if the human approves ACT_TX_AMT -> Transaction Amount, and we don't
    already know tx -> transaction, we can persist that as a learned acronym.
    """
    if not approved:
        return

    source_tokens = _raw_tokens(source_term)
    target_tokens = _raw_tokens(target_term)

    candidates: Dict[str, str] = {}

    for s_tok in source_tokens:
        if not (2 <= len(s_tok) <= 6 and s_tok.isalpha()):
            continue
        if s_tok in ACRONYM_MAP:
            continue

        best_full: str | None = None
        best_score = 0.0
        for t_tok in target_tokens:
            if len(t_tok) <= len(s_tok) or not t_tok.isalpha():
                continue
            if t_tok[0] != s_tok[0]:
                continue
            score = SequenceMatcher(None, s_tok, t_tok).ratio()
            if score > best_score:
                best_score = score
                best_full = t_tok

        # Slightly higher threshold than the dynamic per-request logic since this
        # persists across sessions.
        if best_full and best_score >= 0.65:
            candidates[s_tok] = best_full

    if not candidates:
        return

    for token, expansion in candidates.items():
        row = (
            db.query(models.LearnedAcronym)
            .filter_by(token=token, expansion=expansion)
            .with_for_update(of=models.LearnedAcronym)
            .first()
        )
        if row:
            row.approval_count += 1
        else:
            db.add(
                models.LearnedAcronym(
                    token=token,
                    expansion=expansion,
                    approval_count=1,
                    rejection_count=0,
                )
            )
    # Caller is responsible for committing.


def normalize_term(term: str, dynamic_acronyms: Dict[str, str] | None = None) -> str:
    term = term.strip().lower()
    # Basic camelCase / PascalCase splitting
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", term)
    term = spaced.lower()
    tokens = [t for t in _token_split_re.split(term) if t]
    expanded: List[str] = []
    for tok in tokens:
        base = tok
        if tok in ACRONYM_MAP:
            base = ACRONYM_MAP[tok]
        elif dynamic_acronyms and tok in dynamic_acronyms:
            base = dynamic_acronyms[tok]
        canonical = SYNONYM_MAP.get(base, base)
        expanded.append(canonical)
    return " ".join(expanded)


def token_set(term: str, dynamic_acronyms: Dict[str, str] | None = None) -> Counter:
    return Counter(normalize_term(term, dynamic_acronyms).split())


def jaccard_similarity(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    if union == 0:
        return 0.0
    return intersection / union


def lexical_similarity(
    a: str,
    b: str,
    dynamic_acronyms: Dict[str, str] | None = None,
) -> float:
    na = normalize_term(a, dynamic_acronyms)
    nb = normalize_term(b, dynamic_acronyms)
    seq_score = SequenceMatcher(None, na, nb).ratio()
    jac_score = jaccard_similarity(
        token_set(a, dynamic_acronyms),
        token_set(b, dynamic_acronyms),
    )
    return max(seq_score, jac_score)


def _feedback_adjustment(
    db: Session,
    source_term: str,
    target_term: str,
    direction: MappingDirection,
) -> Tuple[float, bool]:
    """Return (delta, boosted) score adjustment from historical feedback.

    Positive delta for approvals, negative for rejections.
    """
    stmt = (
        select(
            func.count(
                func.nullif(models.TermPairFeedback.approved.is_(True), False)
            ).label("approvals"),
            func.count(
                func.nullif(models.TermPairFeedback.approved.is_(False), False)
            ).label("rejections"),
        )
        .where(models.TermPairFeedback.source_term == source_term)
        .where(models.TermPairFeedback.target_term == target_term)
        .where(models.TermPairFeedback.direction == direction.value)
    )
    result = db.execute(stmt).one_or_none()
    if not result:
        return 0.0, False
    approvals = int(result.approvals or 0)
    rejections = int(result.rejections or 0)
    total = approvals + rejections
    if total == 0:
        return 0.0, False
    # Map approval ratio into a small adjustment in [-0.15, +0.15]
    approval_ratio = approvals / total
    delta = (approval_ratio - 0.5) * 0.3
    return float(delta), True


def suggest_mappings(
    db: Session,
    direction: MappingDirection,
    source_terms: Iterable[str],
    target_terms: Iterable[str],
    top_k: int = 3,
    min_score: float = 0.2,
) -> List[SourceSuggestion]:
    targets = list(target_terms)
    sources = list(source_terms)
    suggestions: List[SourceSuggestion] = []

    dynamic_acronyms = build_dynamic_acronym_map(sources, targets)

    # Incorporate any long-lived learned acronyms from prior feedback.
    learned_rows = db.query(models.LearnedAcronym).all()
    learned_acronyms: Dict[str, str] = {}
    for row in learned_rows:
        key = row.token
        # For each token, pick the expansion with the highest approval bias.
        score = row.approval_count - row.rejection_count
        prev = learned_acronyms.get(key)
        if prev is None:
            learned_acronyms[key] = row.expansion
        else:
            # If there are multiple expansions for the same token, favour the
            # one with more approvals (simple heuristic).
            # We don't track per-expansion score here; for now, first-win or
            # manual clean-up is acceptable for this prototype.
            continue

    for source in sources:
        scored: List[Tuple[str, float, bool]] = []
        for target in targets:
            base_score = lexical_similarity(
                source,
                target,
                dynamic_acronyms={**learned_acronyms, **dynamic_acronyms},
            )
            delta, boosted = _feedback_adjustment(db, source, target, direction)
            score = max(0.0, min(1.0, base_score + delta))
            if score >= min_score:
                scored.append((target, score, boosted))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]
        candidates = [
            MappingCandidate(target_term=t, score=s, boosted_by_feedback=b)
            for t, s, b in top
        ]
        suggestions.append(SourceSuggestion(source_term=source, candidates=candidates))

    return suggestions

