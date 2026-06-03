#!/usr/bin/env python3
"""
gerar_cards_pipeline.py — Pipeline D5N de cards para Instagram.

FLUXO:
  1. Lê notícias
  2. Para CADA notícia:
     a. Busca imagem REAL (múltiplas fontes, SEMPRE encontra)
     b. Gera resumo (3 linhas) com Gemini
     c. Gera hook de engajamento
     d. Cria card com overlay completo: headline + resumo + link + hook
  3. Gera card resumo do dia

Uso:
  python3 gerar_cards_pipeline.py
  python3 gerar_cards_pipeline.py --data 2026-06-01
  python3 gerar_cards_pipeline.py --listar

Documentação completa: CARDS_INSTAGRAM.md

Cron (recomendado):
  0 8 * * * cd /root/repositorio/d5n-videocast-source && python3 gerar_cards_pipeline.py

NOTA: A busca de imagens (Bing) nem sempre encontra foto relevante.
      Ideal: usar Imagen 4.0 ou fontes jornalísticas quando disponível.
      Cards são salvos mesmo assim para referência visual.
"""

import os, sys, re, json, textwrap, time, argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests

# ════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════

REPO = "/root/repositorio/d5n-videocast-source"
ARQUIVO_DIR = f"{REPO}/2026"
OUTPUT_DIR = f"{REPO}/cards-instagram"
SOURCE_FILE = f"{REPO}/source.md"
FEED_FILE = f"{REPO}/feed.json"
FONT_DM = "/usr/local/share/fonts/d5n/DMSans[opsz,wght].ttf"

W, H = 1080, 1350  # 4:5
API_KEY = os.getenv("GCP_API_KEY", "")
SITE_URL = "https://d5n-daily.netlify.app/"
LEO_KEY = os.getenv("LEO_KEY", "")

CATEGORIAS = {
    "Global":    {"cor":(25,100,185),"claro":(80,175,240),"escuro":(10,50,100),"badge":"MUNDO","icone":"🌍"},
    "Tech":      {"cor":(25,155,210),"claro":(90,210,250),"escuro":(15,70,110),"badge":"TECH","icone":"💻"},
    "Economia":  {"cor":(210,170,50),"claro":(250,210,100),"escuro":(100,80,20),"badge":"ECONOMIA","icone":"📈"},
    "Política":  {"cor":(185,45,45),"claro":(235,95,95),"escuro":(100,20,20),"badge":"POLÍTICA","icone":"🏛️"},
    "Brasil":    {"cor":(25,155,75),"claro":(75,205,125),"escuro":(10,80,35),"badge":"BRASIL","icone":"🇧🇷"},
}

CAT_ALIAS = {"global":"Global","brasil":"Brasil","mundo":"Global","tech":"Tech","tecnologia":"Tech",
             "econ":"Economia","economia":"Economia","crypto":"Economia","politica":"Política","política":"Política"}

# Hooks de engajamento para Instagram (variados por categoria)
HOOKS = {
    "Global": ["Isso muda o que você pensa sobre o mundo?", "O que você faria nessa situação?", 
               "Compartilhe com quem precisa saber 🌍", "Sua opinião sobre isso? 👇"],
    "Tech":   ["A tecnologia está mudando tudo 🚀", "Isso vai impactar sua vida digital",
               "Você sabia disso? 👆", "O futuro chegou — e você precisa saber"],
    "Economia": ["Seu bolso vai sentir isso 📊", "Fique de olho nessa informação",
                 "Isso impacta seus investimentos", "Economia não é sorte — é informação"],
    "Política": ["Isso afeta sua vida diretamente", "Você já sabia dessa?",
                 "Política não é só debate — é impacto real", "Sua opinião? 💬"],
    "Brasil": ["Isso acontece no Brasil e você precisa saber", "Compartilhe com os amigos 🇧🇷",
               "Fique por dentro do que importa", "Sua voz faz diferença"],
}

# ════════════════════════════════════════════════
#  UTILITÁRIOS
# ════════════════════════════════════════════════

def log(msg):
    print(f"  {msg}")

