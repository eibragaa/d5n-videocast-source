#!/usr/bin/env python3
"""
gerar_cards_instagram_d5n.py — Gera cards visuais para Instagram do DropFiveNews.

Produz:
  • Story (9:16, 1080×1920) — card hero para Stories/Reels
  • Post quadrado (1:1, 1080×1080) — resumo do dia com categorias
  • Cards individuais por notícia (1080×1080) — para carrossel
  • Opcional: animação via Google Veo 3 (image→video)

Uso:
  python3 gerar_cards_instagram_d5n.py
  python3 gerar_cards_instagram_d5n.py --data 2026-06-01
  python3 gerar_cards_instagram_d5n.py --veo-api-key KEY  # ativa Veo 3
  python3 gerar_cards_instagram_d5n.py --listar
"""

import os, sys, re, json, argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ── CONFIGURAÇÃO ──
REPO = "/root/repositorio/d5n-videocast-source"
ARQUIVO_DIR = f"{REPO}/2026"
OUTPUT_DIR = f"{REPO}/cards-instagram"
SOURCE_FILE = f"{REPO}/source.md"

# Dimensões Instagram
STORY_W, STORY_H = 1080, 1920   # 9:16 Stories/Reels
POST_W, POST_H = 1080, 1080     # 1:1 Feed / Carrossel

# Paleta D5N (exata do site)
BG = (13, 17, 23)          # #0d1117
SURFACE = (19, 25, 32)     # #131920
BORDER = (30, 39, 51)      # #1e2733
TEXT = (226, 232, 240)     # #e2e8f0
MUTED = (100, 116, 139)    # #64748b
ACCENT = (148, 163, 184)   # #94a3b8
ACCENT_DIM = (51, 65, 85)  # #334155
GLOBAL_C = (109, 184, 138) # #6db88a
TECH_C = (96, 165, 212)    # #60a5d4
ECON_C = (168, 144, 96)    # #a89060
FAINT = (30, 45, 61)       # #1e2d3d

PILAR_CORES = {
    'Global': GLOBAL_C, 'Brasil': GLOBAL_C,
    'Tech': TECH_C,
    'Economia': ECON_C, 'Econ': ECON_C,
}

PILAR_EMOJI = {
    'Global': '🌍', 'Brasil': '🇧🇷',
    'Tech': '💻', 'Economia': '📈',
}


def log(msg):
    print(f"  {msg}")


