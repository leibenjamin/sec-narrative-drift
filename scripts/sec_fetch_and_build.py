import argparse
from typing import Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SEC Narrative Drift builder (skeleton). "
            "Ticket 9 provides CLI + dependencies only."
        )
    )
    parser.add_argument("--ticker", help="Ticker symbol (e.g., AAPL).")
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years to include (default: 10).",
    )
    parser.add_argument("--out", help="Output folder for JSON artifacts.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of filings to process.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.ticker or not args.out:
        parser.error("--ticker and --out are required for execution.")

    print(
        "sec_fetch_and_build.py is a stub. "
        "Ticket 11+ will add SEC fetch, extraction, metrics, and output."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
