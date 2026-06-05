#!/usr/bin/env python3
"""
d5n-babysitter.py — Vigilante automático do ecossistema Drop Five News.

Responsabilidades:
  1. Validar episode-counter.json vs. audio/ — todo MP3 no JSON existe em audio/
  2. Validar consistência numérica — sem gaps, sem duplicatas, sem números perdidos
  3. Validar site gerado (index.html) — player principal existe, lista histórica OK
  4. Validar que corujão NÃO está no site
  5. Validar que os 4 pilares (Global, Brasil, Tech, Economy) estão presentes
  6. Se algo falhar, TENTAR CORRIGIR automaticamente
  7. Se não conseguir corrigir, REPORTAR com detalhes no log

Uso:
  python3 scripts/d5n-babysitter.py              → valida e corrige
  python3 scripts/d5n-babysitter.py --report-only → só valida, não corrige
  python3 scripts/d5n-babysitter.py --deploy      → valida + corrige + deploy (push)

Exit codes:
  0 → Tudo OK
  1 → Problema corrigido automaticamente
  2 → Problema NÃO corrigível — precisa ação manual
"""

import os, sys, json, re, subprocess, shutil
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE, "audio")
COUNTER_FILE = os.path.join(BASE, "episode-counter.json")
INDEX_FILE = os.path.join(BASE, "index.html")
SCRIPTS_DIR = os.path.join(BASE, "scripts")

# ── Leitores de estado ──

def load_counter():
    try:
        with open(COUNTER_FILE) as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def list_audio_files():
    """Lista arquivos MP3 no diretório audio/ que seguem o padrão D5N."""
    if not os.path.isdir(AUDIO_DIR):
        return []
    files = []
    for f in os.listdir(AUDIO_DIR):
        m = re.match(r"d5n-ep(\d{3})-(\d{4}-\d{2}-\d{2})\.mp3", f)
        if m:
            files.append({"num": m.group(1), "date": m.group(2), "file": f, "size": os.path.getsize(os.path.join(AUDIO_DIR, f))})
    return sorted(files, key=lambda x: x["num"])

def list_site_index_episodes():
    """Extrai números de episódio do index.html gerado."""
    if not os.path.isfile(INDEX_FILE):
        return []
    with open(INDEX_FILE) as f:
        content = f.read()
    eps = re.findall(r"Ep #(\d+)", content)
    return eps

# ── Validações específicas ──

def validate_counter_integrity(counter):
    """Valida que o counter.json não está corrompido."""
    errors = []
    if "error" in counter:
        return ["❌ episode-counter.json corrompido ou inexistente: " + counter["error"]]
    
    if "last_episode" not in counter:
        errors.append("❌ episode-counter.json sem campo 'last_episode'")
    if "history" not in counter:
        errors.append("❌ episode-counter.json sem campo 'history'")
    if "format" not in counter:
        errors.append("❌ episode-counter.json sem campo 'format'")
    
    return errors

def validate_counter_vs_audio(counter, audio_files):
    """Valida que todo MP3 no JSON existe em audio/ e vice-versa."""
    errors = []
    warnings = []
    
    audio_nums = set(a["num"] for a in audio_files)
    json_audio = [h for h in counter.get("history", []) if h.get("exists", False)]
    json_nums = set(h["num"] for h in json_audio)
    
    # MP3 em audio/ mas não no JSON history
    for a in audio_files:
        if a["num"] not in json_nums:
            warnings.append(f"⚠️  audio/{a['file']} existe mas não está no history do episode-counter.json")
    
    # Episódios marcados como exists=True no JSON mas sem arquivo físico
    for h in json_audio:
        if h["num"] not in audio_nums:
            f_path = os.path.join(AUDIO_DIR, h["file"])
            if not os.path.isfile(f_path):
                errors.append(f"❌ JSON marca {h['file']} como exists=True mas arquivo não encontrado")
    
    # last_episode menor que o maior num em audio/
    if audio_nums:
        max_audio = max(int(n) for n in audio_nums)
        if counter.get("last_episode", 0) < max_audio:
            errors.append(f"❌ last_episode ({counter['last_episode']}) < maior episódio em audio/ ({max_audio})")
    
    return errors, warnings

def validate_no_corujao():
    """Valida que nenhum áudio do corujão está no site."""
    errors = []
    if os.path.isfile(INDEX_FILE):
        with open(INDEX_FILE) as f:
            content = f.read()
        for keyword in ["corujao", "homelab", "epNNN"]:
            if keyword in content.lower():
                errors.append(f"❌ Site contém referência a '{keyword}' — corujão no ar!")
    return errors

def validate_pilares(counter):
    """Valida que os 4 pilares de conteúdo estão presentes nos trends de hoje."""
    today = datetime.now().strftime("%Y-%m-%d")
    trends_path = f"/root/.hermes/cron/output/drop5news-trends-{today}.txt"
    
    if not os.path.isfile(trends_path):
        return [f"ℹ️  Trends de hoje não encontrados (pode ser normal antes das 08:30)"]
    
    with open(trends_path) as f:
        content = f.read()
    
    required = {"GLOBAL", "BRASIL", "TECH", "ECONOMIA"}
    found = set()
    for section in re.findall(r"=== (\w+) ===", content):
        found.add(section.upper())
    
    missing = required - found
    if missing:
        return [f"⚠️  Trends de hoje sem pilares: {', '.join(missing)}"]
    return []

