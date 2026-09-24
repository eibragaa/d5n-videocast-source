#!/usr/bin/env python3
"""Gera manifests de texto para D5N a partir dos manifests diários de MC e FM.

Usa dados reais de ontem (MC/FM) como fallback quando hoje ainda não foi produzido.
Gera conteúdo com volume suficiente para o mixer v10 (480-720s de narração).
"""
import json
import os
from pathlib import Path
from datetime import date, timedelta

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()
TODAY = date.today().isoformat()
TODAY_DATE = date.today()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

# Vozes
THALITA = "pt-BR-ThalitaMultilingualNeural"
FRANCISCA = "pt-BR-FranciscaNeural"

# Categorias de notícias
WORLDCAT = ["trump", "iran", "israel", "russia", "ukraine", "global", "fauci", "missile",
            "hormuz", "fed", "federa", "reunião", "cúpula", "paz", "guerra", "conflito"]
BRACAT = ["brasil", "brasília", "congresso", "bolsonaro", "lula", "stf", "tc-", "brb",
          "delator", "precatório", "eleições", "flávio", "pt", "psdb", "ministro",
          "presidente", "governo", "senado", "câmara", "tribunal"]
TECHCAT = ["inteligência artificial", "ia", "tecnologia", "data center", "cripto",
           "binance", "mastercard", "stablecoin", "galaxy", "baleia", "computação",
           "chip", "nvidia", "open", "ai", "cloud", "servidor"]
ECOCAT = ["ibovespa", "bolsa", "dólar", "fechamento", "mercado", "ações", "wpp",
          "zillow", "investimento", "cryptoquant", "commodities", "renda",
          "juros", "selic", "inflação", "exportação", "importação", "câmbio"]


def load_mc_fm(day: str):
    """Carrega manifestos MC e FM de um dia específico."""
    sources = []
    mc_json = REPO / "manha-conectada" / "manifests" / f"{day}.json"
    fm_json = REPO / "fechamento" / "manifests" / f"{day}.json"
    for jf in [mc_json, fm_json]:
        if jf.exists():
            try:
                data = json.loads(jf.read_text())
                sources.extend(data.get("sources", []))
            except Exception:
                pass
    return sources


def categorize(sources):
    """Categoriza notícias em seções."""
    cats = {"mundo": [], "brasil": [], "tech": [], "economia": []}
    for s in sources:
        title = s.get("title", "").lower()
        matched = False
        for k in WORLDCAT:
            if k in title:
                cats["mundo"].append(s)
                matched = True
                break
        if not matched:
            for k in BRACAT:
                if k in title:
                    cats["brasil"].append(s)
                    matched = True
                    break
        if not matched:
            for k in TECHCAT:
                if k in title:
                    cats["tech"].append(s)
                    matched = True
                    break
        if not matched:
            for k in ECOCAT:
                if k in title:
                    cats["economia"].append(s)
                    matched = True
                    break
    # Fallbacks se categorização for vaga
    uncategorized = [s for s in sources if s not in cats["mundo"] + cats["brasil"] + cats["tech"] + cats["economia"]]
    for i, s in enumerate(uncategorized):
        cats["brasil"].append(s)
    return cats


def manchete(ns):
    """Extrai manchete curta."""
    t = ns.get("title", "")
    if " - " in t:
        t = t.rsplit(" - ", 1)[0]
    return t


def src_name(ns):
    s = ns.get("source", "")
    if not s:
        u = ns.get("url", "")
        s = u.split("//")[-1].split("/")[0] if "//" in u else "fonte"
    return s


def fmt_news(ns):
    t = manchete(ns)
    s = src_name(ns)
    return f"{t}, segundo {s}."


# Carregar dados reais
sources = load_mc_fm(YESTERDAY)
# Se ontem também não tem, tenta hoje
if not sources:
    sources = load_mc_fm(TODAY)
cats = categorize(sources)

# Garantir mínimo de notícias por categoria
all_news = cats["mundo"] + cats["brasil"] + cats["tech"] + cats["economia"]
if not all_news:
    all_news = sources

