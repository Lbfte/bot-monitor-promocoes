"""
Telegram Channel Monitor — Substituto do Junction Bot
=====================================================
Monitora um canal público do Telegram e repassa as mensagens
para o grupo ponte onde o bot do n8n está escutando.

Usa Telethon (MTProto API) para atuar como sua conta pessoal,
sem limites de mensagens, sem atrasos, sem propagandas.

Primeiro uso: Vai pedir seu número de telefone e código de
verificação (SMS ou app). Depois disso, a sessão fica salva
no arquivo 'monitor_session.session' e não pede mais.
"""

import asyncio
import os
import sys
import logging
import re
from datetime import datetime

from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    ChannelPrivateError,
)
from dotenv import load_dotenv
import aiohttp

# ─── Configuração ───────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "monitor_config.env"))

API_ID = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "SamuelF3lipePromo")
DEST_GROUP_ID = os.getenv("DEST_GROUP_ID", "")

# ─── Logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("monitor")

# Silencia logs verbosos do Telethon
logging.getLogger("telethon").setLevel(logging.WARNING)

# ─── Validação ──────────────────────────────────────────
def validate_config():
    """Verifica se todas as variáveis obrigatórias estão preenchidas."""
    errors = []
    if not API_ID:
        errors.append("TELEGRAM_API_ID não configurado")
    if not API_HASH:
        errors.append("TELEGRAM_API_HASH não configurado")
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN não configurado")
    if not DEST_GROUP_ID:
        errors.append("DEST_GROUP_ID não configurado")

    if errors:
        log.error("=" * 50)
        log.error("CONFIGURAÇÃO INCOMPLETA!")
        log.error("Edite o arquivo: monitor_config.env")
        log.error("-" * 50)
        for e in errors:
            log.error(f"  ✗ {e}")
        log.error("=" * 50)
        log.error("")
        log.error("Para obter API_ID e API_HASH:")
        log.error("  1. Acesse https://my.telegram.org")
        log.error("  2. Faça login com seu número")
        log.error("  3. Vá em 'API development tools'")
        log.error("  4. Crie uma aplicação (nome qualquer)")
        log.error("  5. Copie api_id e api_hash")
        log.error("")
        log.error("Para obter DEST_GROUP_ID:")
        log.error("  1. Adicione @get_id_bot ao seu grupo")
        log.error("  2. Ele responde com o Chat ID")
        log.error("  3. Cole no monitor_config.env")
        return False
    return True


# ─── Bot API Helper ─────────────────────────────────────
BOT_API_URL = "https://api.telegram.org/bot{token}/{method}"


async def bot_send_message(session: aiohttp.ClientSession, text: str):
    """Envia uma mensagem para o grupo destino via Bot API."""
    url = BOT_API_URL.format(token=BOT_TOKEN, method="sendMessage")
    payload = {
        "chat_id": int(DEST_GROUP_ID),
        "text": text,
    }
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            if not data.get("ok"):
                log.warning(f"Bot API erro: {data.get('description', 'desconhecido')}")
                return False
            return True
    except Exception as e:
        log.error(f"Falha ao enviar via Bot API: {e}")
        return False


async def bot_send_photo(session: aiohttp.ClientSession, photo_bytes: bytes, caption: str = ""):
    """Envia uma foto com legenda para o grupo destino via Bot API."""
    url = BOT_API_URL.format(token=BOT_TOKEN, method="sendPhoto")
    data = aiohttp.FormData()
    data.add_field("chat_id", str(DEST_GROUP_ID))
    data.add_field("photo", photo_bytes, filename="photo.jpg", content_type="image/jpeg")
    if caption:
        data.add_field("caption", caption)
    try:
        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            result = await resp.json()
            if not result.get("ok"):
                log.warning(f"Bot API erro (foto): {result.get('description', 'desconhecido')}")
                return False
            return True
    except Exception as e:
        log.error(f"Falha ao enviar foto via Bot API: {e}")
        return False


# ─── Estatísticas ───────────────────────────────────────
stats = {
    "total": 0,
    "sent": 0,
    "errors": 0,
    "started_at": None,
}


