import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from monitor.config import Config
from monitor.filters import extract_price, fingerprint, should_publish
from monitor.source import Post


class TestExtractPrice:
    def test_extract_price_simple(self):
        assert extract_price("R$ 61") == 61.0

    def test_extract_price_formatted(self):
        assert extract_price("R$ 1.234,56") == 1234.56

    def test_extract_price_without_price(self):
        assert extract_price("Promoção imperdível sem valor no texto") is None


class TestShouldPublish:
    def test_reject_post_without_link(self):
        post = Post(
            id=1,
            url="https://t.me/canal/1",
            html="<p>Promoção sem link</p>",
            text="Promoção sem link no texto",
        )
        cfg = Config(require_link=True)
        approved, reason = should_publish(post, cfg)
        assert approved is False
        assert reason == "sem link"

    def test_reject_post_with_blocked_keyword(self):
        post = Post(
            id=2,
            url="https://t.me/canal/2",
            html="<p>Confira cupom https://exemplo.com</p>",
            text="Confira esta promoção com cupom https://exemplo.com",
        )
        cfg = Config(require_link=True, block_keywords=["cupom"])
        approved, reason = should_publish(post, cfg)
        assert approved is False
        assert "palavra bloqueada" in reason

    def test_reject_post_with_price_above_max(self):
        post = Post(
            id=3,
            url="https://t.me/canal/3",
            html="<p>Notebook Gamer R$ 5.000,00 https://exemplo.com</p>",
            text="Notebook Gamer R$ 5.000,00 https://exemplo.com",
        )
        cfg = Config(require_link=True, max_price=3000.0)
        approved, reason = should_publish(post, cfg)
        assert approved is False
        assert "acima do máximo" in reason


class TestFingerprint:
    def test_same_text_and_link_gives_same_fingerprint(self):
        post1 = Post(
            id=10,
            url="https://t.me/canal/10",
            html="<p>Promoção R$ 99 https://loja.com/item</p>",
            text="Promoção R$ 99 https://loja.com/item",
        )
        post2 = Post(
            id=20,
            url="https://t.me/canal/20",
            html="<p>Promoção R$ 99 https://loja.com/item</p>",
            text="Promoção R$ 99 https://loja.com/item",
        )
        assert fingerprint(post1) == fingerprint(post2)

    def test_different_prices_give_different_fingerprints(self):
        post1 = Post(
            id=10,
            url="https://t.me/canal/10",
            html="<p>Promoção R$ 99 https://loja.com/item</p>",
            text="Promoção R$ 99 https://loja.com/item",
        )
        post2 = Post(
            id=11,
            url="https://t.me/canal/11",
            html="<p>Promoção R$ 120 https://loja.com/item</p>",
            text="Promoção R$ 120 https://loja.com/item",
        )
        assert fingerprint(post1) != fingerprint(post2)
