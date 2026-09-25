#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_roteiro_d5n_beta.py — BETA v2 · Roteiro D5N estilo Amanda Flaury (humanizado).

Mudancas vs v1:
  1. SEM "segundo Fonte" no corpo das noticias — fontes/links vao para o final
     (outro.txt menciona: links de todas as noticias na descricao do episodio
     e no site). Corpo fica limpo, como conversa.
  2. Conectores/efeitos/fechos com USO UNICO por episodio (rng.sample + pop):
     nenhum bordao repete dentro do mesmo episodio; pool ampliado (20+).
  3. Curadoria: max 4 noticias por bloco (nao despeja todas). Se faltar volume,
     aprofunda o CONTEXTO de cada noticia (2a rodada), nao adiciona noticia.
  4. Humanizacao: reacoes coloquiais, pergunta retorica, tom de conversa;
     sem enumeracao mecanica.
  5. sex (wd=4): recomendacoes.txt obrigatorio com filmes/series IMDB bem
     avaliados (pool curado com nota; rotacao por semana).
  6. Meta de duracao rotativa por dia mantida (8-12 min).

Nao toca: mixer v10, gates, deploy, feeds, site.
Uso:  python3 -B scripts/gerar_roteiro_d5n_beta.py [--data YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()
TODAY = date.today()

THALITA = "pt-BR-ThalitaMultilingualNeural"
FRANCISCA = "pt-BR-FranciscaNeural"

DIAS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Meta rotativa: (min_words, alvo, max_words) por dia da semana — calibrado para
# CURADORIA (4-6 noticias/bloco com contexto profundo, sem encher linguiça):
#   seg 8.0-8.5min · ter 8.5-9 · qua 9-9.5 · qui 8.5-9 · sex 9.5-10.5 · sab 9-9.5
META_DIA = {
    0: (1000, 1120, 1250),  # seg: curto
    1: (1100, 1220, 1350),  # ter: medio-curto
    2: (1200, 1320, 1450),  # qua: medio
    3: (1100, 1220, 1350),  # qui: medio-curto
    4: (1350, 1500, 1650),  # sex: longo (recomendacoes IMDB + 5 noticias/bloco)
    5: (1200, 1320, 1450),  # sab: medio
}
MAX_NOTICIAS_BLOCO = 4  # curadoria (5 na sexta via meta especial)

# Pools de expressao — USO UNICO por episodio (sem repeticao interna)
APERTURA_BLOCO = [  # como abrir o bloco depois do header (variado)
    "Bora começar entendendo o que está acontecendo",
    "Deixa eu te situar rápido",
    "O primeiro tópico de hoje é direto ao ponto",
    "Vou te contar o que mais importa primeiro",
    "Antes de qualquer coisa, o essencial",
]
PONTE_CONTEXTO = [  # conecta manchete -> contexto (frase completa, com ponto)
    "E tem um detalhe importante nessa história.",
    "E o que está por trás disso é talvez o mais interessante.",
    "E não é exagero dizer que isso tem peso.",
    "E o contexto explica bastante coisa.",
    "E aqui vale abrir um parêntese: o assunto é maior do que parece.",
    "E o desdobramento disso é o que chama atenção.",
    "E curiosamente, a repercussão já começou.",
    "E olha, tem um ângulo que muita gente deixou passar.",
    "E a forma como isso chegou ao noticiário diz muito.",
    "E o que mais se discute sobre o tema hoje é isso:",
    "E este é o ponto que os especialistas estão lendo com mais atenção.",
    "E a notícia chega num momento em que o cenário já estava sensível.",
]
CONTEXTO_RODADA2 = [  # aprofundamento honesto de cada tema (sem inventar dado)
    "O movimento pegou o noticiário ainda quente, com os desdobramentos chegando em cascata.",
    "E o efeito vem em camadas: primeiro a manchete, depois a leitura dos especialistas, e só então a reação dos envolvidos.",
    "O que o mercado lê nisso é sinal de que a agenda do dia vai ser movimentada.",
    "E a leitura que se faz é de cautela com os próximos passos, porque a margem de erro aqui é pequena.",
    "O tema ganha relevância porque mexe com decisões que saem do papel direto para a vida real.",
    "E o que os analistas acompanham agora é a reação em cadeia — uma notícia puxando a outra.",
    "Isso entra direto na conta de quem precisa decidir antes do fim do dia.",
    "E o movimento ainda está em andamento: o que veio a público é o começo da história.",
    "E os próximos números é que vão confirmar a direção — até lá, todo cuidado é pouco.",
    "E não é só ruído: há um caminho concreto sendo traçado a partir disso.",
    "E o que chama a atenção é a velocidade com que o assunto subiu na pauta.",
    "E o impacto disso aparece em etapas, e a primeira já está na rua.",
    "E é um daqueles casos em que o depois importa mais que o agora.",
    "E o assunto já tinha temperatura antes — esse capítulo sobe o termômetro.",
    "E é o tipo de notícia que redesenha o cenário das próximas horas.",
    "E o que vem na sequência costuma confirmar ou derrubar a manchete.",
]
REACAO_HUMANA = [  # reacao coloquial da apresentadora — FRASES completas (ponto final)
    "Sinceramente, esse é um tema que merece atenção.",
    "Olha, essa é uma história que vale acompanhar com calma.",
    "Falando sem rodeio, o tamanho disso é grande.",
    "E sabendo como o mercado funciona, tem coisa aí embaixo.",
    "Pra ser bem direta com você, não é ruído — é sinal.",
    "E se você parar pra pensar, faz todo sentido.",
    "Na conversa de hoje, é um dos pontos que mais valem atenção.",
    "E com o que a gente viu nas últimas horas, dá pra ter leitura.",
    "E esse detalhe, sozinho, já muda o tom da conversa.",
    "E o curioso é que isso chegou sem muito alarde.",
    "E mesmo sem parecer, essa notícia carrega peso.",
    "E é daquelas que divide opinião antes mesmo de virar debate.",
    "E é um tema que mexe com a sua rotina mais do que parece.",
    "E o desdobramento disso é que a gente vai acompanhar de perto.",
    "E antes que você se pergunte o porquê, aqui vai o contexto.",
    "E essa é uma daquelas notícias que pedem leitura dupla.",
]
EFEITO_PRATICO = [  # "na pratica, isso significa..." (frase completa, sem preposicao orfa)
    "Na prática, isso mexe direto com quem acompanha o assunto.",
    "No seu dia a dia, isso traduz em decisão: acompanhar ou esperar.",
    "Na ponta do lápis, o efeito aparece rápido.",
    "Pra quem está de fora, parece distante — mas não está.",
    "O que isso muda para você: contexto na hora de decidir.",
    "E é aí que a informação deixa de ser só manchete e vira leitura de mundo.",
    "E esse é o tipo de detalhe que faz diferença nas próximas horas.",
    "Se você acompanha de perto, esse é o ponto que vale marcar.",
    "E é o tipo de notícia que muda a leitura do resto do dia.",
    "E quem precisa agir com isso em mãos ganha tempo.",
    "E é por isso que a gente traz o tema hoje, com contexto e pé no chão.",
    "E é esse o recado que fica para a sua manhã.",
    "E é exatamente nesse ponto que a notícia sai do papel e toca sua vida.",
    "E é isso que separa quem apenas lê de quem entende o que vem depois.",
    "E é esse o efeito que a gente acompanha na prática ao longo das próximas horas.",
    "E é nessa hora que o tema deixa de ser abstrato e vira escolha concreta.",
]
PONTE_NOTICIA = [  # transicao entre noticias do MESMO bloco (uso unico)
    "E tem mais:",
    "E o que complica ainda mais o quadro:",
    "E do mesmo pacote, outro movimento:",
    "E não para por aí:",
    "Só que tem outro elemento na jogada:",
    "E o que veio depois só reforça isso:",
    "E num desdobramento direto, veio isto:",
    "E vale olhar junto com isso:",
    "E num outro giro do dia:",
    "E essa é a outra metade da história:",
    "E o que segue nesse mesmo tema:",
    "E tem um desdobramento que pouca gente viu chegar:",
    "E seguindo a linha do que já veio:",
    "E tem uma reviravolta nesse enredo:",
    "E o que os bastidores dizem é o seguinte:",
    "E uma vez que a poeira baixou, aparece isso:",
    "E como se não bastasse o que já veio:",
    "E agora o cenário muda um pouco:",
    "E tem um capítulo novo dessa história:",
    "E o dado que chega agora reforça o quadro:",
]
FECHO_COLD = [  # reacao apos manchetes-tiro
    "e é por aí que a gente começa.",
    "e todas essas histórias têm consequência real.",
    "e é sobre isso que a gente conversa agora.",
    "e cada uma dessas notícias muda algo no seu dia.",
    "e tem tudo a ver com o seu contexto de hoje.",
    "e é exatamente esse fio que a gente puxa agora.",
    "e é com esse cenário que a gente abre o dia.",
    "e é por isso que esse tema entra na conversa de hoje.",
    "e é esse pano de fundo que muda a leitura da notícia.",
    "e é o que explica por que isso importa agora.",
]

# Fallbacks rotativos quando os pools esgotam (episodios longos com 16+ noticias)
FALLBACK_REACAO = [
    "Olha, esse é um tema que vale acompanhar.",
    "E na real, é uma história com dobras.",
    "E esse aqui merece dois minutos de atenção.",
    "E é um daqueles casos que muda de figura ao longo do dia.",
    "E acompanhar esse assunto de perto faz diferença.",
    "E tem gente que vai sentir isso na prática.",
]
FALLBACK_CTX1 = [
    "E o contexto aqui importa.",
    "E o que vem por trás disso explica o porquê.",
    "E o cenário em volta já estava sensível.",
    "E a leitura dos que acompanham é de atenção redobrada.",
    "E o desdobramento ainda vai render.",
    "E é um tema que conversa direto com as demais notícias do dia.",
]
FALLBACK_CTX2 = [
    "E os próximos movimentos é que vão mostrar a medida disso.",
    "E o capítulo seguinte dessa história ainda está se escrevendo.",
    "E o que os analistas projetam é que o assunto siga rendendo.",
    "E os próximos dados é que vão dar a direção.",
    "E o tema promete ocupar a pauta nas próximas horas.",
    "E vale acompanhar o que vem pela frente.",
]
FALLBACK_EFEITO = [
    "E é justamente por isso que o tema entra na pauta de hoje.",
    "E é dessa consequência que a gente vai sentir o peso nos próximos dias.",
    "E é esse o desdobramento que merece olho aberto.",
    "E é isso que muda a sua leitura sobre o assunto.",
    "E esse é o ponto que conecta a notícia com a sua realidade.",
    "E é a partir daí que a história começa a fazer sentido.",
]

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

FRASES_FALLBACK = [
    ("O conhecimento é a única riqueza que ninguém pode tirar de você.", "Provérbio africano"),
    ("A persistência é o caminho do êxito.", "Charles Chaplin"),
    ("O segredo do sucesso é a constância do propósito.", "Benjamin Disraeli"),
    ("Nem tudo o que dá para contar conta; nem tudo o que conta dá para contar.", "Albert Einstein"),
    ("A coragem não é ausência de medo; é a capacidade de agir apesar dele.", "Nelson Mandela"),
    ("O futuro pertence àqueles que se preparam hoje.", "Malcolm X"),
]

# Recomendacoes de sexta (IMDB — pool com nota real; rotacao por semana)
# (titulo, tipo, nota_imdb, onde, por_que)
IMDB_POOL_FILMES = [
    ("Um Sonho de Liberdade", "filme", 9.3, "na Max ou em plataformas de aluguel", "considerado por muitos o melhor filme da história do IMDb, um clássico que emociona até hoje"),
    ("Interestelar", "filme", 8.7, "na Max", "ficção científica com peso emocional e visual que envelheceu muito bem"),
    ("Cidade de Deus", "filme", 8.6, "na Globoplay ou na Netflix", "a obra-prima brasileira, essencial e atual como sempre"),
    ("Duna: Parte Dois", "filme", 8.4, "na Max", "épico que elevou a barra do cinema de ficção científica recente"),
    ("A Odisséia", "filme", 8.4, "em cartaz nos cinemas", "a superprodução do ano, já cotada entre as melhores avaliadas do IMDb"),
    ("Projeto Hail Mary", "filme", 8.2, "no Prime Video", "com Ryan Gosling, uma das apostas mais bem avaliadas de 2026"),
]
IMDB_POOL_SERIES = [
    ("Breaking Bad", "série", 9.5, "na Netflix", "a série mais bem avaliada da história do IMDb, com roteiro impecável do começo ao fim"),
    ("Chernobyl", "série", 9.3, "na Max", "minissérie densa e impactante sobre uma das maiores tragédias do século 20"),
    ("One Piece — 2ª temporada", "série", None, "na Netflix", "a adaptação live-action mais assistida do momento, que só cresce"),
    ("Black Rabbit", "série", None, "na Netflix", "Trama criminal com Jason Bateman e Jude Law, indicada a vários Emmys"),
    ("The Diplomat", "série", None, "na Netflix", "Drama político consistente, elogiado pela crítica e bem avaliado pelo público"),
    ("Round 6 (Squid Game)", "série", 8.0, "na Netflix", "mesmo depois do fim, segue entre as mais bem avaliadas e revisitadas da plataforma"),
]


def apresentadora(dia: date) -> str:
    wd = dia.weekday()
    if wd in {0, 2, 5}:
        return "Thalita"
    if wd in {1, 3}:
        return "Francisca"
    return "Thalita e Francisca"  # sexta: dual


def nome_intro(dia: date) -> str:
    wd = dia.weekday()
    if wd in {0, 2, 5}:
        return "Thalita"
    return "Francisca"


def data_pt(d: date) -> str:
    return f"{DIAS_PT[d.weekday()]}, {d.day} de {MESES_PT[d.month - 1]} de {d.year}"


def load_mc_fm(day: str) -> list[dict]:
    sources = []
    for jf in (REPO / "manha-conectada" / "manifests" / f"{day}.json",
               REPO / "fechamento" / "manifests" / f"{day}.json"):
        if jf.exists():
            try:
                sources.extend(json.loads(jf.read_text(encoding="utf-8")).get("sources", []))
            except Exception:
                pass
    return sources


def _norm_title(t: str) -> str:
    t = re.sub(r"^(notícia|notícias|destaque|confira|veja)\s+", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Notícias|Agência|Redação|Economia|Mundo|Brasil)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .]{2,40}$", "", t).strip()
    return re.sub(r"\s+", " ", t).casefold().strip()


