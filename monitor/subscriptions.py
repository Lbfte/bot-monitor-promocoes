"""
Inscrições de alerta: quem quer ser avisado sobre quais palavras.

O arquivo vai commitado no repositório para sobreviver entre as rodadas do
GitHub Actions — e como o repositório é público, ele é criptografado. Sem isso,
qualquer pessoa leria a lista de chat IDs e os interesses de cada inscrito.

A criptografia é ligada definindo SUBSCRIBERS_KEY (gere com
`python tools/gerar_chave.py`). Sem a chave o arquivo é gravado em texto puro,
o que só é aceitável rodando localmente.
"""

import json
import logging
import os
import re

from .filters import extract_price, normalize

log = logging.getLogger("monitor.subs")

MAX_KEYWORDS_POR_PESSOA = 20
# Duas letras já bastam para produtos reais como "tv", "pc" e "hd". O risco de
# casamento acidental é baixo porque a busca exige início de palavra.
MIN_TAMANHO_PALAVRA = 2


def matches(texto_normalizado: str, palavra: str) -> bool:
    """
    A palavra casa se aparecer no início de uma palavra do texto.

    Início de palavra em vez de trecho solto porque 'tv' casaria com 'motiva';
    e sem exigir o fim da palavra para que 'notebook' também pegue 'notebooks'.
    """
    return re.search(rf"\b{re.escape(normalize(palavra))}", texto_normalizado) is not None


class Subscriptions:
    def __init__(self, path: str, key: str = ""):
        self.path = path
        self.key = key
        self.dados: dict[str, list[dict]] = {}
        self._load()

    # ─── Persistência ───────────────────────────────────
    def _fernet(self):
        if not self.key:
            return None
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            log.error("SUBSCRIBERS_KEY definida mas o pacote 'cryptography' não está instalado.")
            return None
        try:
            return Fernet(self.key.encode())
        except (ValueError, TypeError):
            log.error("SUBSCRIBERS_KEY inválida — gere uma com: python tools/gerar_chave.py")
            return None

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as fp:
            bruto = fp.read()
        if not bruto.strip():
            return

        fernet = self._fernet()
        if fernet:
            try:
                bruto = fernet.decrypt(bruto)
            except Exception:
                log.error(
                    "Não consegui descriptografar as inscrições. A SUBSCRIBERS_KEY "
                    "mudou? As inscrições anteriores ficam inacessíveis."
                )
                return

        try:
            self.dados = json.loads(bruto.decode("utf-8"))
            total = sum(len(v) for v in self.dados.values())
            log.info(f"Inscrições: {len(self.dados)} pessoa(s), {total} palavra(s)")
        except (json.JSONDecodeError, UnicodeDecodeError):
            log.error("Arquivo de inscrições ilegível — talvez falte a SUBSCRIBERS_KEY.")

    def save(self):
        conteudo = json.dumps(self.dados, ensure_ascii=False, indent=2).encode("utf-8")
        fernet = self._fernet()
        if fernet:
            conteudo = fernet.encrypt(conteudo)
        elif self.dados:
            log.warning("Gravando inscrições SEM criptografia (SUBSCRIBERS_KEY não definida).")

        tmp = f"{self.path}.tmp"
        with open(tmp, "wb") as fp:
            fp.write(conteudo)
        os.replace(tmp, self.path)

    # ─── Operações ──────────────────────────────────────
    def add(self, chat_id: int, palavra: str, teto: float | None) -> tuple[bool, str]:
        palavra = palavra.strip().casefold()
        if len(palavra) < MIN_TAMANHO_PALAVRA:
            return False, f"A palavra precisa ter pelo menos {MIN_TAMANHO_PALAVRA} letras."

        lista = self.dados.setdefault(str(chat_id), [])
        if len(lista) >= MAX_KEYWORDS_POR_PESSOA:
            return False, f"Você já tem {MAX_KEYWORDS_POR_PESSOA} palavras. Remova alguma com /parar."

        for item in lista:
            if item["palavra"] == palavra:
                item["teto"] = teto
                self.save()
                return True, f"Atualizei <b>{palavra}</b>."

        lista.append({"palavra": palavra, "teto": teto})
        self.save()
        return True, f"Vou te avisar sobre <b>{palavra}</b>."

    def remove(self, chat_id: int, palavra: str) -> bool:
        palavra = palavra.strip().casefold()
        lista = self.dados.get(str(chat_id), [])
        antes = len(lista)
        self.dados[str(chat_id)] = [i for i in lista if i["palavra"] != palavra]
        if not self.dados[str(chat_id)]:
            self.dados.pop(str(chat_id), None)
        mudou = len(self.dados.get(str(chat_id), [])) < antes
        if mudou:
            self.save()
        return mudou

    def remove_chat(self, chat_id: int):
        """Remove todas as inscrições de alguém (usado quando o bot é bloqueado)."""
        if self.dados.pop(str(chat_id), None) is not None:
            self.save()

    def list_for(self, chat_id: int) -> list[dict]:
        return self.dados.get(str(chat_id), [])

    # ─── Correspondência ────────────────────────────────
    def match_post(self, post) -> list[tuple[int, str, float | None, float | None]]:
        """
        Devolve (chat_id, palavra, teto, preço) para cada inscrição que casa.

        Quando há teto mas o post não traz preço legível, o alerta é enviado
        mesmo assim: perder uma promoção é pior do que receber um aviso a mais.
        """
        texto = normalize(post.text)
        preco = extract_price(post.text)
        encontrados = []

        for chat_id, lista in self.dados.items():
            for item in lista:
                if not matches(texto, item["palavra"]):
                    continue
                teto = item.get("teto")
                if teto and preco is not None and preco > teto:
                    continue
                encontrados.append((int(chat_id), item["palavra"], teto, preco))

        return encontrados
