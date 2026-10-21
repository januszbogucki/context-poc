"""Testy kontraktu generatora, bez sieci i prawdziwego tokena."""

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_application_context as generator

DOCUMENT = "# Kontekst aplikacji\n" + "\n".join(
    heading + "\n" + "Opis potwierdzony w src/Cart/Domain/Cart.php. " * 6
    for heading in generator.SECTIONS
)


class ContextGenerationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "docs/context").mkdir(parents=True)
        (self.root / "docs/context/instructions.md").write_text("Instrukcja {{GENERATOR}}")
        (self.root / "docs/context/repomap.md").write_text("Mapa")
        self.files = {"src/Cart.php": "pierwsza wersja", "src/Old.php": "stary moduł"}
        self.calls = []
        self.output = DOCUMENT
        self.exit_code = 0
        self.login_mode = "ChatGPT"
        self.claude_response = None
        self.provider_calls = []
        self.codex_usage = {"input_tokens": 100, "cached_input_tokens": 40,
                            "output_tokens": 20, "reasoning_output_tokens": 5}

    def run_process(self, args, **kwargs):
        if args == ["codex", "login", "status"]:
            self.assertNotIn("CODEX_ACCESS_TOKEN", kwargs["env"])
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertEqual(kwargs["env"].get("CODEX_HOME"), "/tmp/test-existing-codex-home")
            return subprocess.CompletedProcess(args, 0, stdout="Logged in using " + self.login_mode, stderr="")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n")
        self.provider_calls.append(args[0])
        self.calls.append(kwargs["input"])
        self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertNotIn("CODEX_API_KEY", kwargs["env"])
        self.assertNotIn("ANTHROPIC_API_KEY", kwargs["env"])
        if args[0] == "claude":
            self.assertEqual(kwargs["env"]["CLAUDE_CODE_OAUTH_TOKEN"], "fake-claude-token")
            self.assertNotIn("CODEX_ACCESS_TOKEN", kwargs["env"])
            self.assertIn("CLAUDE_CONFIG_DIR", kwargs["env"])
            self.assertEqual(args[args.index("--tools") + 1], "")
            self.assertNotIn("--bare", args)
            self.assertIn("--strict-mcp-config", args)
            response = self.claude_response if self.claude_response is not None else json.dumps(
                {"type": "result", "subtype": "success", "is_error": False, "result": self.output,
                 "usage": {"input_tokens": 10, "cache_read_input_tokens": 30,
                           "cache_creation_input_tokens": 60, "output_tokens": 20},
                 "modelUsage": {"claude-test-model": {}}}
            )
            return subprocess.CompletedProcess(args, self.exit_code, stdout=response, stderr="")
        self.assertEqual(args[:2], ["codex", "exec"])
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", kwargs["env"])
        self.assertIn("read-only", args)
        self.assertIn("--json", args)
        Path(args[args.index("--output-last-message") + 1]).write_text(self.output)
        transcript = json.dumps({"type": "item.completed", "text": self.output}) + "\n" + json.dumps(
            {"type": "turn.completed", "usage": self.codex_usage}
        )
        return subprocess.CompletedProcess(args, self.exit_code, stdout=transcript, stderr="")

    def generate(self, auth="token", provider="auto", claude_token=""):
        with patch.dict(os.environ, {"CODEX_ACCESS_TOKEN": "fake-test-token", "GITHUB_TOKEN": "private",
                                     "CLAUDE_CODE_OAUTH_TOKEN": claude_token, "ANTHROPIC_API_KEY": "fake-api-key",
                                     "GITHUB_ACTIONS": "false", "CODEX_HOME": "/tmp/test-existing-codex-home",
                                     "OPENAI_API_KEY": "fake-api-key", "CODEX_API_KEY": "fake-api-key"}), \
             patch.object(generator, "source_files", return_value=self.files), \
             patch.object(generator.subprocess, "run", side_effect=self.run_process):
            generator.generate(self.root, auth=auth, provider=provider)

    def snapshot(self, include_stats=False):
        directory = self.root / "docs/context"
        return {str(path.relative_to(directory)): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()
                and (include_stats or path.name not in ("stats.json", "stats.md"))}

    def test_statistics_measure_tokens_without_saving_transcript(self):
        self.generate()
        directory = self.root / "docs/context/codex"
        stats = json.loads((directory / "stats.json").read_text())
        self.assertEqual(stats["runs"][0]["tokens"]["total_tokens"], 120)
        self.assertEqual(stats["runs"][0]["tokens"]["reasoning_output_tokens"], 5)
        self.assertEqual(stats["runs"][0]["mode"], "full")
        self.assertNotIn("Opis potwierdzony", (directory / "stats.json").read_text())
        before = self.snapshot(include_stats=True)
        self.generate()
        self.assertEqual(before, self.snapshot(include_stats=True))
        self.files["src/Cart.php"] = "nowa wersja"
        self.generate()
        stats = json.loads((directory / "stats.json").read_text())
        self.assertEqual(len(stats["runs"]), 2)
        self.assertEqual(stats["runs"][1]["mode"], "incremental")
        self.assertEqual(stats["runs"][1]["files_analyzed"], 1)

    def test_claude_statistics_count_cache_once(self):
        self.generate(claude_token="fake-claude-token")
        path = self.root / "docs/context/claude/stats.json"
        run = json.loads(path.read_text())["runs"][0]
        self.assertEqual(run["tokens"]["input_tokens"], 100)
        self.assertEqual(run["tokens"]["total_tokens"], 120)
        self.assertEqual(run["models"], ["claude-test-model"])

    def test_failed_generation_is_recorded_without_touching_context(self):
        self.generate()
        before = self.snapshot()
        self.files["src/Cart.php"] = "zmiana"
        self.exit_code = 1
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(before, self.snapshot())
        path = self.root / "docs/context/codex/stats.json"
        run = json.loads(path.read_text())["runs"][-1]
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["tokens"]["total_tokens"], 120)

    def test_force_measures_another_full_run_without_source_changes(self):
        self.generate()
        with patch.dict(os.environ, {"CODEX_ACCESS_TOKEN": "fake-test-token", "CLAUDE_CODE_OAUTH_TOKEN": ""}), \
             patch.object(generator, "source_files", return_value=self.files), \
             patch.object(generator.subprocess, "run", side_effect=self.run_process):
            generator.generate(self.root, force=True)
        runs = json.loads((self.root / "docs/context/codex/stats.json").read_text())["runs"]
        self.assertEqual(len(runs), 2)
        self.assertEqual([run["mode"] for run in runs], ["full", "full"])

    def test_corrupt_statistics_stop_before_calling_model(self):
        self.generate()
        (self.root / "docs/context/codex/stats.json").write_text("broken")
        self.files["src/Cart.php"] = "zmiana"
        with self.assertRaisesRegex(ValueError, "Niepoprawna historia statystyk"):
            self.generate()
        self.assertEqual(len(self.calls), 1)

    def test_local_chatgpt_auth_uses_existing_login_without_token(self):
        self.generate(auth="chatgpt", claude_token="fake-claude-token")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.provider_calls, ["codex"])
        self.assertTrue((self.root / "docs/context/codex/application.md").is_file())

    def test_local_chatgpt_auth_rejects_api_key_login(self):
        self.login_mode = "API key"
        with self.assertRaisesRegex(ValueError, "Brak logowania ChatGPT"):
            self.generate(auth="chatgpt")
        self.assertEqual(len(self.calls), 0)

    def test_ci_cannot_use_local_chatgpt_auth(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            with self.assertRaisesRegex(ValueError, "tylko do pracy lokalnej"):
                generator.generate(self.root, auth="chatgpt")

    def test_first_full_then_skip_then_changed_and_deleted_only(self):
        self.generate()
        self.assertIn("TRYB: pełna budowa", self.calls[0])
        self.assertIn("stary moduł", self.calls[0])
        self.generate()
        self.assertEqual(len(self.calls), 1)
        self.files["src/Cart.php"] = "nowa wersja"
        self.files["src/New.php"] = "nowy moduł"
        del self.files["src/Old.php"]
        self.generate()
        request = self.calls[-1]
        self.assertIn("TRYB: aktualizacja przyrostowa", request)
        self.assertIn("POPRZEDNI KONTEKST", request)
        self.assertIn("nowy moduł", request)
        self.assertIn("USUNIĘTE PLIKI:\nsrc/Old.php", request)
        self.assertNotIn("stary moduł", request)
        self.assertNotIn("pierwsza wersja", request)

    def test_unchanged_sources_are_not_sent_again(self):
        self.generate()
        self.files["src/Cart.php"] = "zmiana"
        self.generate()
        self.assertNotIn("stary moduł", self.calls[-1])

    def test_prompt_change_forces_full_rebuild(self):
        self.generate()
        (self.root / "docs/context/instructions.md").write_text("Nowa instrukcja")
        self.generate()
        self.assertIn("TRYB: pełna budowa", self.calls[-1])

    def test_deletion_without_other_changes_updates_context(self):
        self.generate()
        del self.files["src/Old.php"]
        self.generate()
        self.assertIn("USUNIĘTE PLIKI:\nsrc/Old.php", self.calls[-1])
        self.assertNotIn("PLIK DODANY LUB ZMIENIONY", self.calls[-1])

    def test_invalid_state_forces_full_rebuild(self):
        self.generate()
        (self.root / "docs/context/codex/application-state.json").write_text("broken json")
        self.generate()
        self.assertIn("TRYB: pełna budowa", self.calls[-1])

    def test_failure_keeps_previous_context_and_state(self):
        self.generate()
        before = self.snapshot()
        self.files["src/Cart.php"] = "zmiana"
        for output, exit_code in [("", 0), (DOCUMENT, 1), (DOCUMENT + "fake-test-token", 0)]:
            self.output, self.exit_code = output, exit_code
            with self.assertRaises(ValueError):
                self.generate()
            self.assertEqual(before, self.snapshot())

    def test_missing_token_fails_before_model(self):
        with patch.dict(os.environ, {"CODEX_ACCESS_TOKEN": "", "CLAUDE_CODE_OAUTH_TOKEN": ""}), \
             patch.object(generator.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Brak tokena"):
                generator.generate(self.root)
            run.assert_not_called()

    def test_provider_priority_for_all_secret_combinations(self):
        for claude_token, codex_token, expected in [
            ("", "", "none"), ("", "codex", "codex"),
            ("claude", "", "claude"), ("claude", "codex", "claude"),
            ("  ", "codex", "codex"),
        ]:
            with self.subTest(expected=expected, claude=bool(claude_token), codex=bool(codex_token)), \
                 patch.dict(os.environ, {"CLAUDE_CODE_OAUTH_TOKEN": claude_token, "CODEX_ACCESS_TOKEN": codex_token}):
                self.assertEqual(generator.select_provider(), expected)

    def test_claude_wins_and_preserves_incremental_updates(self):
        self.generate(claude_token="fake-claude-token")
        self.assertEqual(self.provider_calls, ["claude"])
        self.assertIn("Instrukcja Claude", self.calls[0])
        state_path = self.root / "docs/context/claude/application-state.json"
        self.assertEqual(json.loads(state_path.read_text())["provider"], "claude")
        self.generate(claude_token="fake-claude-token")
        self.assertEqual(len(self.calls), 1)
        self.files["src/Cart.php"] = "nowa wersja"
        self.generate(claude_token="fake-claude-token")
        self.assertIn("TRYB: aktualizacja przyrostowa", self.calls[-1])
        self.assertNotIn("stary moduł", self.calls[-1])

    def test_providers_keep_separate_results_and_resume_their_own_state(self):
        self.generate()
        codex_result = (self.root / "docs/context/codex/application.md").read_bytes()
        self.output = DOCUMENT.replace("Opis potwierdzony", "Opis Claude potwierdzony")
        self.generate(claude_token="fake-claude-token")
        claude_result = (self.root / "docs/context/claude/application.md").read_bytes()
        self.assertEqual(codex_result, (self.root / "docs/context/codex/application.md").read_bytes())
        self.assertNotEqual(codex_result, claude_result)
        # Powrót do Codex bez zmiany źródeł korzysta z jego własnego stanu.
        self.generate(provider="codex", claude_token="fake-claude-token")
        self.assertEqual(self.provider_calls, ["codex", "claude"])
        self.files["src/Cart.php"] = "zmiana"
        self.output = DOCUMENT
        self.generate(provider="codex", claude_token="fake-claude-token")
        self.assertEqual(self.provider_calls, ["codex", "claude", "codex"])
        self.assertIn("TRYB: aktualizacja przyrostowa", self.calls[-1])
        self.assertNotIn("Opis Claude potwierdzony", self.calls[-1])
        self.assertEqual(claude_result, (self.root / "docs/context/claude/application.md").read_bytes())

    def test_claude_only_token_generates_without_codex(self):
        with patch.dict(os.environ, {"CODEX_ACCESS_TOKEN": "", "CLAUDE_CODE_OAUTH_TOKEN": "fake-claude-token"}), \
             patch.object(generator, "source_files", return_value=self.files), \
             patch.object(generator.subprocess, "run", side_effect=self.run_process):
            generator.generate(self.root)
        self.assertEqual(self.provider_calls, ["claude"])

    def test_explicit_provider_requires_its_own_token(self):
        with patch.dict(os.environ, {"CODEX_ACCESS_TOKEN": "codex", "CLAUDE_CODE_OAUTH_TOKEN": ""}):
            with self.assertRaisesRegex(ValueError, "Brak CLAUDE_CODE_OAUTH_TOKEN"):
                generator.generate(self.root, provider="claude")

    def test_claude_failure_does_not_fall_back_or_overwrite_state(self):
        self.generate(claude_token="fake-claude-token")
        before = self.snapshot()
        self.files["src/Cart.php"] = "zmiana"
        for response in ["not json", "[]", json.dumps({"is_error": True, "subtype": "error", "result": DOCUMENT}),
                         json.dumps({"is_error": False, "subtype": "success", "result": ""}),
                         json.dumps({"is_error": False, "subtype": "success", "result": DOCUMENT + "fake-claude-token"})]:
            with self.subTest(response=response[:30]):
                self.claude_response = response
                with self.assertRaises(ValueError):
                    self.generate(claude_token="fake-claude-token")
                self.assertEqual(before, self.snapshot())
        self.assertEqual(set(self.provider_calls), {"claude"})

    def test_explicit_claude_cannot_use_chatgpt_auth(self):
        with self.assertRaisesRegex(ValueError, "tylko dla Codex"):
            self.generate(auth="chatgpt", provider="claude")

    def test_file_selection_excludes_credentials_and_local_configuration(self):
        names = ["src/Cart.php", "src/Payment/StripeCredentials.php", "config/app.local.php",
                 "config/secrets/database.php", "config/routes.php", "tests/run.php", "composer.json"]
        for name in names:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        # git ls-files nadal zwraca plik usunięty lokalnie przed git add -u.
        result = subprocess.CompletedProcess([], 0, stdout="\0".join([*names, "src/Removed.php"]))
        with patch.object(generator.subprocess, "run", return_value=result):
            files = generator.source_files(self.root)
        self.assertEqual(set(files), {"src/Cart.php", "config/routes.php", "composer.json"})


if __name__ == "__main__":
    unittest.main()