def carregar_noticias(source_path=None, data_str=None):
    """Carrega notícias de source.md ou arquivo de data específica."""
    noticias = []
    source = source_path or SOURCE_FILE

    # source.md (curado) é o padrão; data específica só se explicitamente requisitada
    if source_path:
        source = source_path
    if not source_path and data_str:
        # Tenta arquivo de data, se existir e tiver conteúdo limpo
        dated_path = f"{ARQUIVO_DIR}/{data_str}.md"
        if os.path.exists(dated_path):
            # Verifica se é o arquivo limpo (contém ### seções) ou raw trends
            with open(dated_path) as f_check:
                first_lines = f_check.read(500)
            if '###' in first_lines or 'INSTRUÇÕES' in first_lines:
                source = dated_path
                log(f"📄 Lendo {source}")
            else:
                # É raw trends — melhor usar source.md
                log(f"ℹ️ {data_str}.md é raw trends — usando source.md (curado)")

    if not os.path.exists(source):
        log(f"❌ Arquivo não encontrado: {source}")
        return [], ""

    with open(source, encoding='utf-8') as f:
        content = f.read()

    # Extrair data
    data_match = re.search(r'(\d+ de \w+ de \d{4})', content)
    data_br = data_match.group(1) if data_match else datetime.now().strftime("%d de %B de %Y")

    # Pilar atual
    pilar_atual = ''
    pilar_map = {
        'GLOBAL': 'Global', 'BRASIL': 'Brasil', 'GLOBAL & BRASIL': 'Global',
        'TECH': 'Tech', 'TECH & IA': 'Tech',
        'ECONOMIA': 'Economia', 'ECONOMIA & MERCADOS': 'Economia',
        'ECONOMIA & CRYPTO': 'Economia', 'CRYPTO': 'Economia',
    }

    # Mapa para extrair pilar de headings como ## [Tech] título
    pilar_from_bracket = {
        'GLOBAL': 'Global', 'BRASIL': 'Brasil',
        'TECH': 'Tech', 'ECONOMIA': 'Economia', 'ECON': 'Economia',
        'CRYPTO': 'Economia',
    }

    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()

        # Detecta seção de pilar: ### Nome
        h3 = re.match(r'^###\s+(.+)$', stripped)
        if h3:
            sec = h3.group(1).strip()
            sec_clean = re.sub(r'[\U0001F300-\U0001FFFF\U00002000-\U00002BFF]', '', sec).strip()
            for k, v in pilar_map.items():
                if k in sec_clean.upper():
                    pilar_atual = v
                    break
            continue

        # Detecta heading de notícia: ## [Pilar] Título
        h2 = re.match(r'^##\s+\[([^\]]+)\]\s+(.+)$', stripped)
        if h2:
            pilar_key = h2.group(1).strip().upper()
            titulo = h2.group(2).strip()[:150]
            pilar = pilar_from_bracket.get(pilar_key, 'Global')
            if titulo and 'coleta completa' not in titulo.lower() and len(titulo) > 10:
                noticias.append({
                    'pilar': pilar,
                    'titulo': titulo,
                    'fonte': 'D5N',
                    'numero': len(noticias) + 1,
                })
            continue

        # Detecta notícia numerada: 1. Título
        m = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if m:
            titulo = m.group(2).strip()[:150]
            if titulo and not titulo.startswith('INSTRUÇÕES') and not titulo.startswith('NÃO'):
                noticias.append({
                    'pilar': pilar_atual or 'Global',
                    'titulo': titulo,
                    'fonte': 'D5N',
                    'numero': len(noticias) + 1,
                })

    log(f"📰 {len(noticias)} notícias carregadas de {os.path.basename(source)}")
    return noticias, data_br


# Fontes D5N (Google Fonts)
_FONT_DIR = "/usr/local/share/fonts/d5n"
_FONT_LB = f"{_FONT_DIR}/LibreBaskerville[wght].ttf"   # Libre Baskerville
_FONT_DM = f"{_FONT_DIR}/DMSans[opsz,wght].ttf"         # DM Sans


def carregar_fonte(tamanho, bold=False, serif=False):
    """Carrega fonte: Libre Baskerville (serif) ou DM Sans (sans)."""
    if serif and os.path.exists(_FONT_LB):
        try:
            return ImageFont.truetype(_FONT_LB, tamanho)
        except Exception:
            pass
    if not serif and os.path.exists(_FONT_DM):
        try:
            return ImageFont.truetype(_FONT_DM, tamanho)
        except Exception:
            pass

    # Fallback system fonts
    fontes_serif = [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "",
    ]
    fontes_sans = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "",
    ]

    candidates = fontes_serif if serif else fontes_sans
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, tamanho)
            except Exception:
                continue
    return ImageFont.load_default()


def desenhar_bg(img, cor_bg=BG):
    """Preenche fundo."""
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), img.size], fill=cor_bg)


def desenhar_borda_sutil(img, draw, cor=BORDER):
    """Adiciona borda fina ao redor."""
    w, h = img.size
    for i in range(1):
        draw.rectangle([(i, i), (w-1-i, h-1-i)], outline=cor, width=1)


def desenhar_linha_horizontal(draw, x1, y, x2, cor, grossura=1):
    draw.line([(x1, y), (x2, y)], fill=cor, width=grossura)