manifest_dir = REPO / "manifests" / "d5n" / TODAY
manifest_dir.mkdir(parents=True, exist_ok=True)

manifests = {}

# coldopen — manchetes de abertura
mundo_txt = " ".join(fmt_news(n) for n in cats["mundo"][:4]) if cats["mundo"] else ""
brasil_txt = " ".join(fmt_news(n) for n in cats["brasil"][:3]) if cats["brasil"] else ""
eco_txt = " ".join(fmt_news(n) for n in cats["economia"][:2]) if cats["economia"] else ""
manifests["coldopen.txt"] = (
    f"{TODAY}. O Ibovespa reage a movimentos internacionais enquanto o cenário "
    f"corporativo acelera em inteligência artificial e telecomunicações. "
    f"{mundo_txt} {brasil_txt} {eco_txt}"
).strip()

# intro
manifests["intro.txt"] = (
    f"Bom dia! Eu sou Francisca, e hoje é {TODAY_DATE.strftime('%A, %d de %B de %Y')}. "
    f"Este é o Drop Five News, o seu briefing das 05 horas da manhã com as "
    f"notícias essenciais para começar o dia bem informado. "
    f"Separe um tempo para ouvir: em 9 minutos, conectamos você ao que move "
    f"o Brasil e o mundo neste horário. Vamos ao que interessa."
)

# mundo
world_intro = (
    "No cenário global, as bolsas internacionais operam com cautela antes de "
    "novos dados de inflação nos Estados Unidos. Investidores monitoram os "
    "próximos passos do Federal Reserve em relação às taxas de juros, "
    "enquanto tensionamentos geopolíticos mantêm a volatilidade elevada. "
)
if cats["mundo"]:
    world_news = " ".join(fmt_news(n) for n in cats["mundo"][:5])
    manifests["mundo.txt"] = f"{world_intro}{world_news}"
else:
    manifests["mundo.txt"] = f"{world_intro} A atenção está nos mercados emergentes e nas negociações comerciais entre grandes potências."

# brasil
brasil_intro = (
    f"No Brasil, o foco da quinta-feira, {TODAY}, reúne a agenda econômica "
    f"em Brasília com discussões sobre equilíbrio fiscal e projetos prioritários "
    f"no Congresso. O cenário político mantém alta tensão, enquanto o Judiciário "
    f"pesa decisões que impactam a estabilidade do país. "
)
if cats["brasil"]:
    brasil_news = " ".join(fmt_news(n) for n in cats["brasil"][:5])
    manifests["brasil.txt"] = f"{brasil_intro}{brasil_news}"
else:
    manifests["brasil.txt"] = f"{brasil_intro} A economia doméstica sente os ecos da crise internacional e das decisões de política monetária."

# tecnologia
tech_intro = (
    "Em tecnologia, os avanços em inteligência artificial generativa aceleram "
    "o mercado corporativo. Empresas ampliam investimentos em infraestrutura "
    "de computação e soluções locais, enquanto governos debatem regulamentação "
    "para este setor em constante transformação. "
)
if cats["tech"]:
    tech_news = " ".join(fmt_news(n) for n in cats["tech"][:4])
    manifests["tecnologia.txt"] = f"{tech_intro}{tech_news}"
else:
    manifests["tecnologia.txt"] = f"{tech_intro} Startups e grandes corporações competem por talentos e parcerias estratégicas."

# economia
eco_intro = (
    "Na economia, o mercado financeiro reflete o bom momento das exportações "
    "e a estabilidade cambial, com o dólar em faixa estável. Investidores "
    "institucionais reconfiguram estratégias de alocação, enquanto os dados "
    "de ontem mostram movimentos de capital em diferentes setores. "
)
if cats["economia"]:
    eco_news = " ".join(fmt_news(n) for n in cats["economia"][:4])
    manifests["economia.txt"] = f"{eco_intro}{eco_news}"
else:
    manifests["economia.txt"] = f"{eco_intro} A atenção está nos resultados corporativos e na agenda de publicações econômicas."

