import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "d5n_release_status.py"


def load_release_status():
    spec = importlib.util.spec_from_file_location("d5n_release_status", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("não foi possível carregar d5n_release_status.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.release_status


class ReleaseStatusTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "d5n_release_status.py ainda não foi implementado")
        self.release_status = load_release_status()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.state = self.root / "state"
        (self.repo / "audio").mkdir(parents=True)
        self.state.mkdir(parents=True)
        self.date = "2026-07-23"

    def write_valid_release(self):
        audio = self.repo / "audio" / f"d5n-ep042-{self.date}.mp3"
        audio.write_bytes(b"valid-audio-fixture")
        digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        (self.repo / "episode-counter.json").write_text(
            json.dumps(
                {
                    "last_episode": 42,
                    "history": [
                        {
                            "num": "042",
                            "date": self.date,
                            "file": audio.name,
                            "exists": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.state / f"published-{self.date}.json").write_text(
            json.dumps(
                {
                    "editorial_date": self.date,
                    "episode": "042",
                    "audio": f"audio/{audio.name}",
                    "sha256": digest,
                    "commit": "a" * 40,
                }
            ),
            encoding="utf-8",
        )
        return audio

    def test_missing_receipt_is_not_published(self):
        result = self.release_status(self.repo, self.state, self.date)
        self.assertFalse(result["published"])
        self.assertEqual(result["reason"], "missing_receipt")

    def test_valid_receipt_audio_and_counter_are_published(self):
        self.write_valid_release()
        result = self.release_status(self.repo, self.state, self.date)
        self.assertTrue(result["published"])
        self.assertEqual(result["reason"], "published")

    def test_tampered_audio_invalidates_receipt(self):
        audio = self.write_valid_release()
        audio.write_bytes(b"tampered")
        result = self.release_status(self.repo, self.state, self.date)
        self.assertFalse(result["published"])
        self.assertEqual(result["reason"], "audio_sha256_mismatch")

    def test_counter_must_confirm_the_same_episode(self):
        self.write_valid_release()
        (self.repo / "episode-counter.json").write_text(
            json.dumps({"last_episode": 41, "history": []}), encoding="utf-8"
        )
        result = self.release_status(self.repo, self.state, self.date)
        self.assertFalse(result["published"])
        self.assertEqual(result["reason"], "counter_missing_episode")


class DeployFailClosedIntegrationTests(unittest.TestCase):
    def test_missing_daily_audio_blocks_without_counter_or_receipt_mutation(self):
        with tempfile.TemporaryDirectory() as tmp_value:
            root = Path(tmp_value)
            repo = root / "repo"
            state = root / "state"
            cron = root / "cron"
            profile_cron = root / "profile-cron"
            trends = root / "trends.txt"
            (repo / "scripts").mkdir(parents=True)
            state.mkdir()
            cron.mkdir()
            profile_cron.mkdir()
            shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
            counter = repo / "episode-counter.json"
            counter.write_text(
                json.dumps({"last_episode": 41, "history": []}) + "\n",
                encoding="utf-8",
            )
            trends.write_text(
                ("GLOBAL notícia real https://example.com/global\n"
                 "BRASIL notícia real https://example.com/brasil\n"
                 "TECH notícia real https://example.com/tech\n"
                 "ECONOMIA notícia real https://example.com/economia\n") * 3,
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "D5N Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "d5n@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
            before = counter.read_bytes()

            env = os.environ.copy()
            env.update(
                {
                    "D5N_DATE": "2026-07-26",  # domingo também exige episódio
                    "D5N_REPO": str(repo),
                    "D5N_STATE_DIR": str(state),
                    "D5N_CRON_AUDIO": str(cron),
                    "D5N_CRON_AUDIO_D5N": str(profile_cron),
                    "D5N_TRENDS_FILE": str(trends),
                }
            )
            completed = subprocess.run(
                ["bash", str(Path(__file__).parents[1] / "deploy_d5n_site.sh")],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
            self.assertIn("Nenhum MP3 válido para hoje", completed.stdout)
            self.assertEqual(counter.read_bytes(), before)
            self.assertFalse((state / "published-2026-07-26.json").exists())
            self.assertTrue((state / "failed").exists())


if __name__ == "__main__":
    unittest.main()