def desenhar_texto_centralizado(draw, texto, y, fonte, cor=TEXT, max_w=None, espacamento=50):
    """Desenha texto centralizado horizontalmente."""
    if max_w and fonte.getbbox(texto):
        # Wrap se necessário
        avg_char_w = fonte.getbbox("A")[2] - fonte.getbbox("A")[0]
        if avg_char_w * len(texto) > max_w:
            chars_por_linha = max_w // avg_char_w
            linhas = textwrap.wrap(texto, width=chars_por_linha)
            y_atual = y
            for linha in linhas:
                bbox = fonte.getbbox(linha)
                tw = bbox[2] - bbox[0]
                x = (STORY_W - tw) // 2
                draw.text((x, y_atual), linha, fill=cor, font=fonte)
                y_atual += espacamento
            return y_atual
    bbox = fonte.getbbox(texto)
    tw = bbox[2] - bbox[0]
    x = (STORY_W - tw) // 2
    draw.text((x, y), texto, fill=cor, font=fonte)
    return y + espacamento


# ═══════════════════════════════════════════════
#  GERADORES DE CARDS
# ═══════════════════════════════════════════════

def gerar_card_story(noticias, data_br, output_path):
    """Gera Story 9:16 — hero branding + notícia principal."""
    font_titulo = carregar_fonte(72, bold=True, serif=True)
    font_sub = carregar_fonte(36, serif=True)
    font_data = carregar_fonte(28)
    font_noticia = carregar_fonte(44, bold=True)
    font_pilar = carregar_fonte(24)
    font_tag = carregar_fonte(20)

    img = Image.new('RGB', (STORY_W, STORY_H), BG)
    draw = ImageDraw.Draw(img)
    desenhar_borda_sutil(img, draw)

    # ── Top: logo ──
    font_logo = carregar_fonte(48, bold=True, serif=True)
    draw.text((60, 60), "drop", fill=TEXT, font=font_logo)
    # five italic (simulado com font serif)
    font_logo_i = carregar_fonte(48, serif=True)
    draw.text((60 + (font_logo.getbbox("drop")[2] - font_logo.getbbox("drop")[0]), 60),
              "five", fill=ACCENT, font=font_logo_i)
    font_logo_b = carregar_fonte(48, bold=True, serif=True)
    fw = font_logo_b.getbbox("five")[2] - font_logo_b.getbbox("five")[0]
    draw.text((60 + (font_logo.getbbox("drop")[2] - font_logo.getbbox("drop")[0]) +
               (font_logo_i.getbbox("five")[2] - font_logo_i.getbbox("five")[0]), 60),
              "news", fill=TEXT, font=font_logo_b)

    # ── Data ──
    font_data = carregar_fonte(26)
    draw.text((60, 60 + 58), data_br.upper(), fill=MUTED, font=font_data)

    # ── Tag curadoria ──
    tag_y = 60 + 58 + 45
    tag_text = "CURADORIA DIÁRIA · IA"
    draw.text((60, tag_y), tag_text, fill=ACCENT, font=font_tag)

    # ── Linha decorativa ──
    desenhar_linha_horizontal(draw, 60, tag_y + 35, 1080 - 60, ACCENT_DIM, 1)

    # ── Notícia principal (destaque) ──
    if noticias:
        principal = noticias[0]
        pilar = principal['pilar']
        cor_pilar = PILAR_CORES.get(pilar, GLOBAL_C)
        emoji = PILAR_EMOJI.get(pilar, '📰')

        # Badge pilar
        badge_y = tag_y + 70
        badge_text = f"{emoji}  {pilar.upper()}"
        draw.text((60, badge_y), badge_text, fill=cor_pilar, font=font_pilar)

        # Notícia título (wrap manual)
        titulo = principal['titulo']
        font_n = carregar_fonte(52, bold=True)
        chars_por_linha = 28
        linhas = textwrap.wrap(titulo, width=chars_por_linha)
        y_atual = badge_y + 60
        for linha in linhas[:4]:  # max 4 linhas
            draw.text((60, y_atual), linha, fill=TEXT, font=font_n)
            y_atual += 62

        # Número outras notícias
        restante = len(noticias) - 1
        if restante > 0:
            y_atual += 40
            font_meta = carregar_fonte(28)
            draw.text((60, y_atual),
                      f"+ {restante} notícias em {len(set(n['pilar'] for n in noticias))} pilares",
                      fill=MUTED, font=font_meta)

    # ── Bottom: CTA Instagram ──
    desenhar_linha_horizontal(draw, 60, STORY_H - 120, STORY_W - 60, ACCENT_DIM, 1)
    font_cta = carregar_fonte(24)
    draw.text((60, STORY_H - 100), "Siga @dropfivenews", fill=ACCENT, font=font_cta)

    # ── Bolinhas de pilar no canto inferior direito ──
    dot_y = STORY_H - 100
    dot_x = STORY_W - 60 - 12
    for pilar in ['Global', 'Tech', 'Economia']:
        cor = PILAR_CORES.get(pilar, GLOBAL_C)
        draw.ellipse([(dot_x, dot_y), (dot_x + 8, dot_y + 8)], fill=cor)
        dot_x -= 18

    img.save(output_path, quality=95)
    log(f"✅ Story: {output_path}")


