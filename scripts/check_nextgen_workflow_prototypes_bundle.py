from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return cast(dict[str, Any], payload)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def resolve_repo_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def repo_rel_or_abs(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def extract_run_ids(staged_rows: object) -> list[str]:
    if not isinstance(staged_rows, list):
        return []
    run_ids: list[str] = []
    for row in cast(list[object], staged_rows):
        if not isinstance(row, dict):
            continue
        run_id = cast(dict[str, object], row).get("run_id")
        if isinstance(run_id, str) and run_id:
            run_ids.append(run_id)
    return run_ids


def check_bundle(bundle_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    notes: list[str] = []
    run_results: list[dict[str, Any]] = []

    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Bundle manifest is missing: {manifest_path}")

    bundle_manifest = load_json(manifest_path)
    emitted_run_ids = cast(list[str], bundle_manifest.get("emitted_run_ids", []))
    manifest_runs = cast(list[dict[str, Any]], bundle_manifest.get("runs", []))
    staged_run_plan = cast(dict[str, Any], bundle_manifest.get("staged_run_plan", {}))
    first_wave_ids = extract_run_ids(staged_run_plan.get("first_wave"))
    second_wave_ids = extract_run_ids(staged_run_plan.get("second_wave_if_first_wave_promising"))

    if first_wave_ids and emitted_run_ids != first_wave_ids:
        failures.append(
            "Emitted run ids do not match the staged first-wave list: "
            f"expected {first_wave_ids}, got {emitted_run_ids}."
        )
    if second_wave_ids and any(run_id in emitted_run_ids for run_id in second_wave_ids):
        failures.append(
            "Second-wave run ids were emitted even though they should stay deferred: "
            f"{sorted(run_id for run_id in emitted_run_ids if run_id in second_wave_ids)}."
        )

    for run_row in manifest_runs:
        run_id = cast(str, run_row["run_id"])
        run_manifest_path = resolve_repo_path(cast(str, run_row["run_manifest_path"]))
        starter_prompt_path = resolve_repo_path(cast(str, run_row["starter_prompt_path"]))
        run_failures: list[str] = []

        if not run_manifest_path.exists():
            run_failures.append(f"Run manifest missing: {repo_rel_or_abs(run_manifest_path)}")
            run_results.append({"run_id": run_id, "status": "fail", "failures": run_failures})
            failures.extend(f"{run_id}: {failure}" for failure in run_failures)
            continue

        run_manifest = load_json(run_manifest_path)
        input_basis = cast(dict[str, Any], run_manifest.get("input_basis", {}))
        default_attachments = cast(list[str], input_basis.get("default_attachments", []))
        combined_fallback = cast(list[str], input_basis.get("combined_attachment_fallback", []))
        output_contract = cast(dict[str, Any], run_manifest.get("output_contract", {}))
        run_identity = cast(dict[str, Any], run_manifest.get("run_identity", {}))

        for attachment in default_attachments:
            attachment_path = resolve_repo_path(attachment)
            if not attachment_path.exists():
                run_failures.append(f"Missing default attachment: {attachment}")

        if not starter_prompt_path.exists():
            run_failures.append(f"Starter prompt missing: {repo_rel_or_abs(starter_prompt_path)}")
        else:
            starter_text = starter_prompt_path.read_text(encoding="utf-8")
            if "{{" in starter_text or "}}" in starter_text:
                run_failures.append("Starter prompt still contains unresolved template placeholders.")

        primary_sidecar_filename = output_contract.get("primary_sidecar_filename")
        evidence_sidecar_filename = output_contract.get("evidence_sidecar_filename")
        sidecar_outputs = cast(list[Any], output_contract.get("sidecar_outputs", []))
        declared_paths: dict[str, str] = {}
        for row in sidecar_outputs:
            if not isinstance(row, dict):
                continue
            row_dict = cast(dict[str, Any], row)
            declared_paths[cast(str, row_dict.get("response_key"))] = Path(
                cast(str, row_dict.get("relative_path", ""))
            ).name
        if declared_paths.get(cast(str, output_contract.get("primary_artifact_key"))) != primary_sidecar_filename:
            run_failures.append("Primary sidecar filename does not match the declared sidecar output path.")
        if declared_paths.get("evidence_bundle") != evidence_sidecar_filename:
            run_failures.append("Evidence sidecar filename does not match the declared sidecar output path.")

        family_id = cast(str, run_identity.get("family_id", ""))
        if family_id == "simple_read_vs_structured_read_contrast_v1_1":
            source_artifacts = cast(dict[str, Any] | None, input_basis.get("source_artifacts"))
            if not source_artifacts:
                run_failures.append("Adjudication run is missing declared source artifacts.")
            else:
                for role in ("simple_read", "structured_read"):
                    artifact = cast(dict[str, Any] | None, source_artifacts.get(role))
                    if not artifact:
                        run_failures.append(f"Missing `{role}` source artifact declaration.")
                        continue
                    bundle_path = cast(str, artifact.get("bundle_path", ""))
                    if not bundle_path:
                        run_failures.append(f"Missing `{role}` bundle path.")
                        continue
                    resolved = resolve_repo_path(bundle_path)
                    if not resolved.exists():
                        run_failures.append(f"Missing `{role}` source artifact file: {bundle_path}")
                    if bundle_path not in default_attachments:
                        run_failures.append(f"`{role}` source artifact not listed in default_attachments.")
                    if bundle_path not in combined_fallback:
                        run_failures.append(
                            f"`{role}` source artifact not listed in combined_attachment_fallback."
                        )

        status = "pass" if not run_failures else "fail"
        run_results.append({"run_id": run_id, "status": status, "failures": run_failures})
        failures.extend(f"{run_id}: {failure}" for failure in run_failures)

    if not failures:
        notes.append("Bundle completeness checks passed.")

    return {
        "artifact_schema_id": "nextgen_workflow_prototype_bundle_check_v1",
        "bundle_root": repo_rel_or_abs(bundle_root),
        "overall_result": "pass" if not failures else "fail",
        "notes": notes,
        "failures": failures,
        "first_wave_run_ids": first_wave_ids,
        "second_wave_deferred_run_ids": second_wave_ids,
        "emitted_run_ids": emitted_run_ids,
        "run_results": run_results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check completeness of the emitted nextgen workflow prototype bundle."
    )
    parser.add_argument("--bundle-root", required=True, help="Bundle root path or repo-relative path.")
    parser.add_argument(
        "--report-out",
        default="",
        help="Optional path for a JSON check report.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    bundle_root = resolve_repo_path(args.bundle_root)
    report = check_bundle(bundle_root)

    if args.report_out:
        write_json(resolve_repo_path(args.report_out), report)

    print(f"bundle_root: {bundle_root.resolve()}")
    print(f"overall_result: {report['overall_result']}")
    print(f"emitted_run_ids: {report['emitted_run_ids']}")
    if report["failures"]:
        print("failures:")
        for failure in cast(list[str], report["failures"]):
            print(f"- {failure}")
    return 0 if report["overall_result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