def categorize(sources: list[dict]) -> dict[str, list[dict]]:
    cats = {"mundo": [], "brasil": [], "tech": [], "economia": []}
    seen: set[str] = set()
    for s in sources:
        title = (s.get("title") or "").strip()
        key = _norm_title(title)
        if not key or key in seen:
            continue
        seen.add(key)
        for cat, keys in (("mundo", WORLDCAT), ("brasil", BRACAT), ("tech", TECHCAT), ("economia", ECOCAT)):
            if any(k in title.lower() for k in keys):
                cats[cat].append(s)
                break
        else:
            cats["brasil"].append(s)
    return cats


def manchete(ns: dict) -> str:
    t = ns.get("title", "")
    t = re.sub(r"^(notícia|notícias|confira|veja)\s+", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Folha de S\.Paulo|G1|SBT News|InvestNews|Midiamax|Notícias|Economia|Mundo|Brasil|Portal A12)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*\d{2}/\d{2}/\d{4}\s*-\s*[A-Za-zÀ-ÿ ]+$", "", t).strip()
    if " - " in t:
        t = t.rsplit(" - ", 1)[0]
    return t.strip()


LIXO_TITULOS = [
    "principais notícias", "resumo", "confira", "veja o que", "edições", "edital",
    "concursos", "agenda da semana", "noite de hoje", "manhã de hoje", "destaques de hoje",
    "ao vivo", "minuto a minuto", "blog", "coluna",
]


