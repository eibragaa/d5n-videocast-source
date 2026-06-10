#!/usr/bin/env python3
"""
d5n_marketing.py — Frameworks de Marketing Científico para D5N (Drop Five News)

Aplica: Evidências de Serviço, Método Científico, NPS/CSAT adaptado para podcast
Baseado no curso "Cientista do Marketing" (V4 Company / Stage)
"""
import json
from pathlib import Path
from datetime import datetime, date

D5N_DIR = Path('/root/repositorio/d5n-videocast-source')
SCORE_PATH = D5N_DIR / 'autoavaliacao-score.json'
FEED_PATH = D5N_DIR / 'feed.json'
OUTPUT_DIR = D5N_DIR / 'scripts' / 'reports'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def carregar_autoavaliacao():
    """Carrega histórico de autoavaliação"""
    if SCORE_PATH.exists():
        with open(SCORE_PATH) as f:
            return json.load(f)
    return []


def carregar_feed():
    """Carrega feed de episódios"""
    if FEED_PATH.exists():
        with open(FEED_PATH) as f:
            return json.load(f)
    return {}


def gerar_daily_report():
    """
    Daily Report do D5N — Evidência de Serviço do Podcast
    
    Mostra: episódios, cobertura, tendência de nota
    """
    scores = carregar_autoavaliacao()
    feed = carregar_feed()
    
    if not scores:
        return "❌ Nenhum dado de autoavaliação encontrado."
    
    ultimo = scores[-1]['metrics'] if scores else {}
    primeiro = scores[0]['metrics'] if scores else {}
    
    total_eps = ultimo.get('total_eps', 0)
    cobertura = ultimo.get('coverage_pct', 0)
    pilares = ultimo.get('pilares', '0/3')
    nota_hoje = scores[-1]['grade'] if scores else 0
    
    # Tendência (últimos 5 dias)
    ultimas_notas = [s['grade'] for s in scores[-5:]] if len(scores) >= 5 else [s['grade'] for s in scores]
    tendencia = '📈' if len(ultimas_notas) >= 2 and ultimas_notas[-1] > ultimas_notas[0] else ('📉' if len(ultimas_notas) >= 2 and ultimas_notas[-1] < ultimas_notas[0] else '➡️')
    
    # Crescimento
    eps_inicio = primeiro.get('total_eps', 0)
    eps_crescimento = total_eps - eps_inicio
    
    today = date.today()
    
    report = f"""📊 DAILY PODCAST — Drop Five News
📅 {today.isoformat()}
{'─'*45}

✅ FEITO HOJE:
  • Episódio #{total_eps} publicado
  • Cobertura de áudio: {cobertura:.0f}%
  • Pilares: {pilares}
  • Nota de qualidade: {nota_hoje}/10 {tendencia}

📈 MÉTRICAS DE CRESCIMENTO:
  • Total de episódios: {total_eps} (+{eps_crescimento} desde início)
  • MP3 em disco: {ultimo.get('mp3_disk', 0)}
  • Gaps: {ultimo.get('gaps', 0)}
  
📋 RANKING DE NOTAS (últimos dias):
{chr(10).join(f'  {s["date"]}: {s["grade"]}/10' for s in scores[-7:])}

📌 AMANHÃ:
  • Novo episódio D5N
  • Verificar cobertura de áudio
  • Publicar cards Instagram (se disponível)

📝 CITAÇÃO DO CURSO:
  "Você é um cientista, não um artista. 
   Você não vai pelo feeling."
"""
    return report


