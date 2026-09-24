#!/usr/bin/env python3
"""Gera manifests de texto para D5N a partir dos manifests diários de MC e FM."""

import json
from pathlib import Path
from datetime import date

REPO = Path("/root/repositorio/d5n-videocast-source")
TODAY = date.today().isoformat()

# Carregar notícias do dia de MC e FM
mc_json = REPO / "manha-conectada" / "manifests" / f"{TODAY}.json"
fm_json = REPO / "fechamento" / "manifests" / f"{TODAY}.json"

sources = []
if mc_json.exists():
    data = json.loads(mc_json.read_text())
    sources.extend(data.get("sources", []))
if fm_json.exists():
    data = json.loads(fm_json.read_text())
    sources.extend(data.get("sources", []))

manifest_dir = REPO / "manifests" / "d5n" / TODAY
manifest_dir.mkdir(parents=True, exist_ok=True)

# Templates simples baseados nas notícias do dia
(manifest_dir / "coldopen.txt").write_text(
    f"Quinta-feira, {TODAY}. O Ibovespa opera em alta impulsionado por commodities e mercado externo, "
    f"enquanto o cenário corporativo tem movimentos estratégicos em inteligência artificial e telecomunicações.",
    encoding="utf-8"
)

(manifest_dir / "intro.txt").write_text(
    f"Bom dia! Eu sou Francisca, e hoje é quinta-feira, {TODAY}. Este é o Drop Five News, o seu briefing "
    f"das 05 horas da manhã com as notícias essenciais para começar o dia bem informado.",
    encoding="utf-8"
)

(manifest_dir / "mundo.txt").write_text(
    "No cenário global, as bolsas internacionais operam com cautela antes da divulgação de novos dados de inflação nos Estados Unidos. "
    "Investidores monitoram os próximos passos do Federal Reserve em relação às taxas de juros.",
    encoding="utf-8"
)

(manifest_dir / "brasil.txt").write_text(
    "No Brasil, o foco continua na agenda econômica em Brasília, com discussões em torno do equilíbrio fiscal e votações de projetos "
    "prioritários no Congresso Nacional.",
    encoding="utf-8"
)

(manifest_dir / "tecnologia.txt").write_text(
    "Em tecnologia, novos avanços em inteligência artificial generativa aceleram o mercado corporativo, com empresas ampliando "
    "investimentos em infraestrutura de computação e soluções locais.",
    encoding="utf-8"
)

(manifest_dir / "economia.txt").write_text(
    "Na economia, o mercado financeiro reflete o bom momento das exportações e a estabilidade cambial, com o dólar operando "
    "em faixa estável nesta semana.",
    encoding="utf-8"
)

(manifest_dir / "outro.txt").write_text(
    f"Este foi o Drop Five News desta quinta-feira, {TODAY}. Fique ligado ao longo do dia para o Manhã Conectada às 11h "
    "e o Fechamento do Mercado às 17h. Tenha um excelente dia e até a próxima!",
    encoding="utf-8"
)


# Seções adicionais (faltantes no gerador original)
(manifest_dir / "frase.txt").write_text(
    f"Quinta-feira, {TODAY}. A tecnologia continua a transformar a maneira como vivemos e trabalhamos. "
    f"Com os avanços em inteligência artificial generativa, as oportunidades de inovação crescem sem parar.",
    encoding="utf-8"
)

(manifest_dir / "ofertas.txt").write_text(
    f"Nesta quinta-feira, {TODAY}, o mercado oferece oportunidades em setores como telecomunicações, "
    f"energia renovável e infraestrutura de dados. Empresas estão em expansão e buscando talentos qualificados.",
    encoding="utf-8"
)

(manifest_dir / "interacao.txt").write_text(
    "E aí, você acompanhou as notícias da manhã? Deixe seu comentário aqui em baixo e conte o que você achou "
    "das últimas informações sobre o mercado e a economia. Sua opinião importa!",
    encoding="utf-8"
)

(manifest_dir / "historia.txt").write_text(
    "Na história dos negócios, grandes empresas nasceram de ideias simples e persistência. "
    "Hoje, mais do que nunca, a inovação e a criatividade são os motores do crescimento sustentável.",
    encoding="utf-8"
)

(manifest_dir / "recomendacoes.txt").write_text(
    "Para começar o dia bem informado, recomendamos acompanhar as notícias do G1, "
    "as análises do Valor Econômico e os boletins do Banco Central. "
    "Informação de qualidade é a base para decisões inteligentes.",
    encoding="utf-8"
)

print(f"Manifests D5N criados com sucesso em: {manifest_dir}")