def get_font(size, weight=700):
    font = ImageFont.truetype(FONT_DM, size)
    try: font.set_variation_by_axes([9, weight])
    except: pass
    return font

def mapear_cat(p):
    return CAT_ALIAS.get(p.strip().lower() if p else "", "Global")

def extrair_data_br(data_str=None):
    if data_str:
        try:
            d = datetime.strptime(data_str, "%Y-%m-%d")
            meses = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                     "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
            dias = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
            return f"{dias[d.weekday()]}, {d.day} de {meses[d.month]} de {d.year}"
        except: pass
    return datetime.now().strftime("%d de %B de %Y")

def data_curta(data_br):
    meses = {"Janeiro":"JAN","Fevereiro":"FEV","Março":"MAR","Abril":"ABR","Maio":"MAI","Junho":"JUN",
             "Julho":"JUL","Agosto":"AGO","Setembro":"SET","Outubro":"OUT","Novembro":"NOV","Dezembro":"DEZ"}
    for k,v in meses.items():
        if k in data_br:
            nums = re.findall(r'\d+', data_br)
            if nums: return f"{nums[0]} {v} {nums[1] if len(nums)>1 else '2026'}"
    return "1 JUN 2026"

def escolher_hook(categoria):
    """Escolhe hook aleatório para a categoria."""
    import random
    hooks = HOOKS.get(categoria, HOOKS["Global"])
    return random.choice(hooks)


# ════════════════════════════════════════════════
#  1. CARREGAR NOTÍCIAS
# ════════════════════════════════════════════════

def carregar_noticias(data_str=None):
    noticias = []; data_br = ""

    if os.path.exists(FEED_FILE):
        try:
            with open(FEED_FILE) as f:
                feed = json.load(f)
            for item in feed.get("items", []):
                content = item.get("content_text", "")
                t = item.get("title","")
                dm = re.search(r'(\d+ de \w+ de \d{4})', t)
                data_br = dm.group(1) if dm else ""
                for line in content.split("\n"):
                    m = re.match(r'^\[(\w+)\]\s+(.+)$', line.strip())
                    if m:
                        noticias.append({"pilar":mapear_cat(m.group(1)),"titulo":m.group(2).strip()[:150],
                                         "fonte":"D5N","numero":len(noticias)+1})
                if noticias: break
            if noticias:
                log(f"📰 {len(noticias)} notícias (feed.json)")
                return noticias, data_br or extrair_data_br(data_str)
        except: pass

    fsp = SOURCE_FILE
    if data_str:
        dp = f"{ARQUIVO_DIR}/{data_str}.md"
        if os.path.exists(dp):
            with open(dp) as f:
                c = f.read()
            if "INSTRUÇÕES" in c or "###" in c:
                fsp = dp

    if not os.path.exists(fsp):
        log(f"❌ Sem arquivo: {fsp}"); return [], ""

    with open(fsp) as f:
        content = f.read()
    data_br = data_br or extrair_data_br(data_str) or (
        re.search(r'(\d+ de \w+ de \d{4})', content).group(1) if re.search(r'(\d+ de \w+ de \d{4})', content) else "")

    pilar_atual = "Global"
    pmap = {'GLOBAL':'Global','BRASIL':'Brasil','GLOBAL & BRASIL':'Global',
            'TECH':'Tech','TECH & IA':'Tech','ECONOMIA':'Economia',
            'ECONOMIA & MERCADOS':'Economia','ECONOMIA & CRYPTO':'Economia',
            'POLÍTICA':'Política','POLITICA':'Política'}

    for line in content.split("\n"):
        s = line.strip()
        h3 = re.match(r'^###\s+(.+)$', s)
        if h3:
            sec = re.sub(r'[\U0001F300-\U0001FFFF]', '', h3.group(1)).strip()
            for k,v in pmap.items():
                if k in sec.upper(): pilar_atual = v; break
            continue
        h2 = re.match(r'^##\s+\[([^\]]+)\]\s+(.+)$', s)
        if h2:
            titulo = h2.group(2).strip()[:150]
            if titulo and len(titulo) > 10 and "coleta" not in titulo.lower():
                noticias.append({"pilar":mapear_cat(h2.group(1)),"titulo":titulo,"fonte":"D5N","numero":len(noticias)+1})
            continue
        nm = re.match(r'^(\d+)\.\s+(.+)$', s)
        if nm:
            titulo = nm.group(2).strip()[:150]
            if titulo and not titulo.startswith("INSTRUÇÕES") and not titulo.startswith("NÃO"):
                noticias.append({"pilar":pilar_atual,"titulo":titulo,"fonte":"D5N","numero":len(noticias)+1})

    log(f"📰 {len(noticias)} notícias ({os.path.basename(fsp)})")
    return noticias, data_br