def gerar_card_post_resumo(noticias, data_br, output_path):
    """Gera Post 1:1 — resumo visual do dia com categorias."""
    img = Image.new('RGB', (POST_W, POST_H), BG)
    draw = ImageDraw.Draw(img)
    desenhar_borda_sutil(img, draw)

    font_logo = carregar_fonte(36, bold=True, serif=True)
    font_data = carregar_fonte(22)
    font_titulo = carregar_fonte(32, bold=True)
    font_categoria = carregar_fonte(20, bold=True)
    font_noticia = carregar_fonte(22)
    font_num = carregar_fonte(18, serif=True)
    font_rodape = carregar_fonte(18)

    # ── Header ──
    draw.text((50, 40), "dropfive", fill=TEXT, font=font_logo)
    draw.text((50, 85), data_br.upper(), fill=MUTED, font=font_data)

    # Linha
    desenhar_linha_horizontal(draw, 50, 120, POST_W - 50, BORDER, 1)

    # ── Notícias por pilar ──
    pilares_ordem = ['Global', 'Tech', 'Economia']
    noticias_por_pilar = {}
    for n in noticias:
        noticias_por_pilar.setdefault(n['pilar'], []).append(n)

    y_atual = 145
    for pilar in pilares_ordem:
        lista = noticias_por_pilar.get(pilar, [])
        if not lista:
            # Tenta match parcial (Brasil → Global)
            for k, v in noticias_por_pilar.items():
                if pilar in k or k in pilar:
                    lista = v
                    break
        if not lista:
            continue

        cor = PILAR_CORES.get(pilar, GLOBAL_C)
        emoji = PILAR_EMOJI.get(pilar, '📰')

        # Cabeçalho da categoria
        draw.text((50, y_atual), f"{emoji}  {pilar.upper()}", fill=cor, font=font_categoria)
        y_atual += 35

        for ntc in lista[:3]:  # max 3 por pilar
            num = f"{ntc['numero']:02d}"
            titulo = ntc['titulo']

            # Número
            draw.text((50, y_atual), num, fill=FAINT, font=font_num)

            # Título (wrap)
            chars_por_linha = 35
            linhas = textwrap.wrap(titulo, width=chars_por_linha)
            x_titulo = 85
            for i, linha in enumerate(linhas[:2]):
                draw.text((x_titulo, y_atual + i * 28), linha, fill=TEXT, font=font_noticia)
            y_atual += max(len(linhas) * 28 + 8, 32)

        y_atual += 10

    # ── Rodapé ──
    desenhar_linha_horizontal(draw, 50, POST_H - 70, POST_W - 50, BORDER, 1)
    draw.text((50, POST_H - 55), f"{len(noticias)} notícias · dropfivenews", fill=MUTED, font=font_rodape)

    # Bolinhas
    dot_x = POST_W - 50 - 12
    for p in ['Global', 'Tech', 'Economia']:
        cor = PILAR_CORES.get(p, GLOBAL_C)
        draw.ellipse([(dot_x, POST_H - 65), (dot_x + 8, POST_H - 57)], fill=cor)
        dot_x -= 18

    img.save(output_path, quality=95)
    log(f"✅ Post resumo: {output_path}")


