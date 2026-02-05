from __future__ import annotations

import argparse
from typing import Optional

import build_lab_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke test for lab build outputs.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--pair", required=True, help="Year pair like 2023-2024")
    parser.add_argument("--section", default="10k_item1a")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    tickers = args.ticker.upper()
    pairs = args.pair

    build_lab_outputs.main(
        [
            "--tickers",
            tickers,
            "--pairs",
            pairs,
            "--section",
            args.section,
            "--detectors",
            "det_logodds_terms_v1,det_jsd_ngrams_v1,det_structure_artifacts_v1",
            "--lenses",
            "raw",
        ]
    )

    print("Smoke lab build complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
