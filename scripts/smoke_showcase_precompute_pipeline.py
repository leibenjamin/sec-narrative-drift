from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    roster_path = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_showcase_roster_v2_smoke.json"
    hero_path = REPO_ROOT / "public" / "data" / "sec_narrative_drift_lab" / "lab_showcase_hero_pairs_v2_smoke.json"
    bundle_dir = REPO_ROOT / "bundles" / f"showcase_llm_inputs_smoke_{timestamp}"

    run(
        [
            "python",
            str(REPO_ROOT / "scripts" / "build_showcase_roster_continuity.py"),
            "--tickers",
            "NVDA",
            "--section",
            "10k_item1a",
            "--year_min",
            "2023",
            "--year_max",
            "2024",
            "--also_try_year",
            "2025",
            "--out",
            str(roster_path),
        ]
    )

    run(
        [
            "python",
            str(REPO_ROOT / "scripts" / "select_showcase_hero_pairs.py"),
            "--roster",
            str(roster_path),
            "--out",
            str(hero_path),
        ]
    )

    run(
        [
            "python",
            str(REPO_ROOT / "scripts" / "build_showcase_llm_inputs_bundle.py"),
            "--roster",
            str(roster_path),
            "--hero",
            str(hero_path),
            "--out_dir",
            str(bundle_dir),
        ]
    )

    print("Smoke outputs:")
    print(f"- roster: {roster_path}")
    print(f"- hero pairs: {hero_path}")
    print(f"- bundle dir: {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