def gerar_cards_carrossel(noticias, data_br, output_dir):
    """Gera slides individuais 1:1 para carrossel do Instagram."""
    os.makedirs(output_dir, exist_ok=True)

    for i, ntc in enumerate(noticias[:10]):  # max 10 slides
        pilar = ntc['pilar']
        cor_pilar = PILAR_CORES.get(pilar, GLOBAL_C)
        emoji = PILAR_EMOJI.get(pilar, '📰')

        img = Image.new('RGB', (POST_W, POST_H), BG)
        draw = ImageDraw.Draw(img)
        desenhar_borda_sutil(img, draw)

        font_num = carregar_fonte(100, bold=True, serif=True)
        font_pilar = carregar_fonte(24, bold=True)
        font_titulo = carregar_fonte(48, bold=True)
        font_data = carregar_fonte(20)
        font_fonte = carregar_fonte(20)

        # ── Número grande decorativo ──
        num = f"{ntc['numero']:02d}"
        draw.text((POST_W - 130, 30), num, fill=FAINT, font=font_num)

        # ── Data + Logo ──
        draw.text((50, 45), "dropfivenews", fill=MUTED, font=font_data)

        # ── Pilar badge ──
        draw.text((50, 85), f"{emoji}  {pilar.upper()}", fill=cor_pilar, font=font_pilar)

        # ── Título ──
        titulo = ntc['titulo']
        chars_por_linha = 25
        linhas = textwrap.wrap(titulo, width=chars_por_linha)
        y_titulo = 170
        for linha in linhas[:5]:
            draw.text((50, y_titulo), linha, fill=TEXT, font=font_titulo)
            y_titulo += 58

        # ── Fonte ──
        draw.text((50, POST_H - 80), f"Fonte: {ntc.get('fonte', 'D5N')}", fill=MUTED, font=font_fonte)

        # ── Bolinhas inferiores ──
        dot_x = POST_W - 50 - 12
        for p in ['Global', 'Tech', 'Economia']:
            cor = PILAR_CORES.get(p, GLOBAL_C)
            draw.ellipse([(dot_x, POST_H - 85), (dot_x + 8, POST_H - 77)], fill=cor)
            dot_x -= 18

        # Navegação (slide X de Y)
        font_nav = carregar_fonte(18)
        nav = f"{i+1}/{min(len(noticias), 10)}"
        draw.text((50, POST_H - 50), nav, fill=ACCENT_DIM, font=font_nav)

        path = f"{output_dir}/slide_{i+1:02d}.png"
        img.save(path, quality=95)
        log(f"  🎴 Slide {i+1}: {path}")


def gerar_card_pilar_destaque(noticias, data_br, output_dir):
    """Gera um card de destaque por pilar (formato post)."""
    os.makedirs(output_dir, exist_ok=True)

    pilares_ordem = ['Global', 'Tech', 'Economia']
    noticias_por_pilar = {}
    for n in noticias:
        noticias_por_pilar.setdefault(n['pilar'], []).append(n)

    for pilar in pilares_ordem:
        lista = noticias_por_pilar.get(pilar, [])
        if not lista:
            continue

        cor = PILAR_CORES.get(pilar, GLOBAL_C)
        emoji = PILAR_EMOJI.get(pilar, '📰')

        img = Image.new('RGB', (POST_W, POST_H), BG)
        draw = ImageDraw.Draw(img)
        desenhar_borda_sutil(img, draw)

        font_pilar = carregar_fonte(100)
        font_nome = carregar_fonte(40, bold=True)
        font_count = carregar_fonte(28)
        font_noticia = carregar_fonte(24)

        # ── Emoji grande decorativo ──
        draw.text((50, 80), emoji, fill=cor, font=font_pilar)

        # ── Nome pilar ──
        draw.text((50, 220), pilar.upper(), fill=cor, font=font_nome)

        # ── Contagem ──
        draw.text((50, 275), f"{len(lista)} notícias", fill=MUTED, font=font_count)

        # ── Linha ──
        desenhar_linha_horizontal(draw, 50, 320, POST_W - 50, cor, 1)

        # ── Notícias do pilar ──
        y_atual = 350
        for ntc in lista[:5]:
            titulo = ntc['titulo']
            chars_por_linha = 35
            linhas = textwrap.wrap(titulo, width=chars_por_linha)
            for linha in linhas:
                draw.text((50, y_atual), linha, fill=TEXT, font=font_noticia)
                y_atual += 30
            y_atual += 8

        # ── Rodapé ──
        draw.text((50, POST_H - 60), f"dropfivenews · {data_br}", fill=MUTED, font=carregar_fonte(18))

        path = f"{output_dir}/pilar_{pilar.lower()}.png"
        img.save(path, quality=95)
        log(f"  🏷️ Card pilar '{pilar}': {path}")


