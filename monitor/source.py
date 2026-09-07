"""
Leitura do canal fonte pelo preview público (https://t.me/s/<canal>).

Por que não usar a conta pessoal (Telethon/MTProto):
  - o preview é HTTP puro: não precisa de API_ID, API_HASH, telefone nem
    arquivo de sessão — o que torna a execução em nuvem descartável trivial;
  - automatizar a conta pessoal viola os termos do Telegram e arrisca banimento.

Limitação: só funciona para canal público com preview ativo, e devolve as
últimas ~20 mensagens por página.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from . import formatter

log = logging.getLogger("monitor.source")

PREVIEW_URL = "https://t.me/s/{channel}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
BG_IMAGE_RE = re.compile(r"background-image\s*:\s*url\('([^']+)'\)")


@dataclass
class Post:
    """Uma mensagem do canal fonte."""

    id: int
    url: str
    html: str                              # texto em HTML da Bot API
    text: str                              # texto puro, para filtros
    photos: list[str] = field(default_factory=list)
    date: datetime | None = None
    has_video: bool = False

    @property
    def is_empty(self) -> bool:
        return not self.text and not self.photos


def fetch(channel: str, timeout: int = 20) -> list[Post]:
    """Baixa a página do canal e devolve os posts em ordem crescente de id."""
    url = PREVIEW_URL.format(channel=channel)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)

    if resp.status_code == 404:
        raise RuntimeError(
            f"Canal @{channel} não encontrado. Confira o username (sem @)."
        )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    blocks = soup.select("div.tgme_widget_message[data-post]")

    if not blocks:
        raise RuntimeError(
            f"Nenhuma mensagem encontrada em @{channel}. O canal pode ser privado "
            "ou estar com o preview desativado (Configurações do canal → "
            "'Sign Messages'/preview público)."
        )

    posts = []
    for block in blocks:
        post = _parse(block, channel)
        if post and not post.is_empty:
            posts.append(post)

    posts.sort(key=lambda p: p.id)
    log.info(f"@{channel}: {len(posts)} mensagens lidas (ids {posts[0].id}–{posts[-1].id})")
    return posts


def _parse(block: Tag, channel: str) -> Post | None:
    data_post = block.get("data-post", "")
    try:
        post_id = int(data_post.split("/")[-1])
    except (ValueError, IndexError):
        log.warning(f"Ignorando bloco com data-post inválido: {data_post!r}")
        return None

    text_div = block.select_one("div.tgme_widget_message_text.js-message_text")
    html = formatter.to_bot_html(text_div) if text_div else ""
    text = formatter.plain_text(text_div) if text_div else ""

    photos = []
    for wrap in block.select("a.tgme_widget_message_photo_wrap"):
        match = BG_IMAGE_RE.search(wrap.get("style", ""))
        if match:
            photos.append(match.group(1))

    time_tag = block.select_one("time[datetime]")
    date = None
    if time_tag:
        try:
            date = datetime.fromisoformat(time_tag["datetime"])
        except ValueError:
            pass

    return Post(
        id=post_id,
        url=f"https://t.me/{channel}/{post_id}",
        html=html,
        text=text,
        photos=photos,
        date=date,
        has_video=bool(block.select_one("video, .tgme_widget_message_video_wrap")),
    )
