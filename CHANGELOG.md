# Changelog

Todas as alterações notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-09-08

### Adicionado
- **Leitura pelo preview público**: Raspagem das publicações diretamente da página de preview pública do Telegram (`https://t.me/s/...`) em HTML simples, dispensando Telethon, arquivos de sessão, `API_ID` e `API_HASH`.
- **Repasse com imagem**: Publicação das ofertas no canal de destino com fotos e legendas ricas formatadas em HTML via Telegram Bot API.
- **Identificação de lojas parceiras**: Detecção automática da loja de origem através do domínio do link com inserção da hashtag correspondente (ex.: `#amazon`, `#magalu`, `#mercadolivre`, `#shopee`).
- **Filtros por palavra-chave**: Mecanismo de filtragem baseado em termos permitidos (`ALLOW_KEYWORDS`) e termos bloqueados (`BLOCK_KEYWORDS`), normalizados sem acento e insensíveis a maiúsculas.
- **Filtros por preço**: Extração de valores monetários em reais (`R$`) e validação de limites mínimo (`MIN_PRICE`) e máximo (`MAX_PRICE`).
- **Deduplicação**: Geração de `fingerprint` única baseada no texto normalizado e nos links, garantindo que promoções repetidas não sejam republicadas.
- **Alertas personalizados no privado**: Sistema de monitoramento individual via chat privado do bot, com os comandos `/monitorar <termo> [preço]`, `/parar`, `/lista`, `/status` e `/ajuda`.
- **Criptografia de inscrições**: Proteção da lista de chats inscritos (`subscribers.json`) através de criptografia simétrica com chave `SUBSCRIBERS_KEY`.
- **Execução no GitHub Actions**: Workflow agendado em nuvem (`.github/workflows/monitor.yml`) rodando a cada 5 minutos de forma autônoma e com persistência de estado via commit automático.
- **Testes automatizados e CI**: Suíte de testes unitários desenvolvida com `pytest` (`tests/test_filters.py`, `tests/test_inbox.py`) e pipeline de CI (`.github/workflows/testes.yml`).
- **Padronização de issues**: Template de melhorias para o repositório em `.github/ISSUE_TEMPLATE/melhoria.md`.
