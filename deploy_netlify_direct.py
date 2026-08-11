#!/usr/bin/env python3
"""PLAN B: Deploy direto no Netlify sem GitHub.

Le o token de /root/.netlify-token e faz deploy via API REST (zip POST).
Usa site ID (UUID) do site cc6d8958-b9b0-42b0-a008-b8dda2ba57fc.

Uso: python3 deploy_netlify_direct.py

Pre-requisitos:
  1. Criar Personal Access Token em https://app.netlify.com/user/applications
  2. Salvar em /root/.netlify-token (1 linha, sem 
)
"""

import json
import os
import sys
import time
import urllib.request
import zipfile
import io
from pathlib import Path

SITE_ID = "cc6d8958-b9b0-42b0-a008-b8dda2ba57fc"
REPO = Path("/root/repositorio/d5n-videocast-source")
TOKEN_FILE = Path("/root/.netlify-token")

def log(msg):
    print(msg)

def main():
    log(f"Deploy DIRETO Netlify - {time.strftime('%Y-%m-%d')} (Plan B)")

    token = TOKEN_FILE.read_text().strip()
    log(f"Token: {len(token)} chars")

    os.chdir(REPO)

    if not Path("index.html").exists():
        log("ERRO: index.html nao encontrado")
        sys.exit(1)

    import re
    html = Path("index.html").read_text()
    m = re.search(r'<strong>(\d+)</strong><span>not\u00edcias', html)
    nc = int(m.group(1)) if m else 0
    if nc == 0:
        log("BLOQUEADO: 0 noticias")
        sys.exit(1)
    log(f"OK: {nc} noticias")

    # ── Verification Engine /goal ──
    log("")
    log("Rodando Verification Engine...")
    verify_script = Path("/root/.hermes/scripts/d5n-verify-site.py")
    if verify_script.exists():
        import subprocess
        r = subprocess.run(
            ["python3", str(verify_script)],
            capture_output=True, text=True, timeout=60
        )
        print(r.stdout)
        if r.returncode != 0:
            log("⚠️  Verificação falhou — deploy bloqueado")
            sys.exit(1)
        log("✅ Verificação OK — prosseguindo com deploy")
    else:
        log("⚠️  Script de verificação não encontrado, pulando")

    # Criar zip
    log("Criando zip...")
    buf = io.BytesIO()
    files = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for item in sorted(REPO.rglob("*")):
            if not item.is_file(): continue
            rel = item.relative_to(REPO)
            r = str(rel)
            if r.startswith((".git/", "cards-instagram/", "scripts/", "__pycache__/", ".github/")): continue
            if r.endswith((".sh", ".py", ".md")): continue
            if r in (".gitignore", "netlify.toml", "source.md", "episode-counter.json"): continue
            z.write(str(item), r)
            files += 1
        sn = REPO / "source.md.nossa"
        if sn.exists():
            z.write(str(sn), "source.md")
            files += 1

    zip_data = buf.getvalue()
    mb = len(zip_data) / 1024 / 1024
    log(f"Zip: {files} arquivos, {mb:.1f} MB")

    # Deploy
    log(f"Enviando deploy para site {SITE_ID}...")
    req = urllib.request.Request(
        f"https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys",
        data=zip_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        deploy = json.loads(r.read())

    did = deploy["id"]
    state = deploy.get("state", "?")
    url = deploy.get("ssl_url") or deploy.get("url") or "?"
    reqd = deploy.get("required", [])
    log(f"Deploy: {did}")
    log(f"Estado: {state}")
    log(f"URL: {url}")
    log(f"Faltando: {len(reqd)}")

    Path("/tmp/.deploy-d5n-failed").unlink(missing_ok=True)

    log("")
    log("=" * 45)
    log(f"Deploy DIRETO concluido {time.strftime('%H:%M:%S')}")
    log("https://d5n-daily.netlify.app/")
    log("=" * 45)

if __name__ == "__main__":
    main()
