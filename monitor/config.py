"""
Configuração lida de variáveis de ambiente.

Localmente as variáveis vêm do arquivo monitor_config.env.
No GitHub Actions elas vêm dos Secrets do repositório.
"""

import os
import sys
import logging
from dataclasses import dataclass, field

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(SCRIPT_DIR, "monitor_config.env"))

log = logging.getLogger("monitor.config")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "sim", "yes", "y", "on")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        log.warning(f"{name}='{raw}' não é um número inteiro — usando {default}")
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip().replace(",", ".")
    try:
        return float(raw) if raw else default
    except ValueError:
        log.warning(f"{name}='{raw}' não é um número — usando {default}")
        return default


def _list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip().casefold() for item in raw.split(",") if item.strip()]


@dataclass
class Config:
    # --- Obrigatórios ---
    bot_token: str = ""
    dest_chat_id: str = ""
    source_channel: str = ""

    # --- Comportamento ---
    dry_run: bool = False
    max_posts_per_run: int = 10
    send_delay: float = 4.0
    backfill: int = 0
    state_file: str = ""

    # --- Alertas por palavra-chave ---
    alerts_enabled: bool = True
    subscribers_file: str = ""
    subscribers_key: str = ""

    # --- Filtros ---
    require_link: bool = True
    allow_keywords: list[str] = field(default_factory=list)
    block_keywords: list[str] = field(default_factory=list)
    min_price: float = 0.0
    max_price: float = 0.0

    # --- Aparência ---
    footer_text: str = ""
    include_source_link: bool = False

    def validate(self) -> list[str]:
        """Retorna a lista de problemas encontrados (vazia = tudo certo)."""
        errors = []
        if not self.source_channel:
            errors.append("SOURCE_CHANNEL não configurado (ex: SamuelF3lipePromo)")
        if not self.dry_run:
            if not self.bot_token:
                errors.append("BOT_TOKEN não configurado (peça um ao @BotFather)")
            elif ":" not in self.bot_token:
                errors.append("BOT_TOKEN parece inválido (formato: 123456789:AAE...)")
            if not self.dest_chat_id:
                errors.append("DEST_CHAT_ID não configurado (ex: @meucanal ou -1001234567890)")
        if self.max_posts_per_run < 1:
            errors.append("MAX_POSTS_PER_RUN precisa ser no mínimo 1")
        return errors

    def warnings(self) -> list[str]:
        """Problemas que não impedem a execução, mas o usuário precisa saber."""
        avisos = []
        if self.alerts_enabled and not self.subscribers_key:
            avisos.append(
                "SUBSCRIBERS_KEY não definida: as inscrições serão gravadas em "
                "texto puro. Num repositório público isso expõe os chat IDs. "
                "Gere uma chave com: python tools/gerar_chave.py"
            )
        return avisos


def from_env() -> Config:
    """Monta a configuração lendo as variáveis de ambiente na hora da chamada."""
    return Config(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        dest_chat_id=os.getenv("DEST_CHAT_ID", "").strip(),
        source_channel=os.getenv("SOURCE_CHANNEL", "").strip().lstrip("@"),
        dry_run=_bool("DRY_RUN", False),
        max_posts_per_run=_int("MAX_POSTS_PER_RUN", 10),
        send_delay=_float("SEND_DELAY", 4.0),
        backfill=_int("BACKFILL", 0),
        state_file=os.getenv("STATE_FILE", "") or os.path.join(SCRIPT_DIR, "state.json"),
        alerts_enabled=_bool("ALERTS_ENABLED", True),
        subscribers_file=(
            os.getenv("SUBSCRIBERS_FILE", "") or os.path.join(SCRIPT_DIR, "subscribers.json")
        ),
        subscribers_key=os.getenv("SUBSCRIBERS_KEY", "").strip(),
        require_link=_bool("REQUIRE_LINK", True),
        allow_keywords=_list("ALLOW_KEYWORDS"),
        block_keywords=_list("BLOCK_KEYWORDS"),
        min_price=_float("MIN_PRICE", 0.0),
        max_price=_float("MAX_PRICE", 0.0),
        footer_text=os.getenv("FOOTER_TEXT", "").strip(),
        include_source_link=_bool("INCLUDE_SOURCE_LINK", False),
    )


def load(**overrides) -> Config:
    """
    Carrega e valida a configuração; encerra o programa se algo faltar.

    Os overrides vêm dos argumentos de linha de comando e têm precedência sobre
    as variáveis de ambiente. Valores None são ignorados, para que uma flag não
    informada não apague o que está no monitor_config.env.
    """
    cfg = from_env()
    for chave, valor in overrides.items():
        if valor is not None:
            setattr(cfg, chave, valor)

    errors = cfg.validate()
    if errors:
        log.error("=" * 56)
        log.error("CONFIGURAÇÃO INCOMPLETA")
        for e in errors:
            log.error(f"  ✗ {e}")
        log.error("-" * 56)
        log.error("Local:   preencha o arquivo monitor_config.env")
        log.error("Actions: preencha os Secrets do repositório")
        log.error("Consulte o README.md para o passo a passo.")
        log.error("=" * 56)
        sys.exit(1)

    for aviso in cfg.warnings():
        log.warning(aviso)
    return cfg
