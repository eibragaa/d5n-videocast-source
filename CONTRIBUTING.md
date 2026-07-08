# Contribuindo para o Drop Five News

Obrigado pelo interesse em contribuir com o D5N! Este é um projeto pessoal mantido por [Jean Braga](https://instagram.com/jeanbraga.ai), mas feedback, sugestões e reports de bugs são sempre bem-vindos.

---

## 📋 Índice

- [Como Contribuir](#como-contribuir)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Melhorias](#sugerindo-melhorias)
- [Pull Requests](#pull-requests)
- [Estrutura do Código](#estrutura-do-código)
- [Style Guide](#style-guide)

---

## Como Contribuir

### 🐛 Reportando Bugs

Se você encontrou um bug no site, podcast ou qualquer parte do projeto:

1. **Verifique se o bug já foi reportado** — Pesquise nas [Issues](https://github.com/eibragaa/d5n-videocast-source/issues)
2. **Abra uma nova issue** — Use o template de bug report e inclua:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Screenshots (se aplicável)
   - URL do site (se for bug visual)

### 💡 Sugerindo Melhorias

Tem uma ideia para melhorar o D5N?

1. **Verifique o roadmap** — Veja se a feature já está planejada no [CHANGELOG.md](CHANGELOG.md)
2. **Abra uma issue** — Use o template de feature request e explique:
   - O problema que sua feature resolve
   - Como ela funcionaria
   - Alternativas que você considerou

### 🔧 Pull Requests

Pull requests são bem-vindos! Para garantir que sua contribuição seja aceita:

1. **Fork o repositório**
2. **Crie uma branch** — `git checkout -b feature/nome-da-feature`
3. **Faça suas mudanças** — Siga o [Style Guide](#style-guide)
4. **Teste** — Certifique-se que o código funciona
5. **Commit** — Use mensagens claras e descritivas
6. **Push** — `git push origin feature/nome-da-feature`
7. **Abra um Pull Request** — Descreva o que você mudou e por quê

**Antes de abrir um PR:**
- ✅ Código está formatado e limpo
- ✅ Comentários estão atualizados
- ✅ Documentação foi atualizada (se necessário)
- ✅ Não há arquivos desnecessários (cache, .env, etc.)

---

## Estrutura do Código

### Arquivos Principais

```
gerar_pagina_d5n.py          # Script principal (900+ linhas)
├── load_today_news()        # Carrega notícias do trends file
├── load_episode_history()   # Carrega histórico de episódios
├── gerar_html()             # Gera HTML completo
├── gerar_source_md()        # Gera roteiro do podcast
├── gerar_feeds_json()       # Gera JSON Feed
└── gerar_feed_rss()         # Gera RSS Feed

gerar_cards_pipeline.py      # Gera cards Instagram
scripts/
├── amanha-conectada/        # Programa "Amanhã Conectada"
├── d5n-babysitter.py        # Validação automática
└── validate_mp3.py          # Validação de MP3s
```

### Fluxo de Dados

```
drop5news-trends-YYYY-MM-DD.txt  →  gerar_pagina_d5n.py  →  index.html
                                                              feed.json
                                                              d5n-feed.xml
                                                              source.md
                                                              2026/YYYY-MM-DD.md
```

---

## Style Guide

### Python

- **Indentação:** 4 espaços (não tabs)
- **Linhas:** Máximo 100 caracteres
- **Nomes:**
  - Variáveis: `snake_case`
  - Funções: `snake_case`
  - Classes: `PascalCase`
  - Constantes: `UPPER_SNAKE_CASE`
- **Docstrings:** Use docstrings para funções públicas
- **Imports:** Agrupe em: stdlib, third-party, local

```python
# Exemplo
def load_today_news(date_str: str, silent: bool = False) -> list:
    """
    Carrega notícias do arquivo trends do dia.
    
    Args:
        date_str: Data no formato YYYY-MM-DD
        silent: Se True, não imprime warnings
    
    Returns:
        Lista de dicionários com as notícias
    """
    # ...
```

### HTML/CSS

- **Indentação:** 2 espaços
- **Classes:** `kebab-case` (ex: `news-item`, `section-header`)
- **IDs:** Apenas quando necessário para JavaScript
- **CSS:** Use variáveis CSS para cores e valores reutilizáveis

```css
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --text: #f1f5f9;
  --accent: #94a3b8;
}

.news-item {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}
```

### Markdown

- **Headers:** Use `#` para títulos (não underline)
- **Listas:** Use `-` para listas não ordenadas
- **Código:** Use ``` para blocos de código
- **Links:** Use links relativos quando possível

---

## Áreas que Precisam de Ajuda

### 🔥 Alta Prioridade

1. **Transcrições automáticas** — Integrar Whisper API para gerar transcrições dos podcasts
2. **Newsletter** — Implementar captura de email com ConvertKit/Mailchimp
3. **Player de vídeo** — Criar player com slides sincronizados ao áudio

### 📊 Média Prioridade

4. **API pública** — Endpoint REST para desenvolvedores consumirem o feed
5. **Testes automatizados** — Adicionar pytest para funções críticas
6. **Internacionalização** — Suporte para inglês/espanhol

### 🎨 Baixa Prioridade

7. **App mobile** — PWA para iOS/Android
8. **Widgets** — Embeddable widgets para outros sites
9. **Analytics avançados** — Heatmaps, funnels, cohort analysis

---

## Ambiente de Desenvolvimento

### Requisitos

- Python 3.11+
- Git
- Editor de código (VSCode, PyCharm, etc.)

### Setup Local

```bash
# Clone o repositório
git clone https://github.com/eibragaa/d5n-videocast-source.git
cd d5n-videocast-source

# (Opcional) Crie um virtual environment
python3 -m venv venv
source venv/bin/activate

# Execute o script principal
python3 gerar_pagina_d5n.py --data $(date +%Y-%m-%d) --no-podcast

# Abra o site no navegador
open index.html  # macOS
# ou
xdg-open index.html  # Linux
```

### Testando Mudanças

```bash
# Gere o site localmente
python3 gerar_pagina_d5n.py --data 2026-07-08

# Valide a saída
cat index.html | grep -c "news-item"  # Deve ter 18+ notícias
cat feed.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['items']))"

# Teste os cards
python3 gerar_cards_pipeline.py --data 2026-07-08
ls cards-instagram/2026-07-08/
```

---

## Código de Conduta

Este projeto segue um código de conduta simples:

- **Seja respeitoso** — Trate todos com cortesia
- **Seja construtivo** — Feedback deve ser útil e específico
- **Seja paciente** — Respostas podem demorar (projeto pessoal)
- **Seja claro** — Use linguagem simples e direta

---

## Contato

- **Instagram:** [@jeanbraga.ai](https://instagram.com/jeanbraga.ai)
- **GitHub:** [@eibragaa](https://github.com/eibragaa)
- **Email:** Via DM no Instagram

---

## Licença

Este projeto é de código aberto para fins de referência e aprendizado.  
Para uso comercial, entre em contato.

---

**Obrigado por contribuir! 🙏**
