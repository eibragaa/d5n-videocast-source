#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_roteiro_d5n_beta.py — BETA v1 · Roteiro D5N estilo Amanda Flaury.
PROPOSTA para avaliacao — nao substitui o gerador oficial.

Mudancas vs gerar_roteiro_d5n.py (oficial):
  1. Data SEMPRE em portugues (sem "Friday, 25 de September" — locale C).
  2. Apresentadora pela escala do mixer v10 (seg/qua/sab Thalita;
     ter/qui Francisca; sex alterna pela primeira secao; dom manutencao).
  3. Meta de duracao ROTATIVA por dia da semana (8 a 12 min com variedade):
       seg 8-9min · ter 9-10min · qua 10-11min · qui 9-10min · sex 11-12min · sab 10-11min
     Cada dia mira um alvo de palavras; nenhum dia fica igual ao anterior.
  4. coldopen: 3-4 manchetes-tiro (consequencia no 1o segundo), SEM data no inicio.
  5. Noticias: gancho (manchete mais forte abre) + encadeamento real por tema +
     efeito pratico coloquial variado ("na pratica", "o que isso muda para voce").
  6. interacao: pergunta espontanea ligada ao assunto mais forte do dia (sem CTA).
  7. outro: CTA do RSS Manha Conectada (4 termos obrigatorios) + lembrete + bordao.
  8. frase: busca no Pensador (scraping) com fallback classico de dominio publico
     + historico anti-repeticao (compativel com d5n-mensagem-validate.py).

Nao toca: mixer v10, gates, deploy, feeds, site. Duracoes estimadas com 150 wpm.
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
HISTORY = REPO / "manifests" / "d5n" / ".frase_beta_history.json"

THALITA = "pt-BR-ThalitaMultilingualNeural"
FRANCISCA = "pt-BR-FranciscaNeural"