# ════════════════════════════════════════════════
#  2. BUSCAR IMAGEM (SEMPRE encontra)
# ════════════════════════════════════════════════

def buscar_imagem(titulo, categoria="Global"):
    """
    Gera imagem de fundo via Leonardo AI (IA).
    Fallback: busca no Bing.
    Custo: ~$0.012/imagem · ~416 imagens com $5.
    """
    import requests, re, json, time as time_module

    stopwords = {"de","da","do","para","com","em","no","na","os","as","que","e","um","uma",
                 "o","a","seu","sua","por","dos","das"}
    palavras = [w for w in titulo.split() if w.lower() not in stopwords and len(w) > 2]
    termo = " ".join(palavras[:6]) if palavras else titulo[:60]

    # Map categoria → estilo visual
    estilo_cat = {
        "Global": "international politics scene, government building or diplomatic meeting, photojournalism",
        "Tech": "technology conference, data center, futuristic computer hardware, blue lighting",
        "Economia": "stock market trading floor, financial district, graphs and screens, brazilian market",
        "Política": "government palace, congress session, political rally, brazilian politics",
        "Brasil": "brazilian city landmark, brazilian street scene, photojournalism",
    }
    vibe = estilo_cat.get(categoria, "dramatic news photography")

    # ── 1. LEONARDO AI ──
    log(f"  🎨 Leonardo AI...")
    headers = {"Authorization": f"Bearer {LEO_KEY}", "Content-Type": "application/json"}

    prompt = f"A dramatic photojournalism news photo of {termo}, {vibe}, cinematic dark composition, photorealistic, ultra HD, empty space at bottom for text overlay, professional photography"

    try:
        r = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            headers=headers,
            json={
                "num_images": 1,
                "prompt": prompt,
                "width": 1080,
                "height": 1344,
                "presetStyle": "CINEMATIC",
                "negative_prompt": "text, watermark, signature, blurry, low quality, cartoon, illustration, logo, drawing",
                "contrast": 3.0,
                "sd_version": "v2",
            },
            timeout=20
        )
        if r.status_code in [200, 201]:
            gen_id = r.json().get("sdGenerationJob", {}).get("generationId", "")
            cost = r.json().get("sdGenerationJob", {}).get("cost", {}).get("amount", "?")
            log(f"  ⏳ Gerando (${cost}/img)...")

            if gen_id:
                for _ in range(30):
                    time_module.sleep(3)
                    r2 = requests.get(
                        f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
                        headers=headers, timeout=10
                    )
                    if r2.status_code == 200:
                        gens = r2.json().get("generations_by_pk", {}).get("generated_images", [])
                        if gens:
                            url = gens[0].get("url", "")
                            if url:
                                ir = requests.get(url, timeout=15)
                                path = f"/tmp/d5n_leo_{gen_id[:8]}.png"
                                with open(path, 'wb') as f:
                                    f.write(ir.content)
                                log(f"  ✅ Leonardo: {len(ir.content)//1024}KB")
                                return path
    except Exception as e:
        log(f"  ⚠️ Leonardo: {e}")

    # ── 2. FALLBACK: BING ──
    log(f"  ⚠️ Fallback: Bing...")
    headers2 = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    estrategias = [
        " ".join(palavras[:5]) + " news" if palavras else titulo[:40],
        f"{palavras[0]} {categoria}" if palavras else titulo[:40],
        {"Global":"world news photography","Tech":"technology computer",
         "Economia":"business finance","Política":"government politics",
         "Brasil":"brazil news"}.get(categoria, "news photography"),
    ]

    for termo_busca in estrategias[:2]:
        try:
            src = f"https://www.bing.com/images/search?q={requests.utils.quote(termo_busca)}&count=10&qft=+filterui:photo-photo"
            resp = requests.get(src, headers=headers2, timeout=8)
            urls = set()
            for pat in [r'murl&quot;:&quot;(https?://[^&]+)', r'mediaurl=(https?://[^&]+)']:
                for u in re.findall(pat, resp.text):
                    uc = u.split('&')[0]
                    if any(ext in uc.lower() for ext in ['.jpg','.jpeg','.png']):
                        if not any(b in uc.lower() for b in ['logo','icon','avatar','svg']):
                            if len(uc) < 300:
                                urls.add(uc)
            for u in list(urls)[:8]:
                try:
                    r2 = requests.get(u, headers={**headers2, "Referer":"https://bing.com/"}, timeout=8)
                    ct = r2.headers.get('Content-Type','')
                    if r2.status_code == 200 and 'image' in ct and 15000 < len(r2.content) < 5000000:
                        path = f"/tmp/d5n_bing_{abs(hash(u)) % 100000}.jpg"
                        with open(path, 'wb') as f:
                            f.write(r2.content)
                        log(f"  ✅ Bing: {len(r2.content)//1024}KB")
                        return path
                except:
                    continue
        except:
            continue

    log(f"  ⚠️ Sem imagem")
    return None


