"""
Publicação no canal de destino via Bot API.

As imagens são baixadas do CDN do Telegram e reenviadas como upload. Seria mais
econômico passar a URL e deixar o Telegram buscar sozinho, mas o servidor da
Bot API recusa as URLs assinadas do cdn*.telesco.pe com "failed to get HTTP URL
content" — então o upload é o único caminho que funciona de verdade.
"""

import json
import logging
import time

import requests

from .formatter import CAPTION_LIMIT, MESSAGE_LIMIT, truncate

log = logging.getLogger("monitor.publisher")

API_URL = "https://api.telegram.org/bot{token}/{method}"
MAX_ATTEMPTS = 3

# Limite de upload de foto da Bot API.
PHOTO_SIZE_LIMIT = 10 * 1024 * 1024


class Publisher:
    def __init__(self, token: str, chat_id: str, dry_run: bool = False):
        self.token = token
        self.chat_id = chat_id
        self.dry_run = dry_run
        self.session = requests.Session()
        # Guarda a última mensagem de erro da API, para quem chamou decidir o
        # que fazer (ex: remover a inscrição de quem bloqueou o bot).
        self.last_error = ""

    # ─── Chamada crua ───────────────────────────────────
    def _call(self, method: str, payload: dict, files: dict | None = None) -> dict | None:
        """
        Chama a Bot API tratando limite de taxa e falhas temporárias.

        Com `files`, a chamada vira multipart (upload de imagem) e os campos
        precisam ir como formulário; sem ela, JSON é mais simples e legível.
        """
        url = API_URL.format(token=self.token, method=method)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if files:
                    resp = self.session.post(url, data=payload, files=files, timeout=60)
                else:
                    resp = self.session.post(url, json=payload, timeout=30)
            except requests.RequestException as e:
                log.warning(f"{method}: falha de rede ({e}) — tentativa {attempt}/{MAX_ATTEMPTS}")
                time.sleep(2 * attempt)
                continue

            try:
                data = resp.json()
            except ValueError:
                log.error(f"{method}: resposta não é JSON (HTTP {resp.status_code})")
                return None

            if data.get("ok"):
                return data["result"]

            description = data.get("description", "erro desconhecido")

            # 429: o Telegram diz exatamente quantos segundos esperar.
            if resp.status_code == 429:
                wait = data.get("parameters", {}).get("retry_after", 5)
                log.warning(f"{method}: limite de taxa, aguardando {wait}s")
                time.sleep(wait + 1)
                continue

            if resp.status_code >= 500:
                log.warning(f"{method}: erro do servidor ({description}) — tentativa {attempt}")
                time.sleep(2 * attempt)
                continue

            # 400/403: erro nosso (chat errado, bot não é admin, HTML inválido).
            # Repetir não adianta.
            self.last_error = description
            log.error(f"{method}: {description}")
            return None

        log.error(f"{method}: desistindo após {MAX_ATTEMPTS} tentativas")
        return None

    # ─── Verificação ────────────────────────────────────
    def check_access(self) -> bool:
        """Confere se o bot existe e consegue enxergar o canal de destino."""
        me = self._call("getMe", {})
        if not me:
            log.error("BOT_TOKEN inválido — o Telegram não reconheceu o token.")
            return False
        log.info(f"Bot: @{me.get('username')} ({me.get('first_name')})")

        chat = self._call("getChat", {"chat_id": self.chat_id})
        if not chat:
            log.error(
                f"Não consegui acessar {self.chat_id}. Verifique se o bot foi "
                "adicionado ao canal COMO ADMINISTRADOR."
            )
            return False
        log.info(f"Destino: {chat.get('title')} ({chat.get('type')})")
        return True

    # ─── Conversa privada ───────────────────────────────
    def get_updates(self, offset: int) -> list[dict]:
        """Busca os comandos que chegaram no privado desde a última rodada."""
        resultado = self._call("getUpdates", {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": ["message"],
        })
        return resultado or []

    def send_to(self, chat_id: int, html: str) -> bool:
        """Manda uma mensagem no privado de alguém."""
        self.last_error = ""
        resultado = self._call("sendMessage", {
            "chat_id": chat_id,
            "text": truncate(html, MESSAGE_LIMIT),
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        })
        return resultado is not None

    @property
    def blocked_by_user(self) -> bool:
        """O último erro foi 'a pessoa bloqueou o bot' ou 'conversa não existe'?"""
        erro = self.last_error.casefold()
        return "blocked" in erro or "chat not found" in erro or "user is deactivated" in erro

    # ─── Envio ──────────────────────────────────────────
    def publish(self, html: str, photos: list[str]) -> int | None:
        """
        Publica um post no canal.

        Devolve o message_id da mensagem publicada (0 em simulação) ou None se
        nada chegou. O id serve para montar o link do post nos alertas.
        """
        if self.dry_run:
            preview = html.replace("\n", " ⏎ ")[:120]
            log.info(f"  [DRY-RUN] {len(photos)} foto(s) | {preview}")
            return 0

        if not photos:
            return self._send_text(html)

        if len(photos) == 1:
            return self._send_photo(photos[0], html)

        return self._send_album(photos, html)

    def _send_text(self, html: str) -> int | None:
        result = self._call("sendMessage", {
            "chat_id": self.chat_id,
            "text": truncate(html, MESSAGE_LIMIT),
            "parse_mode": "HTML",
        })
        return result["message_id"] if result else None

    def _download(self, url: str) -> bytes | None:
        """
        Baixa a imagem do CDN do Telegram.

        Passar a URL direto para a Bot API não funciona: o servidor do Telegram
        recusa as URLs assinadas do cdn*.telesco.pe ("failed to get HTTP URL
        content"). Baixar aqui e subir os bytes é o caminho que funciona.
        """
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"  Falha ao baixar imagem: {e}")
            return None

        if len(resp.content) > PHOTO_SIZE_LIMIT:
            log.warning(f"  Imagem grande demais ({len(resp.content) // 1024} KB)")
            return None
        return resp.content

    def _send_photo(self, photo: str, html: str) -> int | None:
        conteudo = self._download(photo)
        if conteudo is None:
            log.warning("  Sem imagem — enviando só o texto")
            return self._send_text(html)

        # Legenda de foto cabe 1024 caracteres. Passando disso, a foto vai sem
        # legenda e o texto inteiro vem logo atrás, em vez de ser cortado.
        fits = len(html) <= CAPTION_LIMIT
        payload = {"chat_id": self.chat_id}
        if fits:
            payload.update({"caption": html, "parse_mode": "HTML"})

        result = self._call(
            "sendPhoto", payload,
            files={"photo": ("foto.jpg", conteudo, "image/jpeg")},
        )
        if result is None:
            log.warning("  Foto recusada pelo Telegram — enviando só o texto")
            return self._send_text(html)

        if not fits:
            self._send_text(html)
        return result["message_id"]

    def _send_album(self, photos: list[str], html: str) -> int | None:
        baixadas = [(url, self._download(url)) for url in photos[:10]]
        baixadas = [(url, dados) for url, dados in baixadas if dados]

        if not baixadas:
            log.warning("  Nenhuma imagem baixada — enviando só o texto")
            return self._send_text(html)
        if len(baixadas) == 1:
            return self._send_photo(baixadas[0][0], html)

        fits = len(html) <= CAPTION_LIMIT
        media, files = [], {}
        for indice, (_, dados) in enumerate(baixadas):
            nome = f"foto{indice}"
            media.append({"type": "photo", "media": f"attach://{nome}"})
            files[nome] = (f"{nome}.jpg", dados, "image/jpeg")
        if fits:
            media[0]["caption"] = html
            media[0]["parse_mode"] = "HTML"

        result = self._call(
            "sendMediaGroup",
            {"chat_id": self.chat_id, "media": json.dumps(media)},
            files=files,
        )
        if result is None:
            log.warning("  Álbum recusado — tentando com a primeira foto apenas")
            return self._send_photo(baixadas[0][0], html)

        if not fits:
            self._send_text(html)
        return result[0]["message_id"]