# ═══════════════════════════════════════════════
#  VEO 3 — ANIMAÇÃO DE CARDS
# ═══════════════════════════════════════════════

def animar_card_com_veo(image_path, api_key=None, modelo="veo-3.0-generate"):
    """Usa Google Veo 3 para gerar vídeo curto a partir de card estático.

    Requer google-genai e chave de API do Gemini ou Vertex AI.
    """
    if not api_key:
        log("  ⏭️ Sem API key Veo 3 — pulando animação")
        return None

    try:
        import google.genai as genai
    except ImportError:
        log("  ❌ google-genai não instalado. pip install google-genai")
        return None

    client = genai.Client(api_key=api_key)

    # Upload da imagem base
    with open(image_path, 'rb') as f:
        image_data = f.read()

    # Prompt para Veo 3
    prompt = (
        "Anime este card de notícias com movimento sutil e elegante. "
        "Mantenha o texto legível. Adicione um leve brilho animado no texto principal. "
        "Use transição suave, zoom-in muito leve (1.02x). "
        "Estilo: dark mode, sério, profissional, noticiário."
    )

    log(f"  🎬 Enviando para Veo 3: {os.path.basename(image_path)}...")

    try:
        # API Veo 3 — image-to-video
        response = client.models.generate(
            model=modelo,
            contents=[prompt, image_data],
            config={
                "mime_type": "image/png",
                "aspect_ratio": "9:16" if "story" in image_path else "1:1",
                "duration_seconds": 6,
            }
        )

        video_path = image_path.replace('.png', '_veo3.mp4')
        if hasattr(response, 'data') and response.data:
            with open(video_path, 'wb') as f:
                f.write(response.data)
            log(f"  ✅ Vídeo Veo 3 gerado: {video_path}")
            return video_path
        else:
            log(f"  ⚠️ Resposta sem dados de vídeo: {response}")
            return None

    except Exception as e:
        log(f"  ❌ Erro Veo 3: {e}")
        return None


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════

def listar_datas_disponiveis():
    """Lista datas com arquivos .md disponíveis."""
    datas = []
    if os.path.isdir(ARQUIVO_DIR):
        for f in sorted(os.listdir(ARQUIVO_DIR)):
            if f.endswith('.md'):
                datas.append(f.replace('.md', ''))
    return datas