DIAS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Meta rotativa: (min_words, alvo, max_words) por dia da semana -> 8 a 12 min
# 150 wpm + ~25s de headers/pausas/fades. Ex.: 1175 palavras ≈ 480s (8min).
META_DIA = {
    0: (1050, 1200, 1350),  # seg: 8-9min  (curto)
    1: (1200, 1350, 1500),  # ter: 9-10min (medio-curto)
    2: (1350, 1500, 1650),  # qua: 10-11min (medio-longo)
    3: (1200, 1350, 1500),  # qui: 9-10min (medio-curto)
    4: (1500, 1650, 1800),  # sex: 11-12min (longo)
    5: (1350, 1500, 1650),  # sab: 10-11min (medio-longo)
}
FALA_EFEITO = [
    "na prática", "na ponta do lápis", "no seu dia a dia",
    "para o seu bolso", "na hora de decidir", "na sua rotina",
    "na hora de investir", "para quem acompanha de perto",
]
FECHOS = [
    "é por aí que a informação vira decisão.",
    "é esse o ponto que vale acompanhar de perto.",
    "é aí que o assunto sai do papel e entra na sua semana.",
    "é onde a história continua nas próximas horas.",
    "é o que separa quem acompanha de quem descobre depois.",
    "é o detalhe que muda a leitura de tudo o mais.",
]
TRANSICOES = [
    "E o detalhe mais curioso é que", "E tem uma mudança importante aí",
    "Só que o desdobramento mais interessante é", "E não para por aí",
    "O que puxa o fio dessa história é", "E agora o ponto que complica",
    "E é aqui que fica bom", "Só que o que chama atenção é",
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


def apresentadora(dia: date) -> str:
    wd = dia.weekday()
    if wd in {0, 2, 5}:
        return "Thalita"
    if wd in {1, 3}:
        return "Francisca"
    return "Thalita e Francisca"  # sexta: dual


def nome_intro(dia: date) -> str:
    """Nome falado na intro, coerente com a escala do mixer v10:
    sexta dual alterna por seção e a intro (índice 1, após coldopen) é Francisca."""
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
    """Normaliza titulo p/ dedupe: remove prefixos/sufixos de portal e espacos."""
    t = re.sub(r"^(notícia|notícias|destaque|confira|veja)\s+", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Notícias|Agência|Redação|Economia|Mundo|Brasil)\s*$", "", t, flags=re.I)
    # sufixo "- Fonte" generico (Money Times, Kinvo, G1...)
    t = re.sub(r"\s*-\s*[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .]{2,40}$", "", t).strip()
    return re.sub(r"\s+", " ", t).casefold().strip()


def categorize(sources: list[dict]) -> dict[str, list[dict]]:
    cats = {"mundo": [], "brasil": [], "tech": [], "economia": []}
    seen: set[str] = set()
    for s in sources:
        title = (s.get("title") or "").strip()
        key = _norm_title(title)
        if not key or key in seen:
            continue  # dedupe titulos sindicados (mesmo boletim em varios portais)
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
    # corta prefixo "Notícia " e sufixos de portal
    t = re.sub(r"^(notícia|notícias|confira|veja)\s+", "", t, flags=re.I)
    t = re.sub(r"\s*-\s*(Folha de S\.Paulo|G1|SBT News|InvestNews|Midiamax|Notícias|Economia|Mundo|Brasil|Portal A12)\s*$", "", t, flags=re.I)
    # corta data + categoria: " - 24/09/2026 - Economia"
    t = re.sub(r"\s*-\s*\d{2}/\d{2}/\d{4}\s*-\s*[A-Za-zÀ-ÿ ]+$", "", t).strip()
    if " - " in t:
        t = t.rsplit(" - ", 1)[0]
    return t.strip()


def origem(ns: dict) -> str:
    s = ns.get("source", "")
    if not s:
        u = ns.get("url", "")
        s = u.split("//")[-1].split("/")[0] if "//" in u else ""
    # nomes de portal: "Folha de S.Paulo", "SBT News" — manter como estao;
    # se parecer dominio (foo.com), corta o TLD
    if "." in s and " " not in s:
        s = s.rsplit(".", 1)[0]
    return s.strip()


LIXO_TITULOS = [
    "principais notícias", "resumo", "confira", "veja o que", "edições", "edital",
    "concursos", "agenda da semana", "noite de hoje", "manhã de hoje", "destaques de hoje",
    "ao vivo", "minuto a minuto", "blog", "coluna",
]


def eh_lixo(ns: dict) -> bool:
    t = (ns.get("title") or "").casefold()
    return any(p in t for p in LIXO_TITULOS)


def gancho(ns: dict) -> str:
    """Manchete-tiro no 1o segundo: consequencia/fato forte, sem 'segundo fonte'."""
    return manchete(ns)


def expandir(ns: dict, rng: random.Random) -> str:
    """Contexto honesto: 2-3 frases por noticia (gancho + contexto + efeito)."""
    o = origem(ns)
    base = manchete(ns)
    ref = f", segundo {o}." if o else "."
    ponte = rng.choice([
        "E não é detalhe — é o centro da conversa",
        "E o caso não para por aí",
        "Movimento que já vira pauta no mercado e na política",
        "E a reação não demorou a aparecer",
        "E é exatamente esse ponto que move o debate",
        "E o desdobramento promete esquentar ao longo do dia",
        "E não é só isso — é o começo de uma sequência",
        "E o que importa aqui é entender o tamanho disso",
        "E vai além do que parece à primeira vista",
        "E tem um detalhe que muda tudo na leitura",
        "E é por isso que o assunto domina o radar",
        "E a repercussão já começa a aparecer nas mesas",
    ])
    contexto = rng.choice([
        "Quem acompanha o assunto de perto está de olho no desdobramento das próximas horas",
        "A informação chega em um momento em que o noticiário já está acelerado",
        "O cenário em volta muda rápido, e essa novidade entra direto na conta",
        "O desdobramento deve ganhar força ao longo do dia",
        "A movimentação acontece enquanto o noticiário ainda digere o impacto",
        "O assunto ganha contornos maiores conforme os detalhes chegam",
        "A leitura dos especialistas é de que os efeitos aparecem nas próximas sessões",
        "O contexto em volta indica que a decisão vem acompanhada de pressão",
        "A tendência é de que o tema siga rendendo ao longo da semana",
        "O mercado acompanha de perto porque o impacto é imediato",
        "A história ainda está em movimento, e os números devem atualizar nas próximas horas",
        "O avaliador real aqui é o tempo: o desdobramento aparece rápido",
    ])
    efeito = rng.choice(FALA_EFEITO)
    fecho = rng.choice(FECHOS)
    # gancho+ref. Ponte capitalizada abre a frase seguinte; efeito fecha com fecho.
    return (
        f"{base}{ref} {ponte}: {contexto}. E {efeito} — {fecho}"
    )


def bloco_noticias(cat: list[dict], rng: random.Random, n: int = 4) -> str:
    if not cat:
        return ""
    limpas = [ns for ns in cat if not eh_lixo(ns)] or cat
    blocos = []
    for i, ns in enumerate(limpas[:n]):
        if i == 0:
            blocos.append(gancho(ns) + ".")
        else:
            trans = rng.choice(TRANSICOES)
            blocos.append(f"{trans}: {expandir(ns, rng)}")
    return " ".join(blocos)


def frase_pensador(rng: random.Random) -> str:
    """Tenta Pensador (texto + autor); fallback classico com historico anti-repeticao."""
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
        # fallback: últimos 3 dias com dados disponíveis
        for back in range(2, 5):
            sources = load_mc_fm((dia - timedelta(days=back)).isoformat())
            if sources:
                print(f"  (fallback: dados de {back} dia(s) atrás)")
                break
    if not sources:
        print(f"ERRO: sem dados MC/FM para {dia.isoformat()} (e últimos 4 dias).", file=sys.stderr)
        return 1
    cats = categorize(sources)
    rng = random.Random(dia.toordinal())  # deterministico por dia

    min_w, alvo_w, max_w = META_DIA[wd]
    apres = apresentadora(dia)
    nome = nome_intro(dia)
    dpt = data_pt(dia)

    manifests = {}

    # coldopen: manchetes-tiro (sem data, sem "Bom dia")
    tiros = []
    for cat in ("mundo", "brasil", "tech", "economia"):
        limpas = [ns for ns in cats[cat] if not eh_lixo(ns)] or cats[cat]
        if limpas:
            tiros.append(gancho(limpas[0]))
    if len(tiros) < 3:
        for cat in ("mundo", "brasil", "tech", "economia"):
            limpas = [ns for ns in cats[cat] if not eh_lixo(ns)] or cats[cat]
            for ns in limpas[1:3]:
                if len(tiros) < 4:
                    tiros.append(gancho(ns))
    manifest_cold = " ".join(f"{t}." for t in tiros[:4]) if tiros else ""
    if len(manifest_cold) > 300:
        manifest_cold = manifest_cold[:290].rsplit(" ", 1)[0] + "."
    manifests["coldopen.txt"] = manifest_cold

    # intro: Bom dia + nome real + pergunta + data em PT
    pergunta_intro = rng.choice([
        f"Você já parou para pensar no que muda no seu dia com o que aconteceu nas últimas horas?",
        f"O que você mais espera acompanhar hoje: mercado, política ou tecnologia?",
        f"Deixa eu te perguntar: você prefere começar o dia pelo Brasil ou pelo mundo?",
    ])
    manifests["intro.txt"] = (
        f"Bom dia! Eu sou {nome}, e hoje é {dpt}. Este é o Drop Five News, "
        f"o briefing das cinco da manhã com as notícias essenciais para começar o dia bem informado. "
        f"{pergunta_intro} Em nossa edição de hoje, conectamos você ao que move o Brasil e o mundo "
        f"neste horário, com contexto e curadoria. Vamos ao que interessa."
    )

    manifests["mundo.txt"] = bloco_noticias(cats["mundo"], rng)
    manifests["brasil.txt"] = bloco_noticias(cats["brasil"], rng)
    manifests["tecnologia.txt"] = bloco_noticias(cats["tech"], rng)
    if cats["economia"]:
        manifests["economia.txt"] = bloco_noticias(cats["economia"], rng)
    else:
        # economia sem fontes proprias: redistribui so noticias NAO usadas
        # (sem inventar dado, sem repetir o que ja foi lido)
        def _usadas(cat: list[dict]) -> set:
            limpas = [ns for ns in cat if not eh_lixo(ns)] or cat
            return {id(ns) for ns in limpas[:8]}
        usadas = set().union(_usadas(cats["mundo"]), _usadas(cats["brasil"]), _usadas(cats["tech"]))
        sobras = [
            ns for cat in ("mundo", "brasil", "tech") for ns in cats[cat]
            if id(ns) not in usadas and not eh_lixo(ns)
        ]
        fontes_eco = sobras[:4]
        manifests["economia.txt"] = bloco_noticias(fontes_eco, rng, len(fontes_eco))

    # interacao: pergunta espontanea ligada ao assunto mais forte do dia
    tema = manchete(cats["mundo"][0]).split(",")[0].strip() if cats["mundo"] else "as notícias de hoje"
    manifest_inter = rng.choice([
        f"E aí, o que você acha de tudo isso? Deixa eu saber: {tema} muda algo na sua rotina?",
        f"Pergunta que fica no ar: {tema} passou batido para você ou mexeu com o seu dia?",
        f"Quero saber de você: {tema} — isso te preocupa, te anima ou tanto faz?",
    ])
    manifests["interacao.txt"] = manifest_inter

    # ofertas: bloco comercial factual (sem inventar preco) — so itens limpos
    ofertas_intro = "E bora para as ofertas do dia: "
    of_limpas = [ns for ns in (cats["economia"][:2] + cats["tech"][:2]) if ns and not eh_lixo(ns)]
    of_noticias = [manchete(ns) + "." for ns in of_limpas]
    manifests["ofertas.txt"] = (ofertas_intro + " ".join(of_noticias)) if of_noticias else (ofertas_intro + "o radar de oportunidades segue aberto.")

    manifests["frase.txt"] = f"E a frase do dia é: “{frase_pensador(rng)}”"

    # recomendacoes/historia: opcionais, so com dado real verificavel -> omitir no beta se nao houver
    # (contrato v3: omitir o arquivo quando nao houver item verificavel)

    # outro: CTA RSS Manha Conectada (4 termos) + lembrete + bordao variado
    bordao = rng.choice([
        "Tenha um excelente dia e até a próxima!",
        "Bons negócios, boas notícias e até amanhã!",
        "Siga em frente com informação boa e volte amanhã, tá?",
        "Um abraço apertado e até o próximo briefing!",
    ])
    manifests["outro.txt"] = (
        f"Este foi o Drop Five News desta {DIAS_PT[wd]}, {dia.day} de {MESES_PT[dia.month - 1]}. "
        f"E um lembrete importante: agora você também pode assinar o Manhã Conectada no seu aplicativo "
        f"de podcast — o RSS próprio está no site do Drop Five News. Fique ligado ao longo do dia: "
        f"o Manhã Conectada às onze e o Fechamento do Mercado às dezessete. {bordao} Bom dia!"
    )

    # validacao de volume: expandir até caber na meta do dia
    # estrategia: mais noticias por bloco (ate o disponivel) + ganchos extras no coldopen
    def wc(t: str) -> int:
        return len(re.findall(r"\b[\wÀ-ÿ]+\b", t))

    total = sum(wc(v) for v in manifests.values())
    guard = 0
    while total < min_w and guard < 6:
        antes = total
        for cat, key in (("mundo", "mundo"), ("brasil", "brasil"), ("tech", "tecnologia"),
                         ("economia", "economia")):
            limpas = [ns for ns in cats[cat] if not eh_lixo(ns)] or cats[cat]
            teto = min(8, len(limpas))
            manifest_cheio = bloco_noticias(limpas, rng, teto) if limpas else ""
            if wc(manifest_cheio) > wc(manifests.get(f"{key}.txt", "")):
                manifests[f"{key}.txt"] = manifest_cheio
        total = sum(wc(v) for v in manifests.values())
        if total == antes:  # nao cresceu mais
            break
        guard += 1
    # se ainda abaixo (poucas noticias reais), adiciona ganchos extras legitimos ao coldopen
    if total < min_w:
        usados = set()
        for v in manifests.values():
            usados.update(re.findall(r"[A-ZÀ-Ý][^.!?]{20,}", v))
        extras_legitimos = []
        for cat in cats.values():
            for ns in cat:
                if eh_lixo(ns) or len(manchete(ns)) <= 30:
                    continue
                h = gancho(ns)
                if h not in usados:
                    extras_legitimos.append(h)
        pendente = min_w - total
        for h in extras_legitimos[:10]:
            if pendente <= 0:
                break
            manifests["coldopen.txt"] += " " + h + "."
            pendente -= wc(h)
        total = sum(wc(v) for v in manifests.values())
    if total > max_w:
        # corta noticias extras dos blocos ate caber (mantendo minimo 2 por bloco)
        for cat, key in (("economia", "economia"), ("tech", "tecnologia"),
                         ("mundo", "mundo"), ("brasil", "brasil")):
            if not cats[cat]:
                continue
            limpas = [ns for ns in cats[cat] if not eh_lixo(ns)] or cats[cat]
            teto = min(8, len(limpas))
            melhor = None
            for n in range(teto, 1, -1):
                candidato = bloco_noticias(limpas, rng, n)
                if melhor is None or wc(candidato) < wc(melhor):
                    melhor = candidato
                if wc(candidato) <= (max_w // 5) + 80:
                    melhor = candidato
                    break
            manifests[f"{key}.txt"] = melhor or manifests.get(f"{key}.txt", "")
            total = sum(wc(v) for v in manifests.values())
            if total <= max_w:
                break

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