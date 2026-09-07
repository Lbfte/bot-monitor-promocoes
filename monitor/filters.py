"""Filtros de conteúdo e deduplicação."""

import hashlib
import logging
import re
import unicodedata
from urllib.parse import urlparse

log = logging.getLogger("monitor.filters")

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
# Preços em português: "R$ 61", "R$ 1.234,56", "R$61,90"
PRICE_RE = re.compile(r"R\$\s*(\d[\d.\s]*(?:,\d{1,2})?)", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
STORE_DOMAINS = {
    "amazon": ("amazon.com", "amazon.com.br", "amzn.to"),
    "mercadolivre": ("mercadolivre.com", "mercadolivre.com.br", "meli.la"),
    "shopee": ("shopee.com", "shopee.com.br", "shope.ee"),
    "aliexpress": ("aliexpress.com", "s.click.aliexpress"),
    "magalu": ("magalu.com",),
}


def normalize(text: str) -> str:
    """Minúsculas, sem acento — para comparar palavras-chave de forma tolerante."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text)


def detect_store(texto: str) -> str | None:
    """Devolve a loja identificada pelo domínio de um link no texto."""
    for url in extract_urls(texto):
        hostname = (urlparse(url).hostname or "").casefold().rstrip(".")
        for store, domains in STORE_DOMAINS.items():
            if any(hostname == domain or hostname.endswith(f".{domain}") for domain in domains):
                return store
    return None


def extract_price(text: str) -> float | None:
    """Devolve o primeiro preço encontrado no texto, em reais."""
    match = PRICE_RE.search(text)
    if not match:
        return None
    raw = match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def fingerprint(post) -> str:
    """
    Identidade do conteúdo, usada para não repostar a mesma promoção duas vezes.

    Combina o texto sem pontuação/emoji com os links: o mesmo produto reposto
    dias depois com a mesma descrição e o mesmo link gera a mesma impressão
    digital, mesmo tendo id de mensagem diferente.
    """
    body = NON_ALNUM_RE.sub("", normalize(post.text))
    links = "|".join(sorted(set(extract_urls(post.text))))
    return hashlib.sha1(f"{body}||{links}".encode("utf-8")).hexdigest()[:16]


def should_publish(post, cfg) -> tuple[bool, str]:
    """Decide se um post passa nos filtros. Devolve (aprovado, motivo)."""
    text = normalize(post.text)

    if cfg.require_link and not extract_urls(post.text):
        return False, "sem link"

    if cfg.block_keywords:
        for word in cfg.block_keywords:
            if normalize(word) in text:
                return False, f"palavra bloqueada: '{word}'"

    if cfg.allow_keywords:
        if not any(normalize(word) in text for word in cfg.allow_keywords):
            return False, "nenhuma palavra-chave permitida encontrada"

    if cfg.min_price or cfg.max_price:
        price = extract_price(post.text)
        if price is None:
            return False, "preço não identificado (filtro de preço ativo)"
        if cfg.min_price and price < cfg.min_price:
            return False, f"preço R$ {price:.2f} abaixo do mínimo"
        if cfg.max_price and price > cfg.max_price:
            return False, f"preço R$ {price:.2f} acima do máximo"

    return True, "ok"
