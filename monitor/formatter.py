"""
Converte o HTML do preview web do Telegram para o HTML aceito pela Bot API.

O preview (t.me/s/canal) devolve o texto já formatado, mas com detalhes que a
Bot API não entende — principalmente os emojis, que vêm embrulhados em
<i class="emoji"><b>🔥</b></i>. Se repassássemos isso cru, cada emoji viraria
texto em negrito e itálico.

Tags aceitas pela Bot API: b, i, u, s, a, code, pre, blockquote, tg-spoiler.
"""

from html import escape

from bs4 import NavigableString, Tag

# Mapeia a tag do preview para a tag equivalente na Bot API.
TAG_MAP = {
    "b": "b", "strong": "b",
    "i": "i", "em": "i",
    "u": "u", "ins": "u",
    "s": "s", "strike": "s", "del": "s",
    "code": "code",
    "pre": "pre",
    "blockquote": "blockquote",
}

# Dentro dessas tags a Bot API não aceita formatação aninhada.
PLAIN_ONLY = {"code", "pre"}

MESSAGE_LIMIT = 4096
CAPTION_LIMIT = 1024


def to_bot_html(node: Tag) -> str:
    """Converte a árvore HTML do preview em HTML da Bot API."""
    return _render(node).strip()


def _render(node) -> str:
    if isinstance(node, NavigableString):
        return escape(str(node), quote=False)
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    classes = node.get("class") or []

    # Emoji: <i class="emoji"><b>🔥</b></i> → apenas o caractere.
    if "emoji" in classes:
        return escape(node.get_text(), quote=False)

    if name == "br":
        return "\n"

    if name == "a":
        href = (node.get("href") or "").strip()
        inner = _children(node)
        if not href:
            return inner
        return f'<a href="{escape(href, quote=True)}">{inner}</a>'

    if "tg-spoiler" in classes or name == "tg-spoiler":
        return f"<tg-spoiler>{_children(node)}</tg-spoiler>"

    mapped = TAG_MAP.get(name)
    if mapped:
        inner = escape(node.get_text(), quote=False) if mapped in PLAIN_ONLY else _children(node)
        if not inner.strip():
            return inner
        return f"<{mapped}>{inner}</{mapped}>"

    # Qualquer outra tag (span, div...) é descartada, mas o conteúdo continua.
    return _children(node)


def _children(node: Tag) -> str:
    return "".join(_render(child) for child in node.children)


def plain_text(node: Tag) -> str:
    """Texto puro da mensagem, usado para filtros e deduplicação."""
    parts = []
    for child in node.descendants:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif isinstance(child, Tag) and child.name == "br":
            parts.append("\n")
    return "".join(parts).strip()


def truncate(html_text: str, limit: int) -> str:
    """
    Corta o HTML no limite de caracteres sem quebrar uma tag no meio.

    Não é um cortador perfeito de HTML: ele só evita terminar dentro de '<...>'
    e fecha o que ficou aberto. Serve para o caso raro de post gigante.
    """
    if len(html_text) <= limit:
        return html_text

    cut = html_text[: limit - 1]
    # Não terminar no meio de uma tag.
    last_open = cut.rfind("<")
    last_close = cut.rfind(">")
    if last_open > last_close:
        cut = cut[:last_open]

    # Fecha as tags que ficaram abertas.
    open_tags = []
    for chunk in cut.split("<")[1:]:
        tag = chunk.split(">")[0]
        if tag.startswith("/"):
            name = tag[1:].strip()
            if name in open_tags:
                open_tags.remove(name)
        elif ">" in chunk:
            name = tag.split(" ")[0].strip("/")
            if name:
                open_tags.append(name)
    for name in reversed(open_tags):
        cut += f"</{name}>"
    return cut + "…"
