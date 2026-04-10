from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from lab_output_tracks import CORE4_SHOWCASE_TICKERS


SCRIPT_VERSION = "lab_postdeploy_verify.py@v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab"
DEFAULT_REGISTRY = LAB_ROOT / "lab_cases_v1.json"
# Legacy Core4 backstage runtime tickers verified by postdeploy checks.
SHOWCASE_TICKERS = CORE4_SHOWCASE_TICKERS


@dataclass(frozen=True)
class SampleOutput:
    ticker: str
    detector_id: str
    year_from: int
    year_to: int
    filename: str


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_dict(value: Any) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    typed = cast(dict[Any, Any], value)
    output: dict[str, Any] = {}
    for key, item in typed.items():
        if not isinstance(key, str):
            return None
        output[key] = item
    return output


def as_list(value: Any) -> Optional[list[Any]]:
    if isinstance(value, list):
        return cast(list[Any], value)
    return None


def as_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    return None


def as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def normalize_base(base: str) -> str:
    trimmed = base.strip()
    if not trimmed:
        return ""
    return trimmed.rstrip("/")


def join_url(base: str, suffix: str) -> str:
    normalized_suffix = suffix.lstrip("/")
    if not base:
        return f"/{normalized_suffix}"
    return f"{base}/{normalized_suffix}"


def pick_sample_outputs(registry_path: Path) -> tuple[str, list[SampleOutput]]:
    payload = read_json(registry_path)
    root = as_dict(payload)
    if root is None:
        raise SystemExit("Registry root is not an object.")
    updated_at = as_str(root.get("updated_at")) or "<missing>"
    cases_any = as_list(root.get("cases"))
    if cases_any is None:
        raise SystemExit("Registry missing cases[] array.")

    picked: list[SampleOutput] = []
    seen_tickers: set[str] = set()

    for case_any in cases_any:
        case = as_dict(case_any)
        if case is None:
            continue

        ticker = (as_str(case.get("ticker")) or "").upper()
        year_from = as_int(case.get("year_from"))
        year_to = as_int(case.get("year_to"))
        if ticker not in SHOWCASE_TICKERS:
            continue
        if ticker in seen_tickers:
            continue
        if year_from is None or year_to is None:
            continue

        outputs_any = as_list(case.get("outputs")) or []
        for output_any in outputs_any:
            output = as_dict(output_any)
            if output is None:
                continue
            lens = as_str(output.get("cleaning_lens"))
            source = as_str(output.get("source_id"))
            detector_id = as_str(output.get("detector_id"))
            filename = as_str(output.get("filename"))
            if lens != "deboilerplated" or source != "edgar":
                continue
            if detector_id is None or filename is None:
                continue

            picked.append(
                SampleOutput(
                    ticker=ticker,
                    detector_id=detector_id,
                    year_from=year_from,
                    year_to=year_to,
                    filename=filename,
                )
            )
            seen_tickers.add(ticker)
            break

    return updated_at, picked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print post-deploy verification URLs and checks for Lab deterministic baseline."
    )
    parser.add_argument(
        "--site-base",
        default="",
        help=(
            "Base public site URL, e.g. https://example.com/sec-narrative-drift. "
            "If omitted, prints root-relative paths."
        ),
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help="Path to lab_cases_v1.json",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = REPO_ROOT / registry_path
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    base = normalize_base(args.site_base)
    updated_at, samples = pick_sample_outputs(registry_path)

    registry_url = join_url(base, "data/sec_narrative_drift_lab/lab_cases_v1.json")

    print("# Lab Post-Deploy Verification")
    print("")
    print(f"- script: {SCRIPT_VERSION}")
    print(f"- registry_path: {registry_path}")
    print(f"- expected_registry_updated_at: {updated_at}")
    print("")
    print("## 1) Registry URL")
    print(registry_url)
    print("Check: updated_at equals expected_registry_updated_at shown above.")
    print("")

    print("## 2) Deterministic sample output URLs")
    if not samples:
        print("No showcase deterministic samples found in registry.")
    else:
        for sample in samples:
            output_url = join_url(
                base,
                f"data/sec_narrative_drift_lab/{sample.ticker}/{sample.filename}",
            )
            print(
                f"- {sample.ticker} {sample.year_from}-{sample.year_to} {sample.detector_id}: {output_url}"
            )
            print("  Check: file loads (HTTP 200) and JSON parses.")
    print("")

    print("## 3) Lab UI URLs (incognito recommended)")
    print(join_url(base, "company/NVDA?tab=lab&from=2021&to=2022"))
    print(join_url(base, "company/KO?tab=lab&from=2023&to=2024"))
    print("Checks:")
    print("- Available outputs count is non-zero for deterministic methods.")
    print("- Missing artifacts appear as explicit states (not blank cards).")
    print("- Reload outputs button works and does not retain stale rejection cache.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

