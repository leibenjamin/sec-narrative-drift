from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from typing import cast

ROOT_DIR = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT_DIR / "_tmp_test_runs"
sys.path.insert(0, str(ROOT_DIR))

import check_nextgen_workflow_prototypes_bundle as checker  # noqa: E402


class NextgenBundleCheckTest(unittest.TestCase):
    def write_json(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def build_fake_bundle(self, repo: Path, *, with_failure: bool) -> Path:
        bundle_root = repo / "bundles" / "nextgen_workflow_prototypes_v1_1_2026-04-10"
        run_id = "simple_vs_structured__WMT_2025_2026_10k_item1a"
        deferred_run_id = "simple_vs_structured__META_2024_2025_10k_item1a"

        prompt_path = bundle_root / "shared" / "prompts" / "simple_read_vs_structured_read_contrast_v1_1.md"
        fy_a_path = bundle_root / "fixtures" / "WMT_2025_2026_10k_item1a" / "i2_tagged_document_packet_v1_FY2025.json"
        fy_b_path = bundle_root / "fixtures" / "WMT_2025_2026_10k_item1a" / "i2_tagged_document_packet_v1_FY2026.json"
        combined_path = bundle_root / "fixtures" / "WMT_2025_2026_10k_item1a" / "i2_tagged_document_packet_v1.rendered_inputs.json"
        simple_source_path = bundle_root / "runs" / run_id / "source_artifacts" / "simple_read_source.json"
        structured_source_path = bundle_root / "runs" / run_id / "source_artifacts" / "structured_read_source.json"
        starter_prompt_path = bundle_root / "runs" / run_id / "starter_prompt.txt"
        run_manifest_path = bundle_root / "runs" / run_id / "run_manifest.json"

        for path in [
            prompt_path,
            fy_a_path,
            fy_b_path,
            combined_path,
            simple_source_path,
            structured_source_path,
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")

        starter_prompt_path.parent.mkdir(parents=True, exist_ok=True)
        starter_prompt_path.write_text(
            "Use the attached files only.\n{{UNRESOLVED}}\n" if with_failure else "Use the attached files only.\n",
            encoding="utf-8",
        )

        run_manifest = {
            "run_identity": {
                "family_id": "simple_read_vs_structured_read_contrast_v1_1",
            },
            "input_basis": {
                "default_attachments": [
                    prompt_path.relative_to(repo).as_posix(),
                    fy_a_path.relative_to(repo).as_posix(),
                    fy_b_path.relative_to(repo).as_posix(),
                    simple_source_path.relative_to(repo).as_posix(),
                    structured_source_path.relative_to(repo).as_posix(),
                ],
                "combined_attachment_fallback": [
                    prompt_path.relative_to(repo).as_posix(),
                    combined_path.relative_to(repo).as_posix(),
                    simple_source_path.relative_to(repo).as_posix(),
                    structured_source_path.relative_to(repo).as_posix(),
                ],
                "source_artifacts": None
                if with_failure
                else {
                    "simple_read": {
                        "bundle_path": simple_source_path.relative_to(repo).as_posix(),
                    },
                    "structured_read": {
                        "bundle_path": structured_source_path.relative_to(repo).as_posix(),
                    },
                },
            },
            "output_contract": {
                "primary_artifact_key": "simple_vs_structured_adjudication",
                "primary_sidecar_filename": "simple_vs_structured_adjudication_v1_1.json",
                "evidence_sidecar_filename": "evidence_bundle_v1.json",
                "sidecar_outputs": [
                    {
                        "response_key": "simple_vs_structured_adjudication",
                        "relative_path": (
                            bundle_root
                            / "runs"
                            / run_id
                            / "artifacts"
                            / "simple_vs_structured_adjudication_v1_1.json"
                        ).relative_to(repo).as_posix(),
                    },
                    {
                        "response_key": "evidence_bundle",
                        "relative_path": (
                            bundle_root / "runs" / run_id / "artifacts" / "evidence_bundle_v1.json"
                        ).relative_to(repo).as_posix(),
                    },
                ],
            },
        }
        self.write_json(run_manifest_path, run_manifest)

        bundle_manifest = {
            "artifact_schema_id": "nextgen_workflow_prototype_bundle_manifest_v1",
            "bundle_root": bundle_root.relative_to(repo).as_posix(),
            "emitted_run_ids": [run_id] if not with_failure else [run_id, deferred_run_id],
            "staged_run_plan": {
                "first_wave": [{"run_id": run_id}],
                "second_wave_if_first_wave_promising": [{"run_id": deferred_run_id}],
            },
            "runs": [
                {
                    "run_id": run_id,
                    "run_manifest_path": run_manifest_path.relative_to(repo).as_posix(),
                    "starter_prompt_path": starter_prompt_path.relative_to(repo).as_posix(),
                }
            ],
        }
        self.write_json(bundle_root / "manifest.json", bundle_manifest)
        return bundle_root

    def test_check_bundle_passes_for_complete_fake_bundle(self) -> None:
        repo = TMP_ROOT / "bundle_check_case_a"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        original_repo_root = checker.REPO_ROOT
        checker.REPO_ROOT = repo
        try:
            bundle_root = self.build_fake_bundle(repo, with_failure=False)
            report = checker.check_bundle(bundle_root)
            self.assertEqual("pass", report["overall_result"])
            self.assertEqual([], report["failures"])
        finally:
            checker.REPO_ROOT = original_repo_root
            shutil.rmtree(repo, ignore_errors=True)

    def test_check_bundle_fails_for_placeholder_and_missing_source_artifacts(self) -> None:
        repo = TMP_ROOT / "bundle_check_case_b"
        shutil.rmtree(repo, ignore_errors=True)
        repo.mkdir(parents=True, exist_ok=True)
        original_repo_root = checker.REPO_ROOT
        checker.REPO_ROOT = repo
        try:
            bundle_root = self.build_fake_bundle(repo, with_failure=True)
            report = checker.check_bundle(bundle_root)
            self.assertEqual("fail", report["overall_result"])
            failures = cast(list[str], report["failures"])
            self.assertTrue(any("unresolved template placeholders" in failure for failure in failures), failures)
            self.assertTrue(any("missing declared source artifacts" in failure.lower() for failure in failures), failures)
            self.assertTrue(any("Second-wave run ids were emitted" in failure for failure in failures), failures)
        finally:
            checker.REPO_ROOT = original_repo_root
            shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
