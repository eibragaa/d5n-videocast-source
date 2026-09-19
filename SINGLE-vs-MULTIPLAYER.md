# Single Player vs Multiplayer — D5N

**Última atualização:** 19/09/2026  
**Status:** single player (Hoje: apenas Jean usa)

## 1. Definição

| | Single Player | Multiplayer |
|---|---|---|
| **Usuário** | Um só (Jean) | Múltiplos (equipe, clientes, públicos) |
| **Acesso** | Total, sem permissionamento | Por nível: leitura, edição, admin |
| **Regras** | Poucas — agente faz o que anda | Muitas — cada ação tem owner |
| **Backup** | Diário dos manifests | Por usuário + audit trail |
| **Log** | Execuções do pipeline | Quem fez o quê, quando |

## 2. Single Player (Hoje)

- **Usuário:** Jean Braga (admin)
- **Automação:** pipeline D5N roda sem interação humana
- **Aprovação:** não requerida para publicação (trust na curadoria da IA)
- **Feedbacks:** registrados manualmente ou via issues

## 3. Trigger Points para Multiplayer

Mudar para multiplayer quando:

1. **Mais de 1 pessoa acessa o D5N** para editar/aprovar conteúdo
2. **Clientes ou parceiros** precisam de acesso ao boletim
3. **Equipe** precisa de visibilidade sobre o que foi publicado
4. **Exigência legal/contractual** de audit trail

## 4. Estrutura Necessária para Multiplayer

### 4.1 Permissionamento

| Nível | Permissões |
|---|---|
| Leitura | Ver site, feeds, episódios |
| Edição | Editar manifests, roteiros (com aprovação) |
| Publicação | Fazer deploy, postar Instagram/Telegram |
| Admin | Configurar pipelines, adicionar fontes, ver logs |

### 4.2 Audit Trail

- Cada ação registrada: quem, o quê, quando
- Log em `/root/.hermes/state/d5n/audit-trail.json`
- Retenção: 90 dias mínimo

### 4.3 Backup por Usuário

- Manifests versionados por usuário (git blame já faz isso)
- Áudios com metadados de autor

## 5. Plano de Migração

**Fase 1 (Now → Single Player consolidado):**
- [x] Mapa.md criado
- [x] Governança.md criada
- [x] Auditoria automática configurada
- [ ] Index de execuções funcional

**Fase 2 (Multiplayer básico):**
- [ ] Definir usuários e níveis
- [ ] Criar auth básico (ou usar Telegram ID como identidade)
- [ ] Log de ações por usuário
- [ ] Dashboard de atividades

**Fase 3 (Multiplayer completo):**
- [ ] API de acesso para externos
- [ ] Rate limiting por usuário
- [ ] Whitelist de IPs
- [ ] Regras de negócio por usuário

## 6. Decisão

**Decisão atual:** continuar em single player até que haja necessidade real de multiplayer. Single player é mais simples, mais barato, menos falhas.

**Revisar:** quando houver 2+ pessoas ativas no D5N.
