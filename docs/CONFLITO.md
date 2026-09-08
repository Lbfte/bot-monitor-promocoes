# Registro de Resolução de Conflito de Merge

Este documento descreve o conflito de merge provocado e resolvido durante a **Etapa 4** da atividade prática colaborativa no repositório `bot-monitor-promocoes`.

---

## 1. Contexto do Conflito

Durante o desenvolvimento concorrente em equipe:
- O **Integrante 3** (Filipe José) abriu e mesclou o [PR #4](https://github.com/Lbfte/bot-monitor-promocoes/pull/4), que introduziu o comando `/status` e realizou ajustes no cabeçalho e na descrição inicial do `README.md`.
- Concomitantemente, a **Integrante 4** (Amanda Albuquerque) abriu o [PR #6](https://github.com/Lbfte/bot-monitor-promocoes/pull/6), no branch `feature/amanda`, reescrevendo a descrição do projeto no `README.md` e adicionando o template de issue.

Como ambos alteraram o mesmo bloco de linhas no topo do `README.md`, ao tentar mesclar a `main` atualizada de volta para o branch `feature/amanda`, o Git gerou um conflito de merge.

---

## 2. O Conflito no `README.md`

O Git apontou o conflito com os seguintes blocos divergentes:

```markdown
<<<<<<< HEAD (feature/amanda)
Bot em Python que acompanha um canal de promoções, republica as ofertas
no seu canal e envia alertas personalizados por palavra-chave.
=======
Monitora um canal público de promoções do Telegram, reposta tudo no seu
próprio canal e avisa no privado quem está esperando um produto.
>>>>>>> main (origin/main com alterações do Filipe)
```

---

## 3. Estratégia de Resolução

A equipe analisou as duas versões e decidiu adotar a redação proposta pela Amanda, que é mais completa, formal e descreve com precisão a dinâmica Telegram → Telegram e os alertas por palavra-chave.

1. **Remoção dos Marcadores**: Os marcadores de conflito (`<<<<<<<`, `=======`, `>>>>>>>`) foram completamente removidos.
2. **Preservação das Mudanças do Filipe**: Todas as demais adições da `main` (documentação do comando `/status` e testes relacionados) foram integralmente preservadas no restante do arquivo.
3. **Commit de Resolução**: A mescla resolvida foi registrada no commit [`0ba1048`](https://github.com/Lbfte/bot-monitor-promocoes/commit/0ba1048a31b55970f50192196fcfeb509de979ce).

---

## 4. Validação

- O arquivo `README.md` foi inspecionado para assegurar que nenhum resíduo de conflito permanecesse.
- A suíte de testes unitários e CI foi executada com sucesso.
- O PR #6 foi revisado pelo Integrante 5 e mesclado à branch `main` no commit [`166c68d`](https://github.com/Lbfte/bot-monitor-promocoes/commit/166c68d4469792ba26a9fb5fa64e229fc94ad53f).
