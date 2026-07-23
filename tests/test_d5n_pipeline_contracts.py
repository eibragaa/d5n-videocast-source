import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO = Path(__file__).parents[1]
PROFILE_MIXER = Path("/root/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py")
WRAPPER = Path("/root/.hermes/scripts/drop5news-mixer-exec.sh")
PRE_GEN_GATE = Path("/root/.hermes/scripts/d5n-pre-gen-gate.py")
ENGINE = Path("/root/.hermes/scripts/babysitter-engine/babysitter.py")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class PipelineContractTests(unittest.TestCase):
    def test_manha_conectada_site_loads_only_canonical_published_episodes(self):
        generator = load_module(REPO / "gerar_pagina_d5n.py", "d5n_generator_manha_conectada")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            audio_dir = base / "audio"
            manifest_dir = base / "manifests" / "manha-conectada"
            audio_dir.mkdir(parents=True)
            manifest_dir.mkdir(parents=True)

            canonical_audio = audio_dir / "manha-conectada-2026-07-21.mp3"
            prototype_audio = audio_dir / "manha-conectada-2026-07-22-prototipo.mp3"
            canonical_audio.write_bytes(b"canonical-audio")
            prototype_audio.write_bytes(b"prototype-audio")
            (base / "source-manha-2026-07-21.md").write_text(
                "# MANHÃ CONECTADA — 21/07/2026\n\n"
                "## Roteiro aprovado\n\n"
                "O Brasil reage às tarifas; a tecnologia avança na saúde; e os mercados acompanham novos indicadores. "
                "Eu sou Antonio e esta é a Manhã Conectada, do Drop Five News.\n\n"
                "## Fontes coletadas\n",
                encoding="utf-8",
            )
            (manifest_dir / "2026-07-21.json").write_text(json.dumps({
                "program": "MANHÃ CONECTADA",
                "date": "2026-07-21",
                "prototype": False,
                "voice": "pt-BR-AntonioNeural",
                "output": str(canonical_audio),
                "source_file": str(base / "source-manha-2026-07-21.md"),
                "audio": {"duration": 298.2},
                "text_gate": {"words": 703},
            }), encoding="utf-8")
            (manifest_dir / "2026-07-22-prototipo.json").write_text(json.dumps({
                "program": "MANHÃ CONECTADA",
                "date": "2026-07-22",
                "prototype": True,
                "output": str(prototype_audio),
                "audio": {"duration": 280},
            }), encoding="utf-8")

            original_base, original_audio = getattr(generator, "BASE"), getattr(generator, "AUDIO_DIR")
            setattr(generator, "BASE", str(base))
            setattr(generator, "AUDIO_DIR", str(audio_dir))
            try:
                episodes = generator.load_manha_conectada_episodes()
                rendered = generator.render_manha_conectada_program(episodes)
            finally:
                setattr(generator, "BASE", original_base)
                setattr(generator, "AUDIO_DIR", original_audio)

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["date"], "2026-07-21")
        self.assertEqual(episodes[0]["path"], "/audio/manha-conectada-2026-07-21.mp3")
        self.assertEqual(episodes[0]["presenter"], "Antonio")
        self.assertIn('id="manha-conectada"', rendered)
        self.assertIn('id="morningAudio"', rendered)
        self.assertIn('class="morning-episode is-active"', rendered)
        self.assertEqual(rendered.count('class="morning-episode'), 1)
        self.assertIn("O Brasil reage às tarifas", rendered)
        self.assertNotIn("prototipo", rendered)

    def test_manha_conectada_cron_publishes_site_fail_closed(self):
        cron = (REPO / "scripts" / "run-manha-conectada-cron.sh").read_text(encoding="utf-8")
        publisher_path = REPO / "scripts" / "publish-manha-conectada-site.sh"

        self.assertTrue(publisher_path.exists())
        publisher = publisher_path.read_text(encoding="utf-8")
        self.assertIn("publish-manha-conectada-site.sh", cron)
        self.assertNotIn("|| true", cron)
        self.assertIn("gerar_pagina_d5n.py", publisher)
        self.assertIn("--site-only", publisher)
        self.assertIn("d5n-verify-site.py", publisher)
        self.assertNotIn("git add .", publisher)
        self.assertIn('git add -- "$AUDIO" "$SOURCE" "$MANIFEST" index.html', publisher)

    def test_cta_is_after_news_and_before_outro(self):
        mixer = load_module(PROFILE_MIXER, "d5n_profile_mixer")
        sections = [name for name, _, _ in mixer.SECOES]

        self.assertGreater(sections.index("cta"), sections.index("economia"))
        self.assertLess(sections.index("cta"), sections.index("outro"))

    def test_site_credits_follow_the_restored_weekly_voice_schedule(self):
        generator = load_module(REPO / "gerar_pagina_d5n.py", "d5n_generator_voice_schedule")
        expected = {
            "2026-07-20": "Thalita",              # segunda
            "2026-07-21": "Francisca",            # terça
            "2026-07-22": "Thalita",              # quarta
            "2026-07-23": "Francisca",            # quinta
            "2026-07-24": "Thalita + Francisca",  # sexta
            "2026-07-25": "Thalita",              # sábado
        }

        for editorial_date, presenter in expected.items():
            self.assertEqual(generator.historical_voice_name(editorial_date), presenter)
            self.assertEqual(generator.get_voice_of_day(editorial_date)["name"], presenter)
        self.assertIsNone(generator.get_voice_of_day("2026-07-26"))

    def test_mixer_aborts_on_missing_required_inputs(self):
        source = PROFILE_MIXER.read_text(encoding="utf-8")
        self.assertIn("Seções obrigatórias sem roteiro", source)
        self.assertIn("Seção obrigatória sem áudio", source)
        self.assertIn("Trilha obrigatória ausente", source)

    def test_legacy_wrapper_is_fail_closed_and_uses_effective_profile(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertNotIn("|| true", source)
        self.assertIn("/root/.hermes/profiles/d5n/skills/media/trends-podcast/scripts/drop5news-mixer-v9.py", source)
        self.assertIn("/root/repositorio/d5n-videocast-source/deploy_d5n_site.sh", source)

    def test_pre_generation_gate_rejects_missing_input(self):
        source = PRE_GEN_GATE.read_text(encoding="utf-8")
        self.assertIn("diretório de roteiro ausente", source)
        self.assertIn("seções ausentes ou vazias", source)

    def test_periodic_babysitter_skips_generation_gates_without_active_build(self):
        config = yaml.safe_load((REPO / "babysitter.yaml").read_text(encoding="utf-8"))
        ids = {"pre-gen-date-gate", "cta-mensagem-quality", "podcast-final-quality", "daily-release-quality"}
        checks = [check for check in config["checks"] if check["id"] in ids]
        self.assertEqual(len(checks), 4)
        for check in checks:
            self.assertIn("SKIP_NO_ACTIVE_BUILD", check["command"])
            self.assertNotIn("|| true", check["command"])

    def test_critical_checks_cannot_be_suppressed(self):
        source = ENGINE.read_text(encoding="utf-8")
        self.assertIn('if check.get("suppressed") and not critical:', source)
        self.assertIn('r.get("ok") and not r.get("skipped")', source)

    def test_deploy_executes_both_quality_gates_before_copying_audio(self):
        deploy = (REPO / "deploy_d5n_site.sh").read_text(encoding="utf-8")

        technical_gate = deploy.find("d5n-podcast-quality-gate.py")
        daily_gate = deploy.find("d5n_daily_release_gate.py")
        copy_position = deploy.find('cp "$LATEST_MP3" "$DEST"')
        self.assertGreaterEqual(technical_gate, 0)
        self.assertGreaterEqual(daily_gate, 0)
        self.assertGreater(copy_position, technical_gate)
        self.assertGreater(copy_position, daily_gate)
        self.assertIn('/root/.hermes/logs/d5n-deploy', deploy)
        self.assertNotIn('LOG="/tmp/deploy-d5n-', deploy)

    def test_critical_counter_check_does_not_force_success(self):
        config = yaml.safe_load((REPO / "babysitter.yaml").read_text(encoding="utf-8"))
        check = next(item for item in config["checks"] if item["id"] == "counter-integrity")
        self.assertNotIn("|| true", check["command"])
        self.assertNotIn("exit 0", check["command"])

    def test_audio_validator_ignores_other_programs_and_known_missing_history(self):
        source = Path("/root/.hermes/scripts/babysitter-engine/validators/d5n-audio-check.py").read_text(encoding="utf-8")
        self.assertIn('f.startswith("d5n-ep")', source)
        self.assertIn('if h.get("exists", False)', source)

    def test_babysitter_metrics_use_only_d5n_audio_and_four_pillars(self):
        source = (REPO / "scripts/d5n-babysitter.py").read_text(encoding="utf-8")
        self.assertIn('re.fullmatch(r"d5n-ep\\d{3}-\\d{4}-\\d{2}-\\d{2}\\.mp3", f)', source)
        self.assertIn("pilares_esperados = 4", source)
        self.assertIn('["Global", "Brasil", "Tech", "Economia"]', source)
        self.assertIn("if not report_only:\n        save_daily_score", source)

    def test_babysitter_daily_release_check_is_critical(self):
        config = (REPO / "babysitter.yaml").read_text(encoding="utf-8")
        marker = "id: daily-release-quality"
        marker_position = config.find(marker)

        self.assertGreaterEqual(marker_position, 0)
        block = config[max(0, marker_position - 250):marker_position + 250]
        self.assertIn("critical: true", block)
        self.assertIn("d5n_daily_release_gate.py", block)

    def test_deploy_requires_a_daily_episode_including_sunday(self):
        deploy = (REPO / "deploy_d5n_site.sh").read_text(encoding="utf-8")
        self.assertNotIn("IS_SUNDAY", deploy)
        self.assertNotIn("Domingo: manutenção", deploy)
        self.assertIn('block "Nenhum MP3 válido para hoje', deploy)
        self.assertNotIn("usando fallback de source.md", deploy)

    def test_deploy_stages_only_release_files_and_writes_receipt(self):
        deploy = (REPO / "deploy_d5n_site.sh").read_text(encoding="utf-8")
        self.assertNotIn("git add .", deploy)
        self.assertIn('git add -- "$DEST"', deploy)
        self.assertIn("published-${DATE}.json", deploy)
        self.assertIn("d5n_release_status.py", deploy)

    def test_cron_prompt_has_bounded_correction_loop_and_deploy(self):
        prompt = (REPO / "config" / "d5n-podcast-cron-prompt.txt").read_text(encoding="utf-8")
        self.assertIn("MAX_ATTEMPTS=4", prompt)
        self.assertIn("PARA CADA tentativa de 1 até MAX_ATTEMPTS", prompt)
        self.assertIn("d5n_release_status.py", prompt)
        self.assertIn("bash deploy_d5n_site.sh", prompt)
        self.assertIn("python3 /root/.hermes/scripts/d5n-mensagem-validate.py", prompt)
        self.assertNotIn("validate-cta-mensagem.py", prompt)
        self.assertIn("nunca altere, desative ou contorne um gate", prompt.lower())
        self.assertIn("somente o artefato que causou a falha", prompt.lower())
        self.assertIn("não repita a arquitetura", prompt.lower())
        self.assertIn("gancho", prompt.lower())


if __name__ == "__main__":
    unittest.main()