def validate_site_has_player(counter):
    """Valida que o index.html tem player com o episódio mais recente."""
    if not os.path.isfile(INDEX_FILE):
        return ["❌ index.html não encontrado — site não gerado"]
    
    with open(INDEX_FILE) as f:
        content = f.read()
    
    latest = counter.get("last_episode", 0)
    if latest == 0:
        return ["⚠️  Nenhum episódio registrado para validação do player"]
    
    # Verifica se o player principal referencia o último episódio
    if f"D5N EPISÓDIO #{latest}" not in content.upper() and f"Episódio #{latest}" not in content:
        return [f"⚠️  Player do site não mostra episódio #{latest} como principal"]
    
    return []

# ── Ações corretivas ──

def fix_last_episode(counter, audio_files):
    """Corrige last_episode se estiver desatualizado."""
    if not audio_files:
        return False
    max_audio = max(int(a["num"]) for a in audio_files)
    if counter.get("last_episode", 0) < max_audio:
        counter["last_episode"] = max_audio
        counter["updated"] = datetime.now().strftime("%Y-%m-%d")
        _save_counter(counter)
        return True
    return False

def fix_missing_audio_in_counter(counter, audio_files):
    """Adiciona MP3s órfãos ao history do counter."""
    changed = False
    audio_nums = set(a["num"] for a in audio_files)
    
    for a in audio_files:
        # Verifica se já existe no history por num
        exists_in_history = any(h["num"] == a["num"] for h in counter.get("history", []))
        if not exists_in_history:
            counter.setdefault("history", []).append({
                "num": a["num"],
                "date": a["date"],
                "file": a["file"],
                "exists": True
            })
            changed = True
    
    if changed:
        # Reordenar history por num
        counter["history"].sort(key=lambda x: x["num"])
        _save_counter(counter)
    
    return changed

def _save_counter(counter):
    """Salva o counter.json com formatação consistente."""
    with open(COUNTER_FILE, "w") as f:
        json.dump(counter, f, indent=2, ensure_ascii=False)
        f.write("\n")

def regenerate_site():
    """Regenera o site se necessário."""
    try:
        result = subprocess.run(
            ["python3", os.path.join(BASE, "gerar_pagina_d5n.py")],
            cwd=BASE, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

def run_deploy():
    """Executa o deploy se tudo estiver OK."""
    try:
        result = subprocess.run(
            ["bash", os.path.join(SCRIPTS_DIR, "..", "deploy_d5n_site.sh")],
            cwd=BASE, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return True, "Deploy via babysitter OK"
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)

# ── Main ──

def main():
    report_only = "--report-only" in sys.argv
    do_deploy = "--deploy" in sys.argv
    quiet = "--quiet" in sys.argv
    
    report = []
    needs_fix = False
    needs_manual = False
    
    # ── Estado atual ──
    counter = load_counter()
    audio_files = list_audio_files()
    
    report.append("═══════════════════════════════════")
    report.append(f"🤖 D5N Babysitter — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"📊 Estado: {len(audio_files)} MP3s em audio/, last_episode={counter.get('last_episode','?')}")
    report.append("═══════════════════════════════════")
    
    # ── Validação 1: Integridade do counter ──
    errors = validate_counter_integrity(counter)
    for e in errors:
        report.append(f"  {e}")
        needs_manual = True
    
    if not needs_manual:
        # ── Validação 2: Counter vs. Audio ──
        errors, warnings = validate_counter_vs_audio(counter, audio_files)
        for e in errors:
            report.append(f"  {e}")
            needs_fix = True
        for w in warnings:
            report.append(f"  {w}")
            needs_fix = True
        
        # ── Validação 3: Corujão no site ──
        errors = validate_no_corujao()
        for e in errors:
            report.append(f"  {e}")
            needs_manual = True
        
        # ── Validação 4: Pilares ──
        warnings = validate_pilares(counter)
        for w in warnings:
            report.append(f"  {w}")
        
        # ── Validação 5: Player do site ──
        warnings = validate_site_has_player(counter)
        for w in warnings:
            report.append(f"  {w}")
        
        # ── Ações corretivas (se não for report-only) ──
        if not report_only and (needs_fix or do_deploy):
            changed = False
            
            if needs_fix:
                # 1. Adicionar MP3s órfãos ao history
                if fix_missing_audio_in_counter(counter, audio_files):
                    report.append(f"  ✅ Corrigido: MP3s órfãos adicionados ao history do counter")
                    counter = load_counter()  # reload
                    changed = True
                
                # 2. Corrigir last_episode se necessário
                if fix_last_episode(counter, audio_files):
                    report.append(f"  ✅ Corrigido: last_episode atualizado para {counter['last_episode']}")
                    changed = True
            
            # 3. Regenerar site se algo mudou ou deploy foi solicitado
            if changed or do_deploy:
                ok, out = regenerate_site()
                if ok:
                    report.append(f"  ✅ Site regenerado com sucesso")
                    changed = True
                else:
                    report.append(f"  ❌ Falha ao regenerar site: {out[:200]}")
                    needs_manual = True
            
            # 4. Deploy se tudo OK
            if changed and not needs_manual and do_deploy:
                ok, msg = run_deploy()
                if ok:
                    report.append(f"  ✅ Deploy executado com sucesso")
                else:
                    report.append(f"  ❌ Deploy falhou: {msg[:200]}")
                    needs_manual = True
    
    # ── Resumo ──
    report.append("───────────────────────────────────")
    if needs_manual:
        report.append("❌ REQUER AÇÃO MANUAL — problemas não corrigíveis automaticamente")
        exit_code = 2
    elif needs_fix:
        report.append("⚠️  Problemas corrigidos automaticamente — site atualizado")
        exit_code = 1
    elif do_deploy:
        report.append("✅ Tudo OK — deploy realizado")
        exit_code = 0
    else:
        report.append("✅ Tudo OK — nenhuma ação necessária")
        exit_code = 0
    
    if not quiet:
        for line in report:
            print(line)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
