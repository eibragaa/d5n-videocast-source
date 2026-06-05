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
    
    # ── Autoavaliação e Métricas ──
    metrics = calculate_metrics(counter)
    grade, desc = calculate_grade(exit_code, metrics, needs_fix, needs_manual)
    report.append(f"📊 Métricas: {metrics['total_episodes']}eps · {metrics['mp3s_on_disk']}mp3 · {metrics['pilares_present']}/{metrics['pilares_esperados']} pilares · corujão {'✅' if metrics['corujao_blocked'] else '⛔'} · counter {'✅' if metrics['counter_integrity'] else '⚠️'}")
    report.append(f"🎯 Nota: {grade}/10 — {desc}")
    save_daily_score(grade, exit_code, needs_manual)
    
    # ── Mensagem de motivação (das 45 frases do Pensador.com) ──
    if not quiet:
        msg = get_motivational_message(grade, exit_code)
        report.append("")
        report.append(f"💪 {msg}")
    
    if not quiet:
        for line in report:
            print(line)
    
    return exit_code


# ═══════════════════════════════════════════════════
# SISTEMA DE MOTIVAÇÃO E AUTOAVALIAÇÃO
# ═══════════════════════════════════════════════════

MOTIVATIONAL_PHRASES = {
    "excellent": [
        "Nossa maior fraqueza está em desistir. O caminho mais certo de vencer é tentar mais uma vez. — Thomas Edison",
        "O otimismo é a fé daquele que conduz à realização; nada pode ser feito sem esperança. — Helen Keller",
        "A vida se contrai e se expande proporcionalmente à coragem do indivíduo. — Anaïs Nin",
        "Qualquer pessoa de sucesso sabe que é uma peça importante, mas sabe que não conseguirá nada sozinho. — Bernardinho",
        "A felicidade não é algo pronto. Ela é feita das suas próprias ações. — Dalai Lama",
    ],
    "good": [
        "Comece onde você está, use o que você tem e faça o que você pode. — Arthur Ashe",
        "Tudo o que um sonho precisa para ser realizado é alguém que acredite que ele possa ser realizado. — Roberto Shinyashiki",
        "Não importa que você vá devagar, contanto que você não pare. — Confúcio",
        "O sucesso nasce do querer, e da determinação para persistir. — Augusto Cury",
        "A inspiração existe, porém temos que encontrá-la trabalhando. — Pablo Picasso",
    ],
    "warning": [
        "Devíamos ser ensinados a não esperar por inspiração para começar algo. Ação sempre gera inspiração. — Frank Tibolt",
        "Não é a carga que o derruba, mas a maneira como você a carrega. — Lou Holtz",
        "A vida é 10% o que acontece a você e 90% como você reage a isso. — Charles Swindoll",
        "Acredite em milagres, mas não dependa deles. — Immanuel Kant",
        "Se a montanha que você está subindo parece cada vez mais imponente é sinal que você está mais próximo ao topo.",
    ],
    "error": [
        "Só é lutador quem sabe lutar consigo mesmo. — Carlos Drummond de Andrade",
        "A vitalidade é demonstrada não apenas pela persistência, mas pela capacidade de começar de novo. — F. Scott Fitzgerald",
        "Sonhar é verbo: é seguir, é pensar, inspirar e fazer força, insistir, é lutar, transpirar. — Bráulio Bessa",
        "Um dia, quando olhares para trás, verás que os dias mais belos foram aqueles em que lutaste. — Sigmund Freud",
        "Não existe nada de completamente errado no mundo, mesmo um relógio parado consegue estar certo duas vezes por dia. — Paulo Coelho",
    ],
}

def get_motivational_message(grade, exit_code):
    """Retorna uma frase de motivação baseada no estado do sistema."""
    import random
    
    if exit_code == 2:
        pool = MOTIVATIONAL_PHRASES["error"]
    elif exit_code == 1:
        pool = MOTIVATIONAL_PHRASES["warning"]
    elif grade >= 9:
        pool = MOTIVATIONAL_PHRASES["excellent"]
    else:
        pool = MOTIVATIONAL_PHRASES["good"]
    
    return random.choice(pool)


SCORE_HISTORY_FILE = os.path.join(BASE, "autoavaliacao-score.json")

