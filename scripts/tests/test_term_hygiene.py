import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT_DIR.parent
DATA_DIR = REPO_ROOT / "public" / "data" / "sec_narrative_drift"
sys.path.insert(0, str(ROOT_DIR))

from sec_check_term_hygiene import find_duplicate_terms  # noqa: E402


class TestTermHygiene(unittest.TestCase):
    def test_no_duplicate_token_terms(self) -> None:
        if not DATA_DIR.exists():
            self.skipTest("public data directory not found")
        duplicates = find_duplicate_terms(DATA_DIR)
        message = "Duplicate-token terms found:\n" + "\n".join(duplicates)
        self.assertFalse(duplicates, msg=message)


if __name__ == "__main__":
    unittest.main()