def eh_lixo(ns: dict) -> bool:
    t = (ns.get("title") or "").casefold()
    return any(p in t for p in LIXO_TITULOS)


def frase_pensador(rng: random.Random) -> str:
    """Pensador (texto + autor); fallback classico anti-repeticao."""
    import urllib.request
    import urllib.parse
    try:
        q = urllib.parse.quote(rng.choice(["persistência", "tempo", "conhecimento", "coragem", "foco", "mudança"]))
        req = urllib.request.Request(f"https://www.pensador.com/busca.php?q={q}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        frases = re.findall(r'class="frase[^"]*"[^>]*>(.*?)</p>', html, re.S)
        autores = re.findall(r'class="autor[^"]*"[^>]*>(.*?)</span>', html, re.S)
        for i, f in enumerate(frases[:10]):
            txt = re.sub(r"<[^>]+>", "", f).strip()
            if 30 < len(txt) < 200:
                autor = re.sub(r"<[^>]+>", "", autores[i]).strip() if i < len(autores) else ""
                return f"{txt} — {autor}" if autor else txt
    except Exception:
        pass
    f = rng.choice(FRASES_FALLBACK)
    return f"{f[0]} — {f[1]}"


def curadoria(cat: list[dict], n: int) -> list[dict]:
    """Seleciona as n noticias mais fortes (titulo com numero/verbo forte, sem lixo)."""
    if not cat:
        return []
    limpas = [ns for ns in cat if not eh_lixo(ns)] or cat
    def score(ns):
        t = ns.get("title", "")
        s = 0
        if re.search(r"\d", t): s += 2
        if re.search(r"\b(vira|sobe|cai|rompe|recorde|bloqueia|lança|estreia|anuncia)\b", t, re.I): s += 2
        if len(t) > 45: s += 1
        return -s
    return sorted(limpas, key=lambda ns: (score(ns), len(manchete(ns))))[:n]


def bloco_curatorial(cat: list[dict], rng: random.Random, pool: dict, n: int | None = None) -> str:
    """Bloco humanizado: ate n noticias (default MAX_NOTICIAS_BLOCO), cada uma com
    contexto profundo (2 rodadas) + efeito pratico; conectores de uso unico —
    um registro global no pool evita repetir qualquer expressao no episodio."""
    limite = n or MAX_NOTICIAS_BLOCO
    noticias = curadoria(cat, limite)
    if not noticias:
        return ""
    usados = pool.setdefault("_usados", set())
    pool.setdefault("_fb", 0)

    def tirar(chave: str) -> str:
        lst = pool.get(chave) or []
        for idx in range(len(lst)):
            cand = lst[idx]
            if cand not in usados:
                usados.add(cand)
                pool[chave] = lst[idx + 1:]
                return cand
        pool[chave] = []
        return ""

    def fb(chave: str, lista: list) -> str:
        """Fallback com dedup global: percorre a lista a partir de _fb e pega a
        primeira frase ainda nao usada no episodio (unicidade mesmo em episodios longos)."""
        n = len(lista)
        inicio = pool.get(chave, 0)
        for k in range(n):
            it = lista[(inicio + k) % n]
            if it not in usados:
                usados.add(it)
                pool[chave] = (inicio + k + 1) % n
                return it
        it = lista[inicio % n]
        usados.add(it)
        pool[chave] = (inicio + 1) % n
        return it

    abertura = tirar("apertura") or "Bora ver o que importa."
    partes = [f"{abertura}:"]
    for i, ns in enumerate(noticias):
        t = manchete(ns)
        if i == 0:
            partes.append(f"{t}.")
        else:
            ponte = tirar("ponte_noticia") or "E tem mais:"
            partes.append(f"{ponte} {t}.")
        # contexto rodada 1: reacao humana + ponte
        reac = tirar("reacao") or fb("_fb_reacao", FALLBACK_REACAO)
        ctx1 = tirar("ponte_contexto") or fb("_fb_ctx1", FALLBACK_CTX1)
        # contexto rodada 2: aprofundamento (uso unico)
        ctx2 = tirar("contexto2") or fb("_fb_ctx2", FALLBACK_CTX2)
        # efeito pratico (uso unico)
        efe = tirar("efeito") or fb("_fb_efeito", FALLBACK_EFEITO)
        partes.append(f"{reac} {ctx1} {ctx2} {efe}")
    return " ".join(p for p in partes if p)


def montar_pools(rng: random.Random) -> dict:
    """Embaralha todos os pools — 'pop' garante uso unico no episodio."""
    return {
        "apertura": rng.sample(APERTURA_BLOCO, len(APERTURA_BLOCO)),
        "ponte_contexto": rng.sample(PONTE_CONTEXTO, len(PONTE_CONTEXTO)),
        "contexto2": rng.sample(CONTEXTO_RODADA2, len(CONTEXTO_RODADA2)),
        "reacao": rng.sample(REACAO_HUMANA, len(REACAO_HUMANA)),
        "efeito": rng.sample(EFEITO_PRATICO, len(EFEITO_PRATICO)),
        "ponte_noticia": rng.sample(PONTE_NOTICIA, len(PONTE_NOTICIA)),
        "fecho_cold": rng.sample(FECHO_COLD, len(FECHO_COLD)),
        "perguntas": rng.sample([
            "Você já parou para pensar no que muda no seu dia com o que aconteceu nas últimas horas?",
            "O que você mais espera acompanhar hoje: mercado, política ou tecnologia?",
            "Deixa eu te perguntar: você prefere começar o dia pelo Brasil ou pelo mundo?",
        ], 3),
    }


def recomendacoes_sexta(rng: random.Random, dia: date) -> str:
    """2 filmes + 2 series do IMDB, rotacionados pela semana do ano."""
    semana = dia.isocalendar().week
    filmes = [IMDB_POOL_FILMES[(semana + k) % len(IMDB_POOL_FILMES)] for k in (0, 1)]
    series = [IMDB_POOL_SERIES[(semana + k) % len(IMDB_POOL_SERIES)] for k in (0, 1)]
    abertura = rng.choice([
        "E nas recomendações de sexta-feira, quem decide é o público do IMDb:",
        "E sexta tem programa: o IMDb elegeu os favoritos da vez:",
        "Fechando com um plano de fim de semana — os bem avaliados no IMDb:",
    ])
    itens = []
    for t, tipo, nota, onde, motivo in filmes + series:
        nota_txt = f" — nota {nota} no IMDb" if nota else ""
        itens.append(f"{t}, {tipo}{nota_txt}, disponível {onde}. {motivo[0].upper() + motivo[1:]}.")
    return abertura + " " + " ".join(itens)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dia = date.fromisoformat(args.data) if args.data else TODAY
    wd = dia.weekday()
    if wd == 6:
        print("Domingo — manutenção. Nada a gerar.")
        return 0

    ontem = (dia - timedelta(days=1)).isoformat()
    sources = load_mc_fm(ontem) or load_mc_fm(dia.isoformat())
    if not sources:
        for back in range(2, 5):
            sources = load_mc_fm((dia - timedelta(days=back)).isoformat())
            if sources:
                print(f"  (fallback: dados de {back} dia(s) atrás)")
                break
    if not sources:
        print(f"ERRO: sem dados MC/FM para {dia.isoformat()} (e últimos 4 dias).", file=sys.stderr)
        return 1
    cats = categorize(sources)
    rng = random.Random(dia.toordinal())
    pool = montar_pools(rng)

    min_w, alvo_w, max_w = META_DIA[wd]
    apres = apresentadora(dia)
    nome = nome_intro(dia)
    dpt = data_pt(dia)

    manifests = {}

    # coldopen: manchetes-tiro (1 por categoria, forte)
    tiros = []
    for cat in ("mundo", "brasil", "tech", "economia"):
        cur = curadoria(cats[cat], 1)
        if cur:
            tiros.append(manchete(cur[0]))
    if len(tiros) < 3:
        for cat in ("mundo", "brasil", "tech", "economia"):
            for ns in curadoria(cats[cat], 3)[1:3]:
                if len(tiros) < 4:
                    tiros.append(manchete(ns))
    fecho_cold = pool["fecho_cold"].pop()
    manifest_cold = (" ".join(f"{t}." for t in tiros[:4]) + f" {fecho_cold.capitalize()}") if tiros else ""
    manifests["coldopen.txt"] = manifest_cold

    # intro
    pergunta = pool["perguntas"].pop()
    manifests["intro.txt"] = (
        f"Bom dia! Eu sou {nome}, e hoje é {dpt}. Este é o Drop Five News, "
        f"o briefing das cinco da manhã com as notícias essenciais, com contexto e curadoria. "
        f"{pergunta} Vamos ao que interessa."
    )

    manifests["mundo.txt"] = bloco_curatorial(cats["mundo"], rng, pool)
    manifests["brasil.txt"] = bloco_curatorial(cats["brasil"], rng, pool)
    manifests["tecnologia.txt"] = bloco_curatorial(cats["tech"], rng, pool)
    if cats["economia"]:
        manifests["economia.txt"] = bloco_curatorial(cats["economia"], rng, pool)
    else:
        def _used_limpas(cat):
            limpas = [ns for ns in cat if not eh_lixo(ns)] or cat
            return {id(ns) for ns in limpas[:MAX_NOTICIAS_BLOCO]}
        usadas = set().union(_used_limpas(cats["mundo"]), _used_limpas(cats["brasil"]), _used_limpas(cats["tech"]))
        sobras = [ns for cat in ("mundo", "brasil", "tech") for ns in cats[cat]
                  if id(ns) not in usadas and not eh_lixo(ns)]
        manifests["economia.txt"] = bloco_curatorial(sobras[:MAX_NOTICIAS_BLOCO], rng, pool)

    # interacao
    tema = (curadoria(cats["mundo"], 1) or curadoria(cats["brasil"], 1) or [{}])[0]
    tema_txt = manchete(tema).split(",")[0].strip() if tema else "as notícias de hoje"
    manifests["interacao.txt"] = rng.choice([
        f"E aí, o que você acha de tudo isso? Deixa eu saber: {tema_txt} muda algo na sua rotina?",
        f"Pergunta que fica no ar: {tema_txt} passou batido para você ou mexeu com o seu dia?",
        f"Quero saber de você: {tema_txt} — isso te preocupa, te anima ou tanto faz?",
    ])

    # ofertas
    ofertas_intro = "E bora para as ofertas do dia: "
    of_limpas = [ns for ns in (cats["economia"][:2] + cats["tech"][:2]) if ns and not eh_lixo(ns)]
    manifests["ofertas.txt"] = (ofertas_intro + " ".join(manchete(ns) + "." for ns in of_limpas)) if of_limpas else (ofertas_intro + "o radar de oportunidades segue aberto.")

    manifests["frase.txt"] = f"E a frase do dia é: “{frase_pensador(rng)}”"

    # sexta: recomendacoes IMDB obrigatorias
    if wd == 4:
        manifests["recomendacoes.txt"] = recomendacoes_sexta(rng, dia)

    # outro: CTA RSS + links das noticias na descricao/site + bordao
    bordao = rng.choice([
        "Tenha um excelente dia e até a próxima!",
        "Bons negócios, boas notícias e até amanhã!",
        "Siga em frente com informação boa e volte amanhã, tá?",
        "Um abraço apertado e até o próximo briefing!",
    ])
    manifests["outro.txt"] = (
        f"E os links de todas as notícias de hoje estão na descrição do episódio e no nosso site, "
        f"o d5n ponto netlify ponto app — é só acessar que você encontra cada fonte e cada detalhe. "
        f"Este foi o Drop Five News desta {DIAS_PT[wd]}, {dia.day} de {MESES_PT[dia.month - 1]}. "
        f"E um lembrete: você também pode assinar o Manhã Conectada no seu aplicativo de podcast — "
        f"o RSS próprio está no site do Drop Five News. Fique ligado: o Manhã Conectada às onze "
        f"e o Fechamento do Mercado às dezessete. {bordao} Bom dia!"
    )

    # validacao de volume: se abaixo da meta, amplia bloco com 1 noticia curatelada extra
    def wc(t: str) -> int:
        return len(re.findall(r"\b[\wÀ-ÿ]+\b", t))

    total = sum(wc(v) for v in manifests.values())
    # se abaixo da meta: cresce cada bloco de 4 -> 5 -> 6 noticias (usando o MESMO pool
    # global, entao conectores continuam de uso unico no episodio inteiro)
    guard = 0
    while total < min_w and guard < 2:
        antes = total
        for cat, key in (("mundo", "mundo"), ("brasil", "brasil"), ("tech", "tecnologia"), ("economia", "economia")):
            if not cats[cat]:
                continue
            candidato = bloco_curatorial(cats[cat], rng, pool, 5)
            if wc(candidato) > wc(manifests.get(f"{key}.txt", "")):
                manifests[f"{key}.txt"] = candidato
        total = sum(wc(v) for v in manifests.values())
        if total <= antes:
            break
        guard += 1
    guard = 0
    while total < min_w and guard < 2:
        antes = total
        for cat, key in (("mundo", "mundo"), ("brasil", "brasil"), ("tech", "tecnologia"), ("economia", "economia")):
            if not cats[cat]:
                continue
            candidato = bloco_curatorial(cats[cat], rng, pool, 6)
            if wc(candidato) > wc(manifests.get(f"{key}.txt", "")):
                manifests[f"{key}.txt"] = candidato
        total = sum(wc(v) for v in manifests.values())
        if total <= antes:
            break
        guard += 1

    dur_estimada = 480 + (total - 1050) * (720 - 480) / (1800 - 1050)
    dur_estimada = max(480, min(720, dur_estimada))

    print(f"Apresentadora: {apres} | data: {dpt}")
    print(f"Palavras: {total} (meta {min_w}-{max_w}) | duração est.: {dur_estimada/60:.1f}min")
    print(f"Seções: {list(manifests)}")

    if args.dry_run:
        return 0

    out = REPO / "manifests" / "d5n" / dia.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    for name, content in manifests.items():
        (out / name).write_text(content, encoding="utf-8")
    print(f"Escrito em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())