async def resolve_short_urls(session: aiohttp.ClientSession, text: str) -> str:
    """Detecta e resolve links encurtados no texto seguindo redirecionamentos."""
    if not text:
        return text
    
    # Domínios comuns de encurtadores usados em promoções
    short_domains = [r'amzn\.to', r'shope\.ee', r's\.shopee', r'ali\.ski', r's\.click\.aliexpress', r'a\.aliexpress', r'meli\.la', r'bit\.ly', r't\.co', r'tinyurl\.com', r'cutt\.ly', r'is\.gd']
    
    # Regex para encontrar URLs
    url_pattern = re.compile(r'(https?://[^\s<>"\'()]+)', re.IGNORECASE)
    urls = url_pattern.findall(text)
    
    modified_text = text
    for url in urls:
        is_short = any(re.search(domain, url, re.IGNORECASE) for domain in short_domains)
        if is_short:
            try:
                # Tenta HEAD primeiro (mais rápido)
                async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resolved_url = str(resp.url)
                    status = resp.status
                
                # Se der erro no HEAD, tenta GET
                if status >= 400:
                    async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp2:
                        resolved_url = str(resp2.url)

                if resolved_url != url:
                    modified_text = modified_text.replace(url, resolved_url)
                    log.info(f"  🔗 Link resolvido: {url} -> {resolved_url}")
            except Exception as e:
                log.warning(f"  ⚠️ Falha ao resolver link {url}: {e}")
                
    return modified_text


# ─── Main ───────────────────────────────────────────────
async def main():
    if not validate_config():
        sys.exit(1)

    session_path = os.path.join(SCRIPT_DIR, "monitor_session")
    client = TelegramClient(session_path, int(API_ID), API_HASH)

    log.info("Conectando ao Telegram...")
    await client.start()

    me = await client.get_me()
    log.info(f"Logado como: {me.first_name} (@{me.username or 'sem username'})")

    # Resolve o canal fonte
    try:
        source_entity = await client.get_entity(SOURCE_CHANNEL)
        log.info(f"Monitorando canal: {source_entity.title} (@{SOURCE_CHANNEL})")
    except ChannelPrivateError:
        log.error(f"Não foi possível acessar @{SOURCE_CHANNEL}. Você precisa ser membro do canal.")
        await client.disconnect()
        sys.exit(1)
    except Exception as e:
        log.error(f"Erro ao resolver canal @{SOURCE_CHANNEL}: {e}")
        await client.disconnect()
        sys.exit(1)

    stats["started_at"] = datetime.now()
    http_session = aiohttp.ClientSession()

    log.info("=" * 50)
    log.info("  MONITOR ATIVO — Esperando promoções...")
    log.info(f"  Fonte:   @{SOURCE_CHANNEL}")
    log.info(f"  Destino: Grupo {DEST_GROUP_ID}")
    log.info("  Ctrl+C para parar")
    log.info("=" * 50)

    @client.on(events.NewMessage(chats=source_entity))
    async def on_new_message(event):
        """Chamado toda vez que uma mensagem nova chega no canal fonte."""
        stats["total"] += 1
        text = event.raw_text
        has_photo = event.photo is not None

        # Ignora mensagens vazias sem texto e sem foto
        if not text and not has_photo:
            log.info(f"#{stats['total']} Mensagem sem texto/foto — ignorada")
            return

        # Resolve links encurtados
        if text:
            text = await resolve_short_urls(http_session, text)

        # Prévia do texto no log (primeiras 80 chars)
        preview = (text[:80] + "...") if len(text) > 80 else text
        preview = preview.replace("\n", " ")
        log.info(f"#{stats['total']} Nova mensagem: {preview}")

        success = False

        if has_photo:
            # Baixa a foto e envia com legenda
            try:
                photo_bytes = await client.download_media(event.photo, bytes)
                success = await bot_send_photo(http_session, photo_bytes, caption=text or "")
            except Exception as e:
                log.error(f"Erro ao baixar/enviar foto: {e}")
                # Fallback: tenta enviar só o texto
                if text:
                    success = await bot_send_message(http_session, text)
        else:
            # Envia só o texto
            success = await bot_send_message(http_session, text)

        if success:
            stats["sent"] += 1
            log.info(f"  ✓ Repassada ({stats['sent']}/{stats['total']})")
        else:
            stats["errors"] += 1
            log.warning(f"  ✗ Falha ao repassar ({stats['errors']} erros)")

    # Mantém rodando
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        pass
    finally:
        await http_session.close()
        await client.disconnect()
        log.info("")
        log.info("=" * 50)
        log.info("  MONITOR ENCERRADO")
        log.info(f"  Total recebidas: {stats['total']}")
        log.info(f"  Repassadas:      {stats['sent']}")
        log.info(f"  Erros:           {stats['errors']}")
        log.info("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Encerrado pelo usuário.")
