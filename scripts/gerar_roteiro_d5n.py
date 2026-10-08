#!/usr/bin/env python3
"""Gera manifests de texto para D5N a partir dos manifests diários de MC e FM.

Usa dados reais de ontem (MC/FM) como fallback quando hoje ainda não foi produzido.
Gera conteúdo com volume suficiente para o mixer v10 (480-720s de narração).
"""
import json
import os
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d5n_data_ptbr import (  # noqa: E402
    data_curta, data_extenso, hoje_editorial, MESES as MESES_NOMES,
)

REPO = Path(os.environ.get("D5N_REPO", "/root/repositorio/d5n-videocast-source")).resolve()

# Fuso editorial America/Sao_Paulo via helper compartilhado: o cron roda no
# America/Manaus e date.today() pode cair no dia errado perto da meia-noite.
TODAY_DATE = hoje_editorial()
TODAY = TODAY_DATE.isoformat()
YESTERDAY = (TODAY_DATE - timedelta(days=1)).isoformat()

# O dia da semana e a data falada em voz alta sao lidos de uma vez e usados em
# varios trechos. "quinta-feira" estava hardcoded em tres lugares e o episodio
# falava o dia errado em qualquer dia que nao fosse quinta.
DIAS_SEMANA = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)
DIA_SEMANA = DIAS_SEMANA[TODAY_DATE.weekday()]
DATA_FALADA = f"{TODAY_DATE.day} de {MESES_NOMES[TODAY_DATE.month - 1]}"


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
    """Carrega manifestos MC e FM de um dia especifico.

    Ordem de preferencia: MC/FM (sao a fonte editorial, ja categorizada), e se
    nao houver (eles pararam em 29/09/2026), cai no manifest de trends do dia,
    gerado por trends_para_manifest.py a partir dos RSSs coletados. Sem isso o
    roteiro cai no fallback e sai com 3.4k chars, abaixo do minimo de 480s do
    mixer — foi o que travou o D5N apos a queda do host.
    """
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
    if sources:
        return sources

    trends = REPO / "manifests" / "d5n" / "trends" / f"{day}.json"
    if not trends.exists():
        trends = REPO / "manifests" / "d5n" / "trends" / f"{YESTERDAY}.json"
    if trends.exists():
        try:
            data = json.loads(trends.read_text())
            # o manifest de trends ja vem com "categoria"; o categorize() do
            # gerador recalcula por palavra-chave e daria o mesmo resultado.
            fontes = data.get("sources", [])
            print(f"[dados] sem MC/FM de {day}; usando {len(fontes)} manchetes "
                  f"de trends ({trends.name})")
            return fontes
        except Exception as e:
            print(f"[dados] trends {trends} ilegivel: {e}")
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

# ── coldopen: manchetes concretas, modelo TecMundo ───────────────────────────
# Antes: uma frase sintetica generica ("O Ibovespa reage a movimentos
# internacionais...") que nao dizia nada. O video de referencia abre com 10
# manchetes em 40 segundos: verbo + fato concreto, sem adjetivo, ja sem dizer
# a data (a intro faz isso logo em seguida).
# Puxa as manchetes mais varias categorias, alternadas, para nao sair 3 de
# economia seguidas.
def manchetes_abertura(limite: int = 7) -> list:
    # Copia antes de consumir: `fila.pop(0)` nas listas de cats[] esvaziava a
    # fonte, e como a mesma lista alimenta as secoes mundo/brasil/tec/economia
    # mais abaixo, o coldopen saia vazio e as secoes perdiam as primeiras
    # noticias (foi o que aconteceu no teste com 44 fontes reais).
    filas = [list(cats["mundo"]), list(cats["brasil"]),
             list(cats["tech"]), list(cats["economia"])]
    intercalado: list = []
    i = 0
    while len(intercalado) < limite and any(filas):
        fila = filas[i % len(filas)]
        if fila:
            intercalado.append(fila.pop(0))
        i += 1
    return intercalado


# Deduplicacao entre secoes: o mesmo fato pode ser classificado em duas
# categorias (a Anac ja apareceu em mundo E em economia, dita duas vezes com 2
# minutos de distancia). Consome cada manchete em uma unica secao, na ordem
# em que as secoes sao montadas.
_USADAS: set = set()


