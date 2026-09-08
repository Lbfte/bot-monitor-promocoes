# Monitor de Promoções — Telegram → Telegram

Bot em Python que acompanha um canal de promoções, republica as ofertas
no seu canal e envia alertas personalizados por palavra-chave.

Python puro: sem n8n, sem Docker, sem servidor. Roda de graça no GitHub Actions.

```
                                          ┌→  seu canal (Bot API)
canal fonte (t.me/s/…) → filtros + dedup ─┤
                                          └→  alerta no privado de quem
                                              monitora aquela palavra
```

## Como funciona

O monitor **não** usa sua conta pessoal do Telegram. Ele lê a página de preview
pública do canal (`https://t.me/s/SamuelF3lipePromo`), que é HTML comum. Isso
significa: sem `API_ID`, sem `API_HASH`, sem número de telefone, sem arquivo de
sessão — e sem o risco de banimento que existe ao automatizar uma conta pessoal.

Para publicar, aí sim usa um bot comum (Bot API), que precisa ser administrador
do canal de destino.

Cada rodada é independente: lê o que há de novo, publica, grava o `state.json` e
encerra. A memória entre rodadas vive nesse arquivo, que o próprio workflow
commita de volta no repositório.

---

## Passo 1 — Criar o bot que vai publicar

1. No Telegram, abra [@BotFather](https://t.me/BotFather).
2. Envie `/newbot`.
3. Escolha um **nome** (qualquer coisa, ex: `Promos do Albert`).
4. Escolha um **username**, que precisa terminar em `bot` (ex: `albert_promos_bot`).
5. O BotFather responde com o token, algo como:

   ```
   8123456789:AAEhBOweik6ad9r_ABCDEFGHIJKLMNOPQRS
   ```

Esse valor é o `BOT_TOKEN`. Trate como senha: quem tem o token controla o bot.

> Perdeu ou vazou o token? `/token` no BotFather mostra de novo, `/revoke` gera
> um novo e invalida o antigo.

## Passo 2 — Criar o canal de destino

1. No Telegram: menu → **Novo Canal**.
2. Dê nome e escolha entre público ou privado.
3. Abra as informações do canal → **Administradores** → **Adicionar admin**.
4. Busque pelo username do seu bot e adicione.
5. Deixe ligada a permissão **Publicar mensagens** (as outras podem ficar off).

**Sem esse passo nada funciona** — um bot que não é admin não consegue postar.

## Passo 3 — Descobrir o `DEST_CHAT_ID`

Depende do tipo de canal:

**Canal público** (tem um `@username`): é só usar o username, não precisa de ID
numérico.

```
DEST_CHAT_ID=@meucanaldepromos
```

**Canal privado**: precisa do ID numérico, que começa com `-100`. Para descobrir:

1. Poste qualquer mensagem no canal (o bot já precisa ser admin).
2. Rode:

   ```bash
   python tools/get_chat_id.py SEU_TOKEN_AQUI
   ```

O script lista os chats que o bot enxerga, com o ID pronto para copiar:

```
Promos do Albert
  tipo:  channel
  ID:    -1001234567890
  →  DEST_CHAT_ID=-1001234567890
```

Se aparecer "nenhum chat encontrado", quase sempre é porque o bot não é admin ou
porque você não postou nada no canal depois de adicioná-lo.

## Passo 4 — Configurar e testar localmente

```bash
pip install -r requirements.txt
```

Preencha `BOT_TOKEN` e `DEST_CHAT_ID` no arquivo `monitor_config.env`. Primeiro,
confira se as credenciais estão certas:

```
python run_monitor.py --check
```

Ele testa o token, o acesso ao canal de destino e a leitura do canal fonte, sem
publicar nada. Depois, veja o que seria publicado:

```
python run_monitor.py --dry-run --backfill 5
```

Isso mostra no terminal as 5 últimas promoções já formatadas. A simulação não
grava estado, então nada é "consumido" pelo teste. Gostou do resultado? Rode de
verdade:

```
python run_monitor.py
```

Na primeira execução de verdade ele só marca o ponto de partida e não publica
nada — assim seu canal não nasce com 20 promoções velhas de uma vez. Se quiser
publicar as últimas N imediatamente, use `--backfill N`.

> As opções também existem como variáveis de ambiente (`DRY_RUN`, `BACKFILL`,
> `MAX_POSTS_PER_RUN`), que é como o GitHub Actions as usa. As flags existem
> porque a sintaxe `VAR=valor comando` é do bash e não funciona no PowerShell.

## Passo 5 — Colocar na nuvem (GitHub Actions)

O repositório já tem o workflow em `.github/workflows/monitor.yml`, rodando a
cada 5 minutos. Falta só cadastrar as credenciais.

Em **Settings → Secrets and variables → Actions**:

| Aba | Nome | Valor |
|---|---|---|
| Secrets | `BOT_TOKEN` | o token do BotFather |
| Secrets | `DEST_CHAT_ID` | `@seucanal` ou `-100...` |
| Secrets | `SUBSCRIBERS_KEY` | a chave que está no seu `monitor_config.env` |
| Variables | `SOURCE_CHANNEL` | `SamuelF3lipePromo` |

As demais opções (filtros, rodapé) são opcionais e vão na aba **Variables**, com
os mesmos nomes do `monitor_config.env`.

Depois vá em **Actions → Monitor de Promoções → Run workflow** para disparar a
primeira rodada na mão e conferir o log.

### Por que isso sai de graça

Repositórios **públicos** têm minutos ilimitados no GitHub Actions. Em
repositório privado de conta gratuita, workflows agendados por `cron` são
bloqueados — se você tornar este repo privado, o monitor para de rodar.

Dois detalhes do plano grátis:

- O `cron` do GitHub **atrasa** em horários de pico. `*/5` na prática vira algo
  entre 5 e 15 minutos. Para repasse instantâneo seria preciso um processo
  rodando 24/7 numa VM.
- O GitHub **desativa** workflows agendados após 60 dias sem atividade no repo.
  Como o monitor commita o `state.json`, o repositório nunca fica parado.

---

## Alertas por palavra-chave

Além de repostar tudo no canal, o bot avisa no privado quem pediu para
acompanhar um produto específico. Qualquer pessoa que abrir conversa com o bot
pode se inscrever:

```
/monitorar notebook          → avisa em qualquer promoção de notebook
/monitorar notebook 3000     → avisa só se o preço for até R$ 3.000
/parar notebook              → cancela
/lista                       → mostra o que você monitora
```

O aviso chega no privado com o texto da promoção e um link para o post no canal.

Como funciona por dentro: não há processo escutando o tempo todo. A cada rodada
o monitor chama `getUpdates`, responde os comandos que chegaram e só depois
publica — então uma inscrição feita agora já vale para as promoções da mesma
rodada. O efeito colateral é que a resposta ao comando demora o mesmo tanto que
o cron: alguns minutos.

**Como as palavras são comparadas:** acento e maiúsculas são ignorados, e a
busca casa com o início de palavra. Então `notebook` também pega "notebooks",
mas `tv` não dispara em "motivador". Palavras de duas letras são aceitas, para
que `tv`, `pc` e `hd` funcionem.

**Quando há teto de preço mas o post não traz preço legível**, o alerta é
enviado mesmo assim, com um aviso — perder uma promoção é pior do que receber
um aviso a mais. Isso é diferente do filtro `MAX_PRICE` do canal, que descarta
o post nesse caso.

### Privacidade das inscrições

O arquivo `subscribers.json` guarda o chat ID de cada inscrito junto com o que
ele monitora, e precisa ser commitado para sobreviver entre as rodadas do
Actions. Como o repositório é **público**, ele é gravado criptografado.

Gere a chave uma vez:

```
python tools/gerar_chave.py
```

e guarde o mesmo valor em dois lugares: `SUBSCRIBERS_KEY` no
`monitor_config.env` e nos Secrets do repositório. Sem a chave o monitor ainda
funciona, mas grava a lista em texto puro e avisa no log — o que só é aceitável
rodando localmente. Trocar a chave depois torna as inscrições ilegíveis e as
pessoas precisam se inscrever de novo.

Quem bloqueia o bot é removido automaticamente na primeira tentativa de envio.

## Configuração

Todas as opções ficam no `monitor_config.env` (local) ou nos Secrets/Variables
(Actions). O arquivo `monitor_config.env.example` tem a lista completa comentada.

| Variável | Padrão | O que faz |
|---|---|---|
| `SOURCE_CHANNEL` | — | Username do canal fonte, sem `@` |
| `BOT_TOKEN` | — | Token do bot publicador |
| `DEST_CHAT_ID` | — | `@canal` ou ID numérico do destino |
| `DRY_RUN` | `false` | Simula sem publicar |
| `MAX_POSTS_PER_RUN` | `10` | Teto de publicações por rodada |
| `SEND_DELAY` | `4` | Segundos entre publicações |
| `BACKFILL` | `0` | Publicar as últimas N na primeira execução |
| `REQUIRE_LINK` | `true` | Descarta posts sem link |
| `ALLOW_KEYWORDS` | — | Se preenchido, só publica posts com essas palavras |
| `BLOCK_KEYWORDS` | — | Nunca publica posts com essas palavras |
| `MIN_PRICE` / `MAX_PRICE` | `0` | Faixa de preço em reais (0 = sem limite) |
| `FOOTER_TEXT` | — | Texto fixo no fim de cada post |
| `INCLUDE_SOURCE_LINK` | `false` | Link para a mensagem original |
| `ALERTS_ENABLED` | `true` | Liga os comandos e os alertas no privado |
| `SUBSCRIBERS_KEY` | — | Chave que criptografa as inscrições |

Palavras-chave ignoram acento e maiúsculas: `notebook` casa com `Notebook` e
`NOTEBÓOK`.

## Estrutura

```
run_monitor.py              uma rodada completa
monitor/
  config.py                 leitura e validação das variáveis
  source.py                 scraping do preview do canal
  formatter.py              HTML do preview → HTML da Bot API
  filters.py                palavras-chave, preço, deduplicação
  publisher.py              envio via Bot API, com retry e limite de taxa
  state.py                  memória entre execuções (state.json)
  inbox.py                  comandos recebidos no privado do bot
  subscriptions.py          inscrições de alerta, criptografadas
tools/get_chat_id.py        descobre o ID do canal de destino
tools/gerar_chave.py        gera a SUBSCRIBERS_KEY
legacy/telegram_monitor.py  versão antiga (Telethon + n8n), só referência
```

## Limitações conhecidas

- **Só canais públicos com preview ativo.** Canal privado exigiria voltar ao
  Telethon, com conta pessoal e arquivo de sessão.
- **Latência de minutos**, não instantânea (ver seção do `cron` acima).
- **Sem vídeos.** Posts com vídeo são repassados como texto; o canal fonte hoje
  só usa foto.
- **Links de afiliado são repassados como estão** — a comissão continua sendo do
  dono do canal fonte. Trocar por links seus exigiria reescrever as URLs, o que
  esbarra nas regras de cada programa de afiliados.

  ## Nomes dos desenvolvedores:
- Albert William Silva Cunha
- Amanda Albuquerque Silva
- Filipe José
- Laís Bembo de Freitas
  ## Como contribuir

1. Crie uma branch a partir da `main`
2. Faça suas alterações
3. Abra um Pull Request descrevendo o que foi feito