def main():
    parser = argparse.ArgumentParser(
        description='Gera cards Instagram para DropFiveNews',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 gerar_cards_instagram_d5n.py
  python3 gerar_cards_instagram_d5n.py --data 2026-06-01
  python3 gerar_cards_instagram_d5n.py --veo-api-key $API_KEY
  python3 gerar_cards_instagram_d5n.py --listar
  python3 gerar_cards_instagram_d5n.py --apenas-story
  python3 gerar_cards_instagram_d5n.py --apenas-carrossel
        """
    )
    parser.add_argument('--data', help='Data específica (YYYY-MM-DD)')
    parser.add_argument('--source', default=None, help='Arquivo .md específico (default: source.md)')
    parser.add_argument('--veo-api-key', help='Chave da API Google Gemini/Vertex para Veo 3')
    parser.add_argument('--listar', action='store_true', help='Listar datas disponíveis')
    parser.add_argument('--apenas-story', action='store_true', help='Apenas card Story')
    parser.add_argument('--apenas-post', action='store_true', help='Apenas card Post resumo')
    parser.add_argument('--apenas-carrossel', action='store_true', help='Apenas slides carrossel')
    parser.add_argument('--apenas-pilares', action='store_true', help='Apenas cards de pilar')
    parser.add_argument('--veo-animar', action='store_true', help='Animar cards com Veo 3')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Diretório de saída')
    args = parser.parse_args()

    # Listar
    if args.listar:
        datas = listar_datas_disponiveis()
        print(f"\n📅 Datas disponíveis ({len(datas)}):")
        for d in datas:
            print(f"  • {d}")
        print()
        return

    # Data
    data_str = args.data or datetime.now().strftime("%Y-%m-%d")
    data_br = ""

    # Carregar notícias (source.md é o padrão por ter dados curados)
    noticias, data_br = carregar_noticias(source_path=args.source, data_str=data_str)
    if not noticias:
        print(f"\n❌ Nenhuma notícia encontrada para {data_str}")

        # Fallback: tenta o source.md
        noticias, data_br = carregar_noticias(source_path=SOURCE_FILE)
        if not noticias:
            print("❌ Também sem source.md disponível.")
            sys.exit(1)
        log(f"ℹ️ Usando source.md (fallback)")

    print(f"\n╔══ D5N — Cards Instagram ══╗")
    print(f"║  Data: {data_br}")
    print(f"║  Notícias: {len(noticias)}")
    print(f"║  Pilares: {len(set(n['pilar'] for n in noticias))}")
    print(f"╚════════════════════════════╝\n")

    # Diretório de saída
    dated_dir = f"{args.output}/{data_str}"
    os.makedirs(dated_dir, exist_ok=True)
    log(f"📁 Saída: {dated_dir}/\n")

    # ── Gerar cards ──
    todos_os_cards = []

    if not args.apenas_post and not args.apenas_carrossel and not args.apenas_pilares:
        # Story (sempre, a menos que filtrando)
        story_path = f"{dated_dir}/story_{data_str}.png"
        gerar_card_story(noticias, data_br, story_path)
        todos_os_cards.append(story_path)

    if not args.apenas_story and not args.apenas_carrossel and not args.apenas_pilares:
        # Post resumo
        post_path = f"{dated_dir}/post_resumo_{data_str}.png"
        gerar_card_post_resumo(noticias, data_br, post_path)
        todos_os_cards.append(post_path)

    if not args.apenas_story and not args.apenas_post and not args.apenas_pilares:
        # Carrossel
        carrossel_dir = f"{dated_dir}/carrossel"
        gerar_cards_carrossel(noticias, data_br, carrossel_dir)
        for f in sorted(os.listdir(carrossel_dir)):
            todos_os_cards.append(f"{carrossel_dir}/{f}")

    if not args.apenas_story and not args.apenas_post and not args.apenas_carrossel:
        # Cards de pilar
        pilares_dir = f"{dated_dir}/pilares"
        gerar_card_pilar_destaque(noticias, data_br, pilares_dir)
        for f in sorted(os.listdir(pilares_dir)):
            todos_os_cards.append(f"{pilares_dir}/{f}")

    # ── Resumo ──
    print(f"\n📊 Resumo: {len(todos_os_cards)} cards gerados")
    for card in todos_os_cards:
        size = os.path.getsize(card)
        print(f"  • {os.path.basename(card)} — {size // 1024}KB")

    # ── Veo 3 animação ──
    if args.veo_animar and args.veo_api_key:
        print(f"\n🎬 Animando com Veo 3...")
        for card_path in todos_os_cards[:3]:  # Limite de 3 por execução
            if card_path.endswith('.png'):
                animar_card_com_veo(card_path, api_key=args.veo_api_key)
    elif args.veo_animar and not args.veo_api_key:
        print(f"\n⚠️ --veo-animar requer --veo-api-key KEY")

    # ── Atalhos ──
    print(f"\n📌 Para postar no Instagram:")
    print(f"  Story:     {dated_dir}/story_{data_str}.png")
    print(f"  Post:      {dated_dir}/post_resumo_{data_str}.png")
    print(f"  Carrossel: {dated_dir}/carrossel/")
    print(f"  Pilares:   {dated_dir}/pilares/")
    print()


if __name__ == '__main__':
    main()