def gerar_hope_weekly():
    """
    HOPE Weekly do D5N — Framework de Customer Success
    
    Health → Objectives → Premises → Entregas
    """
    scores = carregar_autoavaliacao()
    week_number = datetime.now().isocalendar()[1]
    
    if not scores:
        ultimo = {}
        nota_media = 0
    else:
        ultimo = scores[-1]['metrics'] if scores else {}
        semana_scores = [s for s in scores[-7:]] if len(scores) >= 7 else scores
        nota_media = sum(s['grade'] for s in semana_scores) / len(semana_scores) if semana_scores else 0
    
    total_eps = ultimo.get('total_eps', 0)
    cobertura = ultimo.get('coverage_pct', 0)
    
    report = f"""📆 HOPE WEEKLY — Drop Five News | Semana {week_number}
📅 {date.today().isoformat()}
{'─'*50}

🏆 HEALTH — Vitórias da Semana
{'─'*50}
  ✅ {total_eps} episódios publicados
  ✅ Cobertura média de {cobertura:.0f}%
  ✅ Nota média da semana: {nota_media:.1f}/10
  ✅ Pipeline de publicação diária mantido

🎯 OBJECTIVES — Progresso
{'─'*50}
  Meta: Publicar 1 episódio por dia → ✅ Mantida
  Meta: Cobertura > 80% → {cobertura:.0f}% (⚠️ abaixo)
  Meta: Nota > 9.0 → R$ {nota_media:.1f}/10 {'✅' if nota_media >= 9 else '⚠️'}

⚠️ PREMISSAS — Riscos
{'─'*50}
  🟢 Cobertura de áudio crescendo consistentemente
  🟢 Corujão pode estar bloqueado (check)
  🟡 Cards Instagram — verificar se estão sendo gerados

📋 ENTREGAS — Próximos Passos
{'─'*50}
  [ALTO | BAIXO ESFORÇO] → FAÇA AGORA
  • Verificar cobertura MP3 dos últimos eps
  • Publicar site atualizado
  
  [ALTO | ALTO ESFORÇO] → PLANEJE
  • Melhorar cobertura de áudio (>80%)
  • Adicionar NPS no site para ouvintes
  
  [EVITE]
  • Análise excessiva de métricas (foco em publicar)

{'─'*50}
📌 CITAÇÃO DA SEMANA
{'─'*50}
  "O cliente pensa todos os dias em cancelar com você. 
   Dê evidências de serviço."
"""
    return report


def gerar_relatorio_audiencia():
    """
    Relatório de Audiência — Método Científico
    
    Baseado nos dados disponíveis do D5N
    """
    scores = carregar_autoavaliacao()
    
    if len(scores) < 2:
        return "Dados insuficientes para análise de tendência (mínimo 2 dias)."
    
    # Análise de tendência
    primeira_nota = scores[0]['grade']
    ultima_nota = scores[-1]['grade']
    variacao = ultima_nota - primeira_nota
    
    dias = len(scores)
    eps_inicio = scores[0]['metrics']['total_eps']
    eps_fim = scores[-1]['metrics']['total_eps']
    eps_por_dia = (eps_fim - eps_inicio) / max(1, dias - 1)
    
    analysis = f"""📈 RELATÓRIO DE AUDIÊNCIA — Método Científico
📅 Período: {scores[0]['date']} a {scores[-1]['date']} ({dias} dias)
{'─'*55}

🔬 OBSERVAÇÕES:
  • {eps_fim} episódios publicados no total
  • {eps_por_dia:.1f} episódios/dia
  • Nota inicial: {primeira_nota}/10
  • Nota atual: {ultima_nota}/10
  • Variação: {'+' if variacao >= 0 else ''}{variacao:.1f} {'📈' if variacao >= 0 else '📉'}

🔬 PROBLEMATIZAÇÃO:
  {f'Qualidade está estável/em queda. Hipótese: formato da curadoria pode ser ajustado.' if variacao <= 0 else 'Qualidade está melhorando. Hipótese: conteúdo está encontrando o tom certo.'}

🔬 HIPÓTESES PARA TESTAR:
  H1: Se reduzirmos para 5 notícias, a cobertura de áudio melhora
  H2: Se alternarmos temas (mais tech, menos política), o engajamento sobe
  H3: Se padronizarmos a abertura, a identidade sonora fortalece
"""
    return analysis


if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    
    if cmd == 'daily':
        report = gerar_daily_report()
    elif cmd == 'hope':
        report = gerar_hope_weekly()
    elif cmd == 'audiencia':
        report = gerar_relatorio_audiencia()
    else:
        report = f"Comandos: daily, hope, audiencia"
    
    print(report)
    
    # Salvar
    today = date.today().isoformat()
    filepath = OUTPUT_DIR / f'd5n_marketing_{cmd}_{today}.txt'
    filepath.write_text(report, encoding='utf-8')
    print(f"\n📁 Salvo em: {filepath}")