def noticias(categoria: str, minimo: int, teto: int) -> str:
    """Monta o texto das noticias de uma secao, sem repetir o que ja saiu.

    `minimo` e o piso, `teto` o maximo confortavel. O mixer recusa o episodio
    abaixo de 480s (~7.6k chars), e com os 7 feeds originais o roteiro parava
    em ~6.0k: sobrava materia de qualidade (80 manchetes, 46 delas fora do
    ar) mas o teto fixo nao deixava entrar.

    Por isso o teto sobe sozinho quando o episodio ainda esta curto: e melhor
    12 noticias de tecnologia bem faladas do que um episodio que o mixer
    recusa. O piso continua valendo — 15 noticias de economia seguidas seria
    outra coisa, e `economia` quase sempre tem menos que o piso mesmo.
    """
    disponiveis = [n for n in cats[categoria] if manchete(n) not in _USADAS]
    if not disponiveis:
        return ""
    if len(disponiveis) <= minimo:
        escolhidas = disponiveis
    else:
        escolhidas = disponiveis[:minimo]
        if len(disponiveis) > teto:
            # sobe ate o teto; um piso global de chars e tratado no fim
            escolhidas = disponiveis[:teto]
    for n in escolhidas:
        _USADAS.add(manchete(n))
    return " ".join(fmt_news(n) for n in escolhidas)

abertura = manchetes_abertura()
if abertura:
    for n in abertura:
        _USADAS.add(manchete(n))
    manifests["coldopen.txt"] = " ".join(fmt_news(n) for n in abertura).strip()
else:
    manifests["coldopen.txt"] = (
        "Os principais mercados abrem em movimento enquanto o Brasil acompanha "
        "a agenda economica do dia. Os detalhes vem a seguir."
    )

