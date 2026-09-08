# Registro de Colaboração da Equipe

Este documento consolida o histórico de trabalho em equipe, o fluxo de branches, revisões cruzadas de Pull Requests, abertura de issues e resolução de conflitos realizados no repositório **bot-monitor-promocoes**.

---

## 1. Organização do Fluxo de Trabalho

A equipe adotou o modelo de fluxo de trabalho baseado em branches individuais (`feature/<nome>`), onde nenhuma alteração é enviada diretamente para a branch `main`. Cada entrega seguiu o ciclo completo:
1. Criação de branch a partir da `main` atualizada.
2. Implementação das funcionalidades ou melhorias com commits atômicos e descritivos.
3. Envio da branch ao GitHub e abertura de Pull Request.
4. Revisão cruzada obrigatória com comentários na aba Conversation por outro integrante.
5. Mescla (Merge) para a `main` e exclusão das branches integradas.

---

## 2. Tabela de Revisão Cruzada de Pull Requests

Cada Pull Request foi inspecionado, comentado e validado por um colega antes da mescla, assegurando qualidade de código e alinhamento do time:

| PR | Título / Escopo | Autor(a) | Branch | Revisor(a) | Status |
|---|---|---|---|---|---|
| [#1](https://github.com/Lbfte/bot-monitor-promocoes/pull/1) | feat: identifica a loja e adiciona hashtag na promocao | Laís Bembo (`@Lbfte`) | `feature/lais` | Albert William (`@albert-wb`) | Mesclado |
| [#2](https://github.com/Lbfte/bot-monitor-promocoes/pull/2) | test: testes automatizados dos filtros | Albert William (`@albert-wb`) | `feature/albert` | Filipe José (`@soueuFilipeJose`) | Mesclado |
| [#4](https://github.com/Lbfte/bot-monitor-promocoes/pull/4) | feat: comando /status no bot | Filipe José (`@soueuFilipeJose`) | `feature/filipe` | Laís Bembo (`@Lbfte`) | Mesclado |
| [#6](https://github.com/Lbfte/bot-monitor-promocoes/pull/6) | docs: adiciona template de issue e reescreve descricao | Amanda Albuquerque (`@amandaalbuquerquesilva2-star`) | `feature/amanda` | Albert William (`@albert-wb`) | Mesclado |
| [#7](https://github.com/Lbfte/bot-monitor-promocoes/pull/7) | docs: adiciona changelog da v1.0 e registro da colaboracao | Albert William (`@albert-wb`) | `feature/albert` | Laís Bembo (`@Lbfte`) | Mesclado |

---

## 3. Links dos Pull Requests

- **PR #1:** [feat: identifica a loja e adiciona hashtag na promocao](https://github.com/Lbfte/bot-monitor-promocoes/pull/1)
- **PR #2:** [test: testes automatizados dos filtros](https://github.com/Lbfte/bot-monitor-promocoes/pull/2)
- **PR #4:** [feat: comando /status no bot](https://github.com/Lbfte/bot-monitor-promocoes/pull/4)
- **PR #6:** [docs: adiciona template de issue e reescreve descricao](https://github.com/Lbfte/bot-monitor-promocoes/pull/6)
- **PR #7:** [docs: adiciona changelog da v1.0 e registro da colaboracao](https://github.com/Lbfte/bot-monitor-promocoes/pull/7)

---

## 4. Links das Issues de Melhorias Futuras

O repositório registrou melhorias planejadas para próximas iterações do bot:
- **Issue #3:** [Repassar promoções que vêm com vídeo](https://github.com/Lbfte/bot-monitor-promocoes/issues/3) — Proposta para estender o suporte de extração e repasse de mídias para incluir vídeos no Telegram Bot API.
- **Issue #5:** [Monitorar mais de um canal fonte](https://github.com/Lbfte/bot-monitor-promocoes/issues/5) — Proposta para permitir o acompanhamento simultâneo de múltiplos canais de promoções configuráveis.

---

## 5. Resolução de Conflito de Merge (Etapa 4)

Na Etapa 4, a integração concorrente da branch `feature/amanda` com a `main` (que já continha as atualizações da branch `feature/filipe`) causou um conflito de merge no arquivo `README.md` devido à edição simultânea das linhas de descrição inicial do bot. O conflito foi solucionado por meio de uma mescla cuidadosa que preservou a melhor redação da descrição sem perder as adições funcionais da `main`, garantindo a remoção de todos os marcadores de conflito (`<<<<<<<`, `=======`, `>>>>>>>`). Os detalhes completos do conflito, os trechos divergentes e a justificativa da decisão estão registrados em [docs/CONFLITO.md](CONFLITO.md).
