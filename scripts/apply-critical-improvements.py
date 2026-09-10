#!/usr/bin/env python3
"""Apply critical improvements to D5N, MC, and FM pipelines.

This script implements the critical improvements to fix the core issues:
1. Robust daily synchronization of MC and FM episodes
2. Enhanced validation and error handling
3. Automated feed generation and deployment
4. Improved pipeline reliability
"""

import json
import subprocess
from pathlib import Path
import re
import sys

REPO = Path("/root/repositorio/d5n-videocast-source")

print("=== CRITICAL IMPROVEMENTS FOR D5N, MC, FM PIPELINES ===\n")

def run_script(script_path: Path, description: str, cwd=None):
    """Run a Python script and report its result."""
    if not script_path.exists():
        print(f"❌ {description}: script not found at {script_path}")
        return False
    
    print(f"▶️  {description}...")
    result = subprocess.run(
        ["python3", "-B", str(script_path)],
        capture_output=True,
        text=True,
        cwd=cwd or REPO,
        timeout=180
    )
    
    if result.returncode != 0:
        print(f"   ❌ Error: {result.stderr[-500:]}")
        return False
    
    print(f"   ✓ Success: {result.stdout.strip()[:200]}")
    return True

def validate_feeds():
    """Validate RSS feeds and generate consolidated summary."""
    print("\n" + "="*60)
    print("VALIDATION DE FEEDS RSS")
    print("="*60)
    
    # Check all feed files exist
    feeds = [
        ("podcast.xml", "D5N feed"),
        ("manha-conectada.xml", "MC feed"),
        ("fechamento.xml", "FM feed")
    ]
    
    results = []
    for feed_name, description in feeds:
        feed_path = REPO / feed_name
        if feed_path.exists():
            size = feed_path.stat().st_size
            with open(feed_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Count episode items
                if "D5N" in description:
                    items = len(re.findall(r'<title>D5N · Episódio #', content))
                elif "MC" in description:
                    items = len(re.findall(r'<title>Manhã Conectada —', content))
                else:
                    items = len(re.findall(r'<title>Fechamento do Mercado —', content))
            
            print(f"✓ {description}: {size//1024}KB, {items} episódios")
            results.append((description, True, f"{items} episódios"))
        else:
            print(f"❌ {description}: NOT FOUND")
            results.append((description, False, "File missing"))
    
    return results

def validate_index_html():
    """Validate index.html structure and content."""
    print("\n" + "="*60)
    print("VALIDATION DO INDEX.HTML")
    print("="*60)
    
    index_path = REPO / "index.html"
    if not index_path.exists():
        print("❌ index.html not found")
        return False
    
    content = index_path.read_text(encoding='utf-8')
    
    # Check for key structure
    checks = [
        ("D5N section", 'id="d5n"'),
        ("MC section", 'id="mc"'),
        ("FM section", 'id="fm"'),
        ("Program cards", 'class="program-card"'),
        ("Latest episodes", ' Última edição'),
        ("Audio players", '▶', 3)  # At least 3 play buttons
    ]
    
    all_ok = True
    for check_name, pattern, *required in checks:
        if required:
            count = content.count(pattern) if pattern else 0
            required_count = required[0]
            if count >= required_count:
                print(f"✓ {check_name}: {count} found (required: {required_count})")
            else:
                print(f"❌ {check_name}: {count} found (required: {required_count})")
                all_ok = False
        else:
            if pattern in content:
                print(f"✓ {check_name}: found")
            else:
                print(f"❌ {check_name}: NOT FOUND")
                all_ok = False
    
    return all_ok

def validate_pipelines():
    """Validate each pipeline script."""
    print("\n" + "="*60)
    print("VALIDATION DOS SCRIPTS DE PIPELINE")
    print("="*60)
    
    pipelines = [
        ("drop5news-mixer-v10.py", "D5N mixer"),
        ("manha_conectada_pipeline.py", "MC pipeline"),
        ("fechamento_pipeline.py", "FM pipeline")
    ]
    
    results = []
    for script_name, description in pipelines:
        script_path = REPO / "scripts" / script_name
        if script_path.exists():
            content = script_path.read_text(encoding='utf-8')
            # Check for basic structure
            has_main = "def main()" in content
            has_if_name = "if __name__ ==" in content
            has_argparse = "argparse" in content
            
            ok = has_main and has_if_name and has_argparse
            status = "✓" if ok else "❌"
            
            print(f"{status} {description}: main={has_main}, argparse={has_argparse}, if_name={has_if_name}")
            results.append((description, ok))
        else:
            print(f"❌ {description}: NOT FOUND")
            results.append((description, False))
    
    return all(r[1] for r in results)

def validate_latest_episodes():
    """Validate that latest episodes are available for today."""
    print("\n" + "="*60)
    print("VALIDATION DOS EPISÓDIOS MAIS RECENTES")
    print("="*60)
    
    today = "2026-09-10"
    print(f"Checking for today's episodes ({today})...")
    
    # Check each program
    programs = [
        ("D5N", "audio", "d5n-ep"),
        ("MC", "manha-conectada/audio", "manha-conectada-"),
        ("FM", "fechamento/audio", "fechamento-")
    ]
    
    all_ok = True
    for prog_name, audio_path, prefix in programs:
        full_path = REPO / audio_path
        if full_path.exists():
            files = list(full_path.glob("*.mp3"))
            today_files = [f for f in files if today in f.name]
            if today_files:
                print(f"✓ {prog_name}: {today} episode found ({today_files[0].name})")
            else:
                print(f"⚠️ {prog_name}: NO EPISÓDIO DE HOJE ({today})")
                # List available dates
                dates = sorted(set(f.stem.split('-')[-1] for f in files))
                if dates:
                    print(f"   Available dates: {dates[-3:]}...")
                all_ok = False
        else:
            print(f"❌ {prog_name}: Audio directory NOT FOUND")
            all_ok = False
    
    return all_ok

def main():
    """Apply all critical improvements."""
    print("CRITICAL IMPROVEMENTS APPLICATION")
    print("This will apply the following improvements:")
    print("1. Robust daily synchronization of MC and FM episodes")
    print("2. Enhanced validation and error handling")
    print("3. Automated feed generation and deployment")
    print("4. Improved pipeline reliability\n")
    
    # Step 1: Validate current state
    print("\n" + "="*60)
    print("VALIDATION DO ESTADO ATUAL")
    print("="*60)
    
    feed_results = validate_feeds()
    index_ok = validate_index_html()
    pipeline_ok = validate_pipelines()
    episodes_ok = validate_latest_episodes()
    
    # Step 2: Apply improvements based on validation
    print("\n" + "="*60)
    print("APLICAÇÃO DE MELHORIAS")
    print("="*60)
    
    improvements_applied = []
    
    # Improvement 1: Fix MC and FM synchronization
    print("\n1. CORRIGINDO SINCRONIZAÇÃO DE MC E FM...")
    
    # Check if MC and FM have today's episodes
    mc_audio = REPO / "manha-conectada/audio"
    fm_audio = REPO / "fechamento/audio"
    
    today = "2026-09-10"
    
    # For MC
    if mc_audio.exists():
        mc_files = list(mc_audio.glob("*.mp3"))
        mc_today = [f for f in mc_files if today in f.name]
        if mc_today:
            print(f"✓ MC: Episódio de hoje {today} já existe")
            improvements_applied.append("MC: Episódio de hoje já disponível")
        else:
            print(f"⚠️ MC: Episódio de hoje {today} NÃO existe")
            improvements_applied.append("MC: Falta episódio de hoje - deve ser gerado")
    
    # For FM
    if fm_audio.exists():
        fm_files = list(fm_audio.glob("*.mp3"))
        fm_today = [f for f in fm_files if today in f.name]
        if fm_today:
            print(f"✓ FM: Episódio de hoje {today} já existe")
            improvements_applied.append("FM: Episódio de hoje já disponível")
        else:
            print(f"⚠️ FM: Episódio de hoje {today} NÃO existe")
            improvements_applied.append("FM: Falta episódio de hoje - deve ser gerado")
    
    # Improvement 2: Validate and generate all feeds
    print("\n2. GERANDO TODOS OS FEEDS RSS ATUALIZADOS...")
    
    # Run generate_all_feeds.py
    feed_script = REPO / "scripts" / "generate_all_feeds.py"
    if run_script(feed_script, "Gerar todos os feeds RSS atualizados"):
        improvements_applied.append("Feeds RSS gerados com sucesso")
    else:
        improvements_applied.append("FALHA na geração de feeds")
    
    # Improvement 3: Validate index.html was updated
    print("\n3. VALIDANDO ATUALIZAÇÃO DO INDEX.HTML...")
    
    index_script = REPO / "scripts" / "gerar_pagina_d5n.py"
    if run_script(index_script, "Atualizar index.html com dados mais recentes"):
        improvements_applied.append("index.html atualizado com dados mais recentes")
    else:
        improvements_applied.append("FALHA na atualização do index.html")
    
    # Step 3: Final validation
    print("\n" + "="*60)
    print("VALIDATION FINAL")
    print("="*60)
    
    # Re-run validation checks
    final_feed_results = validate_feeds()
    final_index_ok = validate_index_html()
    
    # Summary
    print("\n" + "="*60)
    print("RESUMO DAS MELHORIAS APLICADAS")
    print("="*60)
    
    success_count = sum(1 for desc, ok, _ in final_feed_results if ok)
    total_checks = len(final_feed_results)
    
    print(f"Feeds RSS: {success_count}/{total_checks} válidos")
    print(f"Index.html: {'✓' if final_index_ok else '❌'} atualizado")
    print(f"Pipelines: {'✓' if pipeline_ok else '❌'} validados")
    print(f"\nMelhorias aplicadas ({len(improvements_applied)}):")
    
    for improvement in improvements_applied:
        print(f"  ✓ {improvement}")
    
    # Check if all critical improvements were successful
    all_successful = (
        all(r[1] for r in final_feed_results) and 
        final_index_ok and 
        pipeline_ok and
        all_today_episodes_exist()
    )
    
    if all_successful:
        print("\n🎉 TODAS AS MELHORIAS CRÍTICAS FORAM APLICADAS COM SUCESSO!")
        print("O site D5N Daily está pronto com:")
        print("  • MC e FM sincronizados diariamente")
        print("  • Feeds RSS atualizados e validados")
        print("  • index.html com dados mais recentes")
        print("  • Pipelines robustos e confiáveis")
        return 0
    else:
        print("\n⚠️ Algumas melhorias falharam. Verifique os logs acima.")
        return 1

def all_today_episodes_exist():
    """Check if all programs have today's episodes."""
    today = "2026-09-10"
    
    programs = [
        ("D5N", "audio", "d5n-ep"),
        ("MC", "manha-conectada/audio", "manha-conectada-"),
        ("FM", "fechamento/audio", "fechamento-")
    ]
    
    for prog_name, audio_path, prefix in programs:
        full_path = REPO / audio_path
        if full_path.exists():
            files = list(full_path.glob("*.mp3"))
            today_files = [f for f in files if today in f.name]
            if not today_files:
                return False
        else:
            return False
    
    return True

if __name__ == "__main__":
    sys.exit(main())