# D5N — Cards para Instagram

## Pipeline de Geração

Script: `gerar_cards_pipeline.py`

Gera cards no estilo "Notícia de Impacto" para cada notícia do D5N.

### Estrutura de saída

```
cards-instagram/YYYY-MM-DD/
├── resumo_YYYY-MM-DD.png         → Resumo do dia com todas as manchetes
└── individuais/
    ├── 01_categoria_YYYY-MM-DD.png  → 1 card por notícia
    └── ...
```

### Como usar

```bash
# Gerar cards do dia atual
python3 gerar_cards_pipeline.py

# Data específica
python3 gerar_cards_pipeline.py --data 2026-06-01

# Forçar recriação
python3 gerar_cards_pipeline.py --forcar 99
```

### Cada card contém

| Elemento | Descrição |
|----------|-----------|
| Badge categoria | Selo colorido (MUNDO, TECH, ECONOMIA, POLÍTICA, BRASIL) |
| Foto de fundo | Imagem real buscada via Bing Images |
| Headline | Título da notícia em DM Sans 105pt Weight 900 |
| Resumo | 3 linhas de contexto (gerado por Gemini ou fallback) |
| Link | d5n-daily.netlify.app |
| Hook | Frase de engajamento para Instagram |
| Rodapé | dropfivenews · data |

### Categorias e cores

| Categoria | Cor | Badge |
|-----------|-----|-------|
| Global | Azul | MUNDO |
| Tech | Ciano | TECH |
| Economia | Dourado | ECONOMIA |
| Política | Vermelho | POLÍTICA |
| Brasil | Verde | BRASIL |

### Geração de imagens de fundo

Primário: **Leonardo AI** (IA generativa)
- Chave: `d6f18826-dfe3-4df2-b58b-3f669de8a3d6`
- Custo: ~$0.012/imagem (~416 imagens com $5)
- Prompt automático por categoria + título da notícia
- Estilo: Cinematic, foto jornalística
- Fallback: Bing Images (se IA falhar)

### Limitações atuais

1. **Resumo com IA**: Gemini free quota (20 req/dia). Com plano pago, funciona para todas.
2. **Fonte DM Sans**: Instalada localmente em `/usr/local/share/fonts/d5n/`.
3. **Leonardo AI**: Requer internet e saldo de tokens ($5 disponível).

### Integração no cron

```bash
# Executar diariamente junto com o deploy
0 8 * * * cd /root/repositorio/d5n-videocast-source && python3 gerar_cards_pipeline.py
```

### Para melhorar (próximos passos)

- Usar Veo 3 para animar cards → vídeos para Reels/Stories
- Envio automático para Instagram (API Business)
- Substituir Leonardo por Imagen 4.0 quando plano pago do Google for ativado