# ════════════════════════════════════════════════
#  3. GERAR RESUMO + HOOK com Gemini
# ════════════════════════════════════════════════

def gerar_resumo_e_hook(titulo, categoria):
    """
    Gera resumo de 3 linhas + hook de engajamento usando Gemini.
    Fallback: resumo extraído do título.
    """
    import google.genai as genai
    from google.genai import types

    hook = escolher_hook(categoria)

    prompt = f"""Você é um redator de notícias para Instagram. 
Para a manchete: "{titulo}"
Gere um resumo de EXATAMENTE 3 linhas curtas (máx 40 caracteres cada).
Tom: direto, informativo, brasileiro.
NÃO use aspas.
Formato: apenas as 3 linhas, uma por linha."""

    try:
        client = genai.Client(api_key=API_KEY)
        resp = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[prompt],
        )
        linhas = [l.strip() for l in resp.text.strip().split('\n') if l.strip()][:3]
        # Garantir que tem 3 linhas
        while len(linhas) < 3:
            linhas.append("")
        return linhas[:3], hook
    except Exception as e:
        log(f"  ⚠️ Gemini resumo: {e}")
        # Fallback: quebrar o título em 3 partes
        palavras = titulo.split()
        parte1 = " ".join(palavras[:len(palavras)//3]) if len(palavras) > 3 else titulo[:40]
        parte2 = " ".join(palavras[len(palavras)//3:2*len(palavras)//3]) if len(palavras) > 6 else ""
        parte3 = " ".join(palavras[2*len(palavras)//3:]) if len(palavras) > 6 else ""
        return [parte1[:40], parte2[:40], parte3[:40]], hook


# ════════════════════════════════════════════════
#  4. GERAR CARD
# ════════════════════════════════════════════════

def criar_card(titulo, categoria, data_curta, bg_path, resumo, hook, output_path):
    """Gera card final com foto + headline + resumo + link + hook."""
    est = CATEGORIAS.get(categoria, CATEGORIAS["Global"])

    # ── Processar imagem de fundo ──
    if bg_path and os.path.exists(bg_path):
        try:
            img = Image.open(bg_path).convert("RGB").resize((W, H), Image.LANCZOS)
            pixels = img.load()
            mr,mg,mb = est["escuro"]
            for y in range(H):
                ratio = y / H
                if ratio > 0.08:
                    dark = int((ratio - 0.08) / 0.92 * 210)
                    for x in range(W):
                        r,g,b = pixels[x,y]
                        r = max(0,r-dark); g = max(0,g-dark); b = max(0,b-dark)
                        if ratio > 0.3:
                            tint = (ratio-0.3)*0.15
                            r = int(r*(1-tint)+mr*tint); g = int(g*(1-tint)+mg*tint); b = int(b*(1-tint)+mb*tint)
                        pixels[x,y] = (max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))
            # Vignette
            for y in range(H):
                for x in range(W):
                    dx = min(x, W-x)/(W/2); dy = min(y, H-y)/(H/2)
                    vig = min(dx, dy)
                    if vig < 0.5:
                        esc = int((0.5-vig)*90)
                        r,g,b = pixels[x,y]
                        pixels[x,y] = (max(0,r-esc),max(0,g-esc),max(0,b-esc))
        except Exception as e:
            log(f"  ⚠️ Erro img: {e}")
            img = Image.new('RGB', (W,H), (12,14,18))
    else:
        log(f"  ⚠️ Sem imagem de fundo!")
        # Gradiente de emergência
        img = Image.new('RGB', (W,H), (12,14,18))
        draw = ImageDraw.Draw(img)
        for y in range(H):
            ratio = y/H
            r = int(10+ratio*(est["escuro"][0]/3))
            g = int(12+ratio*(est["escuro"][1]/3))
            b = int(18+ratio*(est["escuro"][2]/3))
            draw.rectangle([(0,y),(W,y)], fill=(r,g,b))

    draw = ImageDraw.Draw(img)

    # ── Fontes ──
    f_badge = get_font(30, 700)
    f_head = get_font(105, 900)
    f_resumo = get_font(32, 600)
    f_hook = get_font(36, 700)
    f_link = get_font(22, 500)
    f_sub = get_font(20, 400)

    # ── SELO CATEGORIA (topo esquerdo) ──
    bx = 45
    draw.rectangle([(bx, 50), (bx+140, 90)], fill=est["cor"])
    draw.text((bx+14, 56), est["badge"], fill=(255,255,255), font=f_badge)

    # ── HEADLINE (terço inferior) ──
    chars = 14
    linhas = textwrap.wrap(titulo.upper(), width=chars)
    ty = H - 580
    bar_h = len(linhas) * 105 + 30
    draw.rectangle([(bx, ty-15), (bx+6, ty-15+bar_h)], fill=est["cor"])

    for linha in linhas:
        draw.text((bx+4, ty+4), linha, fill=(0,0,0), font=f_head)
        draw.text((bx, ty), linha, fill=(255,255,255), font=f_head)
        ty += 105

    # ── RESUMO 3 LINHAS ──
    ry = ty + 15
    resumo_linhas = [l for l in resumo if l]
    for rl in resumo_linhas:
        draw.text((bx, ry), rl, fill=(200,210,225), font=f_resumo)
        ry += 38

    # ── LINK ──
    ly = max(ry + 12, H - 120)
    draw.rectangle([(bx, ly), (W-50, ly+2)], fill=est["claro"])

    link_y = ly + 10
    draw.text((bx, link_y), SITE_URL, fill=est["claro"], font=f_link)

    # ── HOOK DE ENGAJAMENTO ──
    hy = link_y + 32
    draw.text((bx, hy), hook, fill=(255,255,255), font=f_hook)

    # ── RODAPÉ ──
    draw.text((bx, H-40), f"dropfivenews  ·  {data_curta}", fill=(120,130,150), font=f_sub)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, quality=92)
    return output_path


# ════════════════════════════════════════════════
#  5. CARD RESUMO DO DIA
# ════════════════════════════════════════════════

def criar_card_resumo(noticias, data_br, data_curta, output_path):
    img = Image.new('RGB', (W, H), (12, 14, 18))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(10+y/H*15); g = int(12+y/H*18); b = int(18+y/H*25)
        draw.rectangle([(0,y),(W,y)], fill=(r,g,b))

    f_logo = get_font(38,700); f_data = get_font(20,400)
    f_cat = get_font(24,700); f_item = get_font(26,500); f_rodape = get_font(18,400)

    draw.text((50,40), "DROP FIVE NEWS", fill=(200,210,220), font=f_logo)
    draw.text((50,82), data_br.upper(), fill=(120,130,150), font=f_data)
    draw.rectangle([(50,115),(W-50,117)], fill=(40,50,65))

    cats = ["Global","Brasil","Tech","Economia","Política"]
    n_por_cat = {}
    for n in noticias:
        n_por_cat.setdefault(n["pilar"], []).append(n)

    y = 145
    for cat in cats:
        lst = n_por_cat.get(cat, [])
        if not lst: continue
        est = CATEGORIAS.get(cat, CATEGORIAS["Global"])
        draw.text((50, y), f"{est['icone']} {cat.upper()}", fill=est["cor"], font=f_cat)
        y += 36
        for ntc in lst[:4]:
            for linha in textwrap.wrap(ntc["titulo"], width=32):
                draw.text((75,y), linha, fill=(200,210,220), font=f_item); y+=30
            y += 4
        y += 8

    draw.rectangle([(50,H-60),(W-50,H-58)], fill=(40,50,65))
    draw.text((50,H-48), f"{len(noticias)} notícias · dropfivenews · {SITE_URL}", fill=(120,130,150), font=f_rodape)
    img.save(output_path, quality=92)


# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════

def listar_datas():
    if os.path.isdir(ARQUIVO_DIR):
        return sorted(f.replace('.md','') for f in os.listdir(ARQUIVO_DIR) if f.endswith('.md'))
    return []


def main():
    parser = argparse.ArgumentParser("Pipeline de cards D5N")
    parser.add_argument('--data', help='Data (YYYY-MM-DD)')
    parser.add_argument('--listar', action='store_true')
    parser.add_argument('--resumo', action='store_true', help='Só card resumo')
    parser.add_argument('--forcar', type=int, default=0, help='Recriar N primeiros')
    args = parser.parse_args()

    if args.listar:
        for d in listar_datas(): print(f"  • {d}")
        return

    data_str = args.data or datetime.now().strftime("%Y-%m-%d")
    noticias, data_br = carregar_noticias(data_str)
    if not noticias:
        print("❌ Nenhuma notícia"); sys.exit(1)

    dc = data_curta(data_br)
    out_dir = f"{OUTPUT_DIR}/{data_str}"
    os.makedirs(out_dir, exist_ok=True)

    cats = sorted(set(n["pilar"] for n in noticias))
    print(f"\n╔══ D5N — Pipeline Cards ══╗")
    print(f"║  Data: {data_br}")
    print(f"║  Notícias: {len(noticias)}")
    print(f"║  Categorias: {', '.join(cats)}")
    print(f"╚══════════════════════════╝\n")

    gerados = []

    # ── Card resumo ──
    rp = f"{out_dir}/resumo_{data_str}.png"
    criar_card_resumo(noticias, data_br, dc, rp)
    gerados.append(rp)
    log(f"✅ Resumo: {os.path.basename(rp)} ({os.path.getsize(rp)//1024}KB)")

    # ── Cards individuais ──
    ind_dir = f"{out_dir}/individuais"
    os.makedirs(ind_dir, exist_ok=True)

    for i, ntc in enumerate(noticias):
        titulo = ntc["titulo"]
        cat = ntc["pilar"]
        num = f"{ntc['numero']:02d}"
        fname = f"{num}_{cat.lower()}_{data_str}"

        # Pular se já existe
        out_path = f"{ind_dir}/{fname}.png"
        if os.path.exists(out_path) and i >= args.forcar:
            log(f"  ⏩ {fname}.png (já existe)")
            gerados.append(out_path)
            continue

        log(f"\n  [{i+1}/{len(noticias)}] {titulo[:50]}...")

        # 1. Buscar imagem
        bg = buscar_imagem(titulo, cat)

        # 2. Gerar resumo + hook
        resumo, hook = gerar_resumo_e_hook(titulo, cat)

        # 3. Gerar card
        criar_card(titulo, cat, dc, bg, resumo, hook, out_path)
        gerados.append(out_path)
        sz = os.path.getsize(out_path)//1024
        log(f"  🎴 {fname}.png ({sz}KB) — resumo/hook: OK")

        # Limpar bg temporário
        if bg and bg.startswith("/tmp/") and os.path.exists(bg):
            try: os.remove(bg)
            except: pass

        time.sleep(0.3)

    # ── Summary ──
    print(f"\n📊 {len(gerados)} cards em: {out_dir}/")
    print(f"📌 Instagram: @dropfivenews")
    print()


if __name__ == '__main__':
    main()
