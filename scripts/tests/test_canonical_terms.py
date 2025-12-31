import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT_DIR))

from build_canonical_terms import ValidationError, compile_terms, load_yaml  # noqa: E402


class TestCanonicalTerms(unittest.TestCase):
    def test_ok_compiles_json(self) -> None:
        payload = load_yaml(FIXTURES_DIR / "canonical_terms_ok.yml")
        output, _warnings = compile_terms(payload)
        variant_map = output.get("variantToConcept", {})
        self.assertIsInstance(variant_map, dict)
        self.assertEqual(variant_map.get("ai"), "ai")

    def test_duplicate_variant_fails(self) -> None:
        payload = load_yaml(FIXTURES_DIR / "canonical_terms_dupes.yml")
        with self.assertRaises(ValidationError):
            compile_terms(payload)

    def test_overlap_variant_fails(self) -> None:
        payload = load_yaml(FIXTURES_DIR / "canonical_terms_overlap.yml")
        with self.assertRaises(ValidationError):
            compile_terms(payload)

    def test_short_token_requires_whitelist(self) -> None:
        payload = {
            "version": "1.0",
            "concepts": [
                {"id": "short", "label": "Short", "variants": ["it"]},
            ],
        }
        with self.assertRaises(ValidationError):
            compile_terms(payload)

    def test_longest_match_wins_sorting(self) -> None:
        payload = {
            "version": "1.0",
            "concepts": [
                {
                    "id": "ai",
                    "label": "Artificial intelligence",
                    "variants": ["ai", "artificial intelligence"],
                }
            ],
        }
        output, _warnings = compile_terms(payload)
        concepts = output.get("concepts", [])
        self.assertIsInstance(concepts, list)
        first = concepts[0]
        variants = first.get("variants")
        self.assertIsInstance(variants, list)
        self.assertEqual(variants[0], "artificial intelligence")


if __name__ == "__main__":
    unittest.main()
