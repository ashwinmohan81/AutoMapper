#!/usr/bin/env python3
"""
Mine acronym candidates from the eval dataset (and optional term files).

Ensures acronym coverage is derived from the same terms we test against,
so adding new eval cases surfaces missing acronyms.

Usage (from repo root):

    python backend/scripts/mine_acronyms.py

    # With extra terms file (one term per line):
    python backend/scripts/mine_acronyms.py --terms path/to/terms.txt

Output: report of (1) short tokens already in ACRONYM_MAP, (2) suggested
expansions from targets (not yet in map), (3) short tokens with no suggested
expansion (add manually or add target terms).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import matching  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Mine acronym candidates from eval dataset and optional term files.")
    ap.add_argument("--terms", type=Path, help="Extra file with one term per line")
    ap.add_argument("--yaml", action="store_true", help="Print suggested entries as YAML for acronyms.yml")
    args = ap.parse_args()

    # Collect all source and target terms from eval dataset
    from tests.run_eval import DATASET  # noqa: E402

    all_sources: list[str] = []
    all_targets: list[str] = []
    for case in DATASET:
        all_sources.extend(case.source_terms)
        all_targets.extend(case.target_terms)

    if args.terms and args.terms.exists():
        with args.terms.open() as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#"):
                    all_sources.append(t)

    short = matching.short_tokens_from_terms(all_sources)
    in_map = short & set(matching.ACRONYM_MAP)
    not_in_map = short - set(matching.ACRONYM_MAP)

    dynamic = matching.build_dynamic_acronym_map(all_sources, all_targets)
    suggested = {k: v for k, v in dynamic.items() if k in not_in_map}
    missing = not_in_map - set(suggested)

    print("Short tokens (2–4 char alpha) from eval sources:", len(short))
    print("  Already in ACRONYM_MAP:", len(in_map))
    print("  Suggested by target terms (add to acronyms.yml):", len(suggested))
    print("  Missing (no expansion inferred):", len(missing))
    if missing:
        print("  Missing tokens:", sorted(missing))

    if args.yaml and suggested:
        print("\n# Suggested additions for backend/config/acronyms.yml")
        for k in sorted(suggested):
            print(f"{k}: {suggested[k]}")
    elif suggested:
        print("\nSuggested acronym -> expansion (run with --yaml to emit YAML):")
        for k in sorted(suggested):
            print(f"  {k} -> {suggested[k]}")


if __name__ == "__main__":
    main()