# intro
# "briefing" e palavra inglesa: o validador editorial barra ruido/ingles no
# texto falado. Troquei por "panorama", que e o que o Jean ouve no referencia.
manifests["intro.txt"] = (
    f"Bom dia! Eu sou Francisca, e hoje é {data_extenso(TODAY_DATE)}. "
    f"Este é o Drop Five News, o seu panorama das 05 horas da manhã com as "
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
    world_news = noticias("mundo", 6, 10)
    manifests["mundo.txt"] = f"{world_intro}{world_news}"
else:
    manifests["mundo.txt"] = f"{world_intro} A atenção está nos mercados emergentes e nas negociações comerciais entre grandes potências."

# brasil
# "a agenda econômica da quinta-feira" estava hardcoded: na quarta-feira o
# episodio falava o dia errado. Puxa do helper. E a data ISO (2026-10-07) nao
# pode ser falada: TTS le "2026" como "duas mil e vinte e seis". O validador
# barra data ISO crua no texto.
brasil_intro = (
    f"No Brasil, o foco da {DIA_SEMANA}, {TODAY_DATE.day} de "
    f"{MESES_NOMES[TODAY_DATE.month - 1]}, reúne a agenda econômica "
    f"em Brasília com discussões sobre equilíbrio fiscal e projetos prioritários "
    f"no Congresso. O cenário político mantém alta tensão, enquanto o Judiciário "
    f"pesa decisões que impactam a estabilidade do país. "
)
if cats["brasil"]:
    brasil_news = noticias("brasil", 6, 10)
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
    tech_news = noticias("tech", 5, 9)
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
    eco_news = noticias("economia", 4, 8)
    manifests["economia.txt"] = f"{eco_intro}{eco_news}"
else:
    manifests["economia.txt"] = f"{eco_intro} A atenção está nos resultados corporativos e na agenda de publicações econômicas."

# interacao
# O quality gate barra CTA fora do encerramento: mandar "siga no Instagram"
# aqui reprovava o episodio. Fica so o convite a comentar, que e o que a secao
# promete; os canais ficam no outro.txt.
manifests["interacao.txt"] = (
    "E ai, voce acompanhou as noticias da manha? Deixe seu comentario aqui "
    "em baixo e conte o que voce achou das ultimas informacoes sobre o mercado "
    "e a economia brasileira. Sua opiniao importa!"
)

# ofertas
# "quinta-feira" estava hardcoded no codigo: num dia de quarta-feira o episodio
# saia com o dia errado falado em voz alta. Puxa do helper, que ja resolve o
# fuso editorial.
ofertas_intro = (
    f"Nesta {DIA_SEMANA}, {TODAY_DATE.day} de "
    f"{MESES_NOMES[TODAY_DATE.month - 1]}, o mercado oferece oportunidades em "
    f"setores como telecomunicações, energia renovável e infraestrutura de "
    f"dados. Empresas estão em expansão e buscando talentos qualificados. "
)
if cats["economia"] or cats["tech"]:
    # Sem deduplicar: SpaceX e Meta ja saem em tecnologia, e repetir a noticia
    # em ofertas so ocupava tempo com o mesmo fato dito de outro jeito.
    _oferta_n = [n for n in (cats["economia"][:3] + cats["tech"][:3])
                 if manchete(n) not in _USADAS]
    ofertas_news = " ".join(fmt_news(n) for n in _oferta_n)
    manifests["ofertas.txt"] = f"{ofertas_intro}{ofertas_news}"
else:
    manifests["ofertas.txt"] = f"{ofertas_intro} Acompanhe as vagas e oportunidades na nossa página de cursos."

# frase — mensagem do dia de um pensador, com a citacao do banco
# Antes: "Quinta-feira, {data}. A tecnologia continua..." — nao era citacao de
# ninguem, era motivacao genérica que soava como frase de pensador. Agora a
# citacao vem do arquivo verificado, com o autor e a obra, e a personagem nao
# inventa: se nao houver citacao para o dia, o trecho fica para revisao.
# A citacao e texto de terceiro: exige `fonte` conferida no banco, nao gerada.
from frase_do_dia import citacao_para  # noqa: E402

_fr = citacao_para(TODAY_DATE.day, TODAY_DATE.month)
if _fr:
    manifests["frase.txt"] = (
        f"A mensagem do dia e de {_fr['autor']}. {_fr['citacao']} "
        f"({_fr['obra']}). {_fr['ponto']}"
    )
else:
    manifests["frase.txt"] = (
        "Nao temos citacao verificada para esta data. Este trecho precisa de "
        "revisao antes de ir ao ar."
    )
    print(f"[AVISO] frase do dia sem citacao no banco para "
          f"{TODAY_DATE.day:02d}-{TODAY_DATE.month:02d}")

# recomendacoes — direto, no modelo TecMundo.
# Antes: "recomendamos acompanhar... sugerimos revisar sua carteira... vale
# conferir", tudo indireto e sem destino. No video de referencia cada item e
# verbo + onde: "confira no site", "ative o lembrete", "pesquise no Google".
# Mantem as sessoes do D5N (G1/Valor/Banco Central, site, MC e FM), mas cada
# linha vira um comando com destino explicito.
manifests["recomendacoes.txt"] = (
    "Para fechar o dia: abra o site do Drop Five News e confira o episodio "
    "completo com os capitulos, para pular direto ao tema que te interessa. "
    "Se quiser o dado da manha, ouve o Manha Conectada as onze. "
    "Se quiser o fechamento do mercado, volta no Fechamento do Mercado as "
    "dezessete horas. Para o texto das noticias, le o G1 e o Valor Economico. "
    "E ativa o lembrete do podcast para nao perder nenhum episodio."
)

# historia — fato real que aconteceu NESTE dia do calendario
# Antes: texto motivacional sobre negocios, sem nenhum fato. Agora segue o
# padrao do video de referencia: um evento que ocorreu em (dia, mes) de algum
# ano, com a data falada em voz alta e um fechamento que da sentido ao fato.
# O texto vem do banco curado (assets/historia-das-datas.json), nunca gerado:
# um LLM escrevendo "fato historico" produz data e nome errados com muita
# naturalidade. Ver a data antes de publicar e obrigatorio.
from historia_do_dia import entrada_para  # noqa: E402

_h = entrada_para(TODAY_DATE.day, TODAY_DATE.month)
if _h:
    # so a primeira letra, para nao rebaixar "Luna 3" e "Terra" — .capitalize()
    #(lowercases) transformava o nome proprio em "luna 3" e a TTS falava errado.
    def _ini(t: str) -> str:
        return t[:1].upper() + t[1:]

    manifests["historia.txt"] = (
        f"E nao aconteceu na historia da tecnologia. {TODAY_DATE.day} de "
        f"{MESES_NOMES[TODAY_DATE.month - 1]} de {_h['ano']}. "
        f"{_ini(_h['titulo'])}. {_ini(_h['detalhe'])}. {_ini(_h['fechamento'])}."
    )
else:
    # Sem fato registrado para a data: o quality gate barra o episodio para
    # revisao humana. Prefere nao publicar a inventar.
    manifests["historia.txt"] = (
        "Nao temos um fato historico confirmado para esta data. Este trecho "
        "precisa de revisao antes de ir ao ar."
    )
    print(f"[AVISO] historia do dia sem entrada no banco para "
          f"{TODAY_DATE.day:02d}-{TODAY_DATE.month:02d}: revisar antes de publicar")

# outro — só a saudação, sem repetir data nem nome do programa.
# A intro ja anuncia data e programa; repetir no encerramento era o que o
# Jean apontou. No video de referencia o encerramento e seco: "Curta,
# compartilhe e se inscreva. Ate amanha."
manifests["outro.txt"] = (
    "Era isso por hoje. Curte, compartilhe e se inscreva para nao perder o "
    "Drop Five News de amanha as cinco da manha. Ate amanha, e boa semana!"
)

# Preenchimento final: se o episodio ainda esta curto para o mixer, completa
# com as manchetes que sobram. Com 80 coletadas sobravam 46 fora do ar e o
# roteiro parava em ~6.6k chars, quase 1k abaixo do minimo de 480s.
#
# Distribui o excedente respeitando o teto de cada secao (o validar-manifests
# reprova acima de 2600 chars por secao: encher tudo em mundo.txt dava 2824 e
# o roteiro inteiro era rejeitado por causa de um unico bloco). Alterna entre
# as secoes para caber em todas.
#
# Vem DEPOIS das secoes fixas (frase, historia, outro), entao nunca atropela a
# historia do dia nem o encerramento.
DENSIDADE_D5N = 15.9
MIN_CHARS = int(480 * DENSIDADE_D5N)   # ~7.632 chars = 480s
TETO_SECAO = 2500   # folga sobre o limite de 2600 do validador


def _sobra(cat: str) -> list:
    return [n for n in cats[cat] if manchete(n) not in _USADAS]


# Secoes por onde o excedente pode entrar, na ordem em que faz sentido
# editorialmente: o ouvinte nao deve ouvir 25 noticias de tecnologia seguidas.
_DESTINO = [
    ("tech", "mundo"), ("mundo", "mundo"), ("brasil", "brasil"),
    ("mundo", "economia"), ("tech", "tecnologia"), ("brasil", "economia"),
]

total_bytes = sum(len(v) for v in manifests.values())
if total_bytes < MIN_CHARS:
    for _cat, _bloco in _DESTINO:
        if total_bytes >= MIN_CHARS:
            break
        # nao estoura a secao de destino
        folga = TETO_SECAO - len(manifests[f"{_bloco}.txt"])
        if folga < 200:
            continue
        extra = _sobra(_cat)[:8]
        if not extra:
            continue
        add = " ".join(fmt_news(n) for n in extra)
        if len(add) > folga:
            # cabe so o que couber: recorta por manchete, nunca no meio de uma
            while extra and len(add) > folga:
                extra.pop()
                add = " ".join(fmt_news(n) for n in extra)
            if not extra:
                continue
        manifests[f"{_bloco}.txt"] += " " + add
        for n in extra:
            _USADAS.add(manchete(n))
        total_bytes = sum(len(v) for v in manifests.values())
        print(f"[preenchimento] +{len(extra)} de '{_cat}' em {_bloco}.txt "
              f"(total {total_bytes} chars)")

total_bytes = sum(len(v) for v in manifests.values())

# Densidade de fala: o mixer v10 so aceita 480-720s de audio.
#
# Medido no D5N de verdade (ep076, 498.44s com 7.937 chars spoken) = 15.9
# chars/s. A referencia TecMundo (14min37s, 13.011 chars) = 14.9 chars/s. A
# diferenca e pequena, entao o minimo e calculado pela densidade REAL do D5N,
# nao pela da referencia: 480s * 15.9 = ~7.640 chars.
#
# A estimativa por chars/s e so um aviso na geracao. O mixer decide: ele mede
# a duracao do audio e recusa fora de 480-720s.
for name, content in manifests.items():
    path = manifest_dir / name
    path.write_text(content, encoding="utf-8")

print(f"Manifests D5N criados com sucesso em: {manifest_dir}")
print(f"Total: {len(manifests)} secoes, {total_bytes} chars "
      f"(~{total_bytes/DENSIDADE_D5N:.0f}s de audio na densidade medida do D5N)")
if total_bytes < MIN_CHARS:
    faltam = MIN_CHARS - total_bytes
    print(f"[AVISO] roteiro curto: {total_bytes} chars < {MIN_CHARS} "
          f"(faltam ~{faltam} para o minimo de 480s do mixer). "
          f"Materiais: {len(all_news)} noticias coletadas. "
          f"O mixer vai recusar o episodio.")