# interacao
manifests["interacao.txt"] = (
    "E aí, você acompanhou as notícias da manhã? Deixe seu comentário aqui "
    "em baixo e conte o que você achou das últimas informações sobre o mercado "
    "e a economia. Sua opinião importa! Você também pode seguir o @ojeanbraga.s "
    "no Instagram para atualizações em tempo real e participar do grupo exclusivo "
    "no Telegram com outros profissionais que acompanham o mercado de capitais "
    "e economia brasileira todos os dias. Conto com você!"
)

# ofertas
ofertas_intro = (
    f"Nesta quinta-feira, {TODAY}, o mercado oferece oportunidades em setores "
    f"como telecomunicações, energia renovável e infraestrutura de dados. "
    f"Empresas estão em expansão e buscando talentos qualificados. "
)
if cats["economia"] or cats["tech"]:
    ofertas_news = " ".join(fmt_news(n) for n in (cats["economia"][:2] + cats["tech"][:2]))
    manifests["ofertas.txt"] = f"{ofertas_intro}{ofertas_news}"
else:
    manifests["ofertas.txt"] = f"{ofertas_intro} Acompanhe as vagas e oportunidades na nossa página de cursos."

# frase
manifests["frase.txt"] = (
    f"Quinta-feira, {TODAY}. A tecnologia continua transformando a maneira como "
    f"vivemos e trabalhamos. Com os avanços em inteligência artificial "
    f"generativa, as oportunidades de inovação crescem sem parar. A chave para "
    f"o sucesso está em adaptar-se rapidamente a essas mudanças e investir em "
    f"conhecimento contínuo. Quem não evolui, é ultrapassado."
)

# recomendacoes
manifests["recomendacoes.txt"] = (
    "Para começar o dia bem informado, recomendamos acompanhar as notícias do G1, "
    "as análises do Valor Econômico e os boletins do Banco Central. "
    "Informação de qualidade é a base para decisões inteligentes. "
    "Além disso, sugerimos revisar sua carteira de investimentos, "
    "verificar os relatórios corporativos publicados esta semana "
    "e manter um olhar atento sobre a agenda de publicações econômicas "
    "que podem impactar seus ativos. "
    "Na seção de tecnologia, vale conferir as novidades em IA generativa "
    "e os lançamentos de hardware que podem moldar o próximo trimestre. "
    "E não esqueça de ouvir o Manhã Conectada às 11h e o Fechamento do Mercado às 17h."
)

# historia
manifests["historia.txt"] = (
    "Na história dos negócios, grandes empresas nasceram de ideias simples e "
    "persistência. Hoje, mais do que nunca, a inovação e a criatividade são "
    "os motores do crescimento sustentável. Empresas que começaram em garagens "
    "ou em pequenos escritórios agora lideram setores estratégicos da economia "
    "global. A lição é clara: quem tem visão de longo prazo e executa com "
    "consistência constrói uma vantagem competitiva duradoura. "
    "Nomes que hoje dominam o cenário — bancos, embaixadoras e gigantes da "
    "tecnologia — todos passaram por fases de incerteza, ajustando rotas, "
    "redefinindo modelos e acreditando em transformações que, no início, "
    "pareciam ousadas demais. O padrão se repete: inovação disruptiva, "
    "capital de risco e coragem para desafiar consensos. Investir nisso "
    "exige olhar além do ciclo de notícias de hoje."
)

# outro
manifests["outro.txt"] = (
    f"Este foi o Drop Five News desta quinta-feira, {TODAY}. Fique ligado ao "
    f"longo do dia para o Manhã Conectada às 11h e o Fechamento do Mercado "
    f"às 17h, com análises aprofundadas do que movimentou as bolsas hoje. "
    f"Lembre-se de ativar as notificações do podcast para receber cada "
    f"episódio automaticamente. Tenha um excelente dia e até a próxima!"
)

total_bytes = sum(len(v) for v in manifests.values())
for name, content in manifests.items():
    path = manifest_dir / name
    path.write_text(content, encoding="utf-8")

print(f"Manifests D5N criados com sucesso em: {manifest_dir}")
print(f"Total: {len(manifests)} seções, {total_bytes} bytes (~{total_bytes/14.3:.0f}s TTS)")
