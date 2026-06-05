from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fill_once import NA, canonical_hash, load_json, resolve_answers, validate_map  # noqa: E402
from generate_samples import generate_random, quota_counts  # noqa: E402


class FixedRng:
    def random(self) -> float:
        return 0.99

    def choice(self, values: list[str]) -> str:
        return values[0]


class OfflineLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.questionnaire_map = load_json(ROOT / "questionnaire_map.json")

    def test_starter_map_is_structurally_valid(self) -> None:
        self.assertEqual(validate_map(self.questionnaire_map), [])

    def test_formal_generation_is_blocked_until_yes_branches_are_explored(self) -> None:
        errors = validate_map(self.questionnaire_map, require_verified=True)
        self.assertTrue(any("branch exploration" in error for error in errors))

    def test_hidden_children_are_na(self) -> None:
        payload = json.loads((ROOT / "examples/all_no.json").read_text(encoding="utf-8"))
        resolved = resolve_answers(self.questionnaire_map, payload["answers"])
        self.assertEqual(resolved["fear.scary_elements"], NA)
        self.assertEqual(resolved["fear.scary_frequency"], NA)

    def test_visible_question_cannot_be_na(self) -> None:
        with self.assertRaisesRegex(ValueError, "visible questions cannot"):
            resolve_answers(
                self.questionnaire_map,
                {
                    "violence.exists": "no",
                    "fear.contains_disturbing_content": "yes",
                    "fear.scary_elements": NA,
                    "fear.horrifying_elements": "no",
                    "fear.scary_frequency": NA,
                },
            )

    def test_hash_ignores_hidden_na_nodes(self) -> None:
        left = {"root": "no", "child": NA}
        right = {"root": "no"}
        self.assertEqual(canonical_hash(left), canonical_hash(right))

    def test_no_biased_generator_respects_tree(self) -> None:
        answers = generate_random(self.questionnaire_map, "no_biased", FixedRng())
        self.assertEqual(answers["fear.contains_disturbing_content"], "no")
        self.assertEqual(answers["fear.scary_elements"], NA)

    def test_quota_is_exact(self) -> None:
        self.assertEqual(
            quota_counts(1000),
            {"no_biased": 300, "yes_biased": 200, "balanced_random": 500},
        )


if __name__ == "__main__":
    unittest.main()
