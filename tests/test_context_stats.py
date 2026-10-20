"""Zliczanie raportowanych tokenów bez szacowania brakujących danych."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from context_stats import usage_from_cli


class TokenUsageTest(unittest.TestCase):
    def test_codex_adds_completed_turns_without_double_counting_cache_or_reasoning(self):
        transcript = "\n".join(json.dumps(event) for event in [
            {"type": "item.completed", "usage": {"input_tokens": 9999}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20,
                                                "cached_input_tokens": 40, "reasoning_output_tokens": 5}},
            {"type": "turn.completed", "usage": {"input_tokens": 200, "output_tokens": 40,
                                                "cached_input_tokens": 80, "reasoning_output_tokens": 10}},
        ])
        tokens = usage_from_cli("codex", transcript)["tokens"]
        self.assertEqual(tokens["total_tokens"], 360)
        self.assertEqual(tokens["cached_input_tokens"], 120)
        self.assertEqual(tokens["reasoning_output_tokens"], 15)
        self.assertIsNone(tokens["cache_creation_input_tokens"])

    def test_claude_normalizes_input_cache_and_ignores_duplicate_model_breakdown(self):
        transcript = json.dumps({
            "usage": {"input_tokens": 10, "cache_read_input_tokens": 30,
                      "cache_creation_input_tokens": 60, "output_tokens": 20,
                      "output_tokens_details": {"thinking_tokens": 5}},
            "modelUsage": {"claude-test-model": {"inputTokens": 100, "outputTokens": 20}},
        })
        tokens = usage_from_cli("claude", transcript)["tokens"]
        self.assertEqual(tokens["total_tokens"], 120)
        self.assertEqual(tokens["reasoning_output_tokens"], 5)

    def test_unknown_usage_is_not_reported_as_zero(self):
        for provider, transcript in [("codex", "{}\nnot json\n[]"), ("claude", "{}"), ("claude", "not json")]:
            with self.subTest(provider=provider):
                tokens = usage_from_cli(provider, transcript)["tokens"]
                self.assertTrue(all(value is None for value in tokens.values()))

    def test_invalid_counts_are_not_silently_used(self):
        transcript = json.dumps({"type": "turn.completed", "usage": {"input_tokens": -1, "output_tokens": True}})
        self.assertIsNone(usage_from_cli("codex", transcript)["tokens"]["total_tokens"])


if __name__ == "__main__":
    unittest.main()