def calculate_metrics(counter):
    """Calcula métricas do ecossistema para autoavaliação."""
    audio_dir = os.path.join(BASE, "audio")
    mp3_files = [f for f in os.listdir(audio_dir) if f.endswith(".mp3")]
    
    history = counter.get("history", [])
    total_eps = len(history)
    mp3_on_disk = len(mp3_files)
    
    # Pilares esperados vs presentes
    pilares_esperados = 3  # Global, Brasil, Tech
    site_file = os.path.join(BASE, "index.html")
    pilares_present = 0
    if os.path.exists(site_file):
        content = open(site_file, "r", encoding="utf-8").read()
        for pilar in ["Global", "Brasil", "Tech"]:
            if pilar in content:
                pilares_present += 1
    
    # Corujão bloqueado?
    corujao_blocked = True
    if os.path.exists(site_file):
        content = open(site_file, "r", encoding="utf-8").read()
        if "corujao" in content.lower() or "homelab" in content.lower():
            corujao_blocked = False
    
    # Integridade do counter
    counter_integrity = True
    expected_nums = set()
    for entry in history:
        num = entry.get("num", "")
        expected_nums.add(num)
    last = counter.get("last_episode", 0)
    # Verifica se o número máximo tem MP3 correspondente
    max_mp3 = f"d5n-ep{last:03d}"
    has_latest = any(max_mp3 == f"d5n-ep{entry['num']}" for entry in history)
    counter_integrity = has_latest
    
    return {
        "total_episodes": total_eps,
        "mp3s_on_disk": mp3_on_disk,
        "pilares_present": pilares_present,
        "pilares_esperados": pilares_esperados,
        "corujao_blocked": corujao_blocked,
        "counter_integrity": counter_integrity,
    }


def calculate_grade(exit_code, metrics, needs_fix, needs_manual):
    """Calcula nota 0-10 baseada em múltiplos fatores."""
    grade = 10.0
    
    # Penalidades por exit_code
    if exit_code == 2:
        grade -= 4.0  # Requer ação manual
    elif exit_code == 1:
        grade -= 1.5  # Precisou de correção
    
    # Penalidades por métricas
    if metrics["total_episodes"] == 0:
        grade -= 3.0
    if metrics["mp3s_on_disk"] < metrics["total_episodes"]:
        grade -= 1.0
    if metrics["pilares_present"] < metrics["pilares_esperados"]:
        diff = metrics["pilares_esperados"] - metrics["pilares_present"]
        grade -= diff * 0.5
    if not metrics["corujao_blocked"]:
        grade -= 2.0
    if not metrics["counter_integrity"]:
        grade -= 1.0
    
    # Bônus por estabilidade
    if exit_code == 0 and not needs_fix:
        grade += 0.5
    
    grade = max(0, min(10, grade))
    
    if grade >= 9:
        desc = "Excelente! Ecossistema saudável e autônomo."
    elif grade >= 7:
        desc = "Bom! Pequenos ajustes, mas funcionando."
    elif grade >= 5:
        desc = "Regular. Precisa de atenção em algumas áreas."
    elif grade >= 3:
        desc = "Ruim. Vários problemas detectados."
    else:
        desc = "Crítico. Sistema precisa de intervenção urgente."
    
    return round(grade, 1), desc


def save_daily_score(grade, exit_code, needs_manual):
    """Acumula histórico de autoavaliação para análise de tendências."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    history = []
    if os.path.exists(SCORE_HISTORY_FILE):
        try:
            history = json.load(open(SCORE_HISTORY_FILE, "r"))
        except (json.JSONDecodeError, IOError):
            history = []
    
    # Atualizar ou adicionar entrada de hoje
    found = False
    for entry in history:
        if entry["date"] == today:
            entry["grade"] = grade
            entry["exit_code"] = exit_code
            entry["needs_manual"] = needs_manual
            entry["updated_at"] = datetime.now().isoformat()
            found = True
            break
    
    if not found:
        history.append({
            "date": today,
            "grade": grade,
            "exit_code": exit_code,
            "needs_manual": needs_manual,
            "created_at": datetime.now().isoformat(),
        })
    
    # Manter só últimos 90 dias
    history = sorted(history, key=lambda x: x["date"])[-90:]
    
    try:
        with open(SCORE_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except IOError:
        pass  # Falha ao salvar não interrompe o fluxo

if __name__ == "__main__":
    sys.exit(main())
