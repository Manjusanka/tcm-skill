from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_package", ROOT / "scripts" / "validate_package.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PackageContractTest(unittest.TestCase):
    def test_required_files(self) -> None:
        VALIDATOR.validate_required_files()

    def test_configuration_invariants(self) -> None:
        config = VALIDATOR.validate_skill_config()
        self.assertEqual(config["name"], "tcm-safe-knowledge-qa")

    def test_json_schemas(self) -> None:
        self.assertGreaterEqual(VALIDATOR.validate_json_schemas(), 7)

    def test_eval_cases(self) -> None:
        self.assertGreaterEqual(VALIDATOR.validate_eval_cases(), 12)

    def test_capability_graph(self) -> None:
        self.assertGreaterEqual(VALIDATOR.validate_capability_graph(), 20)


if __name__ == "__main__":
    unittest.main()
