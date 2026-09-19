# Padrão de Operação — Drop Five News (D5N)

**Última atualização:** 19/09/2026  
**Revisão:** quando houver mudança na pipeline ou no design editorial

## 1. Visão Geral

D5N é um boletim diário de notícias curado por IA, publicado automaticamente todo dia útil.

- **Site:** https://d5n-daily.netlify.app/
- **Instagram:** @minho.oficial
- **Telegram:** @minho.oficial, @d5n-daily
- **Design:** premium editorial — off-white, serifas, numerais mono, 1 acento lime. Rejeita IA slop (dark ou creme+terracota).

## 2. Pipeline de Produção (ordem obrigatória)

1. **Coleta de notícias** → fontes dispersas em `source/`
2. **Geração do site** → `gerar_pagina_d5n.py` → `index.html`
3. **Geração dos programas** → `manha-conectada_pipeline.py` + `fechamento_pipeline.py`
4. **Mixagem do áudio** → `drop5news-mixer-v10.py` (precisa de manifests em `manifests/YYYY-MM-DD/`)
5. **Validação** → `validate_feeds.py` → relatório
6. **Deploy** → `git push origin HEAD:master` → Netlify auto-deploy

## 3. Git Workflow (CRÍTICO)

- **Nunca** editar `index.html` diretamente. Sempre usar `gerar_pagina_d5n.py`.
- **Nunca** fazer PR ou merge manual. Sempre:
  ```
  git push origin HEAD:master
  ```
- **Verificar** após push: `git log master --oneline`
- Branch de trabalho: `test/fechamento-mercado` (ou similar). Após commits: push direto para master.

## 4. Mixer v10

- **Entrada:** manifests em `manifests/YYYY-MM-DD/*.txt`
- **Saída:** MP3 de 8-12 min com 12 seções
- **Sem manifests:** mixer não roda. Gerar manifests antes.
- **Trilhas:** lidas do diretório `assets/` (ou `audio/`)

## 5. Programas

| Programa | Código | Frequência | Pipeline |
|---|---|---|---|
| Drop Five News | D5N | Diário (seg-sex) | `manha-conectada_pipeline.py` |
| Manha Conectada | MC | Diário (seg-sex) | `manha-conectada_pipeline.py` |
| Fechamento do Mercado | FM | Diário (seg-sex) | `fechamento_pipeline.py` |

## 6. Validação

Após gerar qualquer artefato:
```
python3 validate_feeds.py
```
Relatório salvo em `reports/`.

## 7. Deploy

```
git push origin HEAD:master
```
Netlify detecta mudança no master e faz build automático.

Se build falhar: verificar logs no Netlify UI. Sempre testar local antes:
```
python3 -c "import gerar_pagina_d5n; ..." # validar pagina
```

## 8. Adicionar Nova Fonte de Notícias

1. Documentar fonte em `docs/fontes.md`
2. Adicionar lógica de coleção em `gerar_pagina_d5n.py` (ou script separado)
3. Validar coleta: verificar se as notícias estão chegando
4. Commit com mensagem `feat: adiciona fonte XYZ`

## 9. Design Editorial

- **Fundo:** off-white (#F5F0E8 ou similar)
- **Tipografia:** serifas para título, mono para numerais
- **Acento:** lime (1 cor de destaque)
- **Never:** dark mode automático, creme+terracota, emoji (exceto ícones técnicos)

## 10. Troubleshooting

| Problema | Causa comum | Solução |
|---|---|---|
| Mixer não roda | Faltam manifests | Gerar manifests para a data |
| Site não atualiza | Git push falhou ou Netlify offline | Verificar `git log master` e Netlify UI |
| Feed inválido | XML malformado | Rodar `validate_feeds.py` e corrigir |
| Cron falhou | Falta de manifests ou credencial expirada | Verificar logs em `/root/.hermes/logs/` |
