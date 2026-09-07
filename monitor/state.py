"""
Estado persistente entre execuções.

Como cada rodada no GitHub Actions começa numa máquina nova, o estado precisa
sobreviver fora do processo. Ele é gravado em state.json e o próprio workflow
commita o arquivo de volta no repositório — é o jeito de manter memória sem
pagar por banco de dados.
"""

import json
import logging
import os
from datetime import datetime, timezone

log = logging.getLogger("monitor.state")

# Quantas impressões digitais manter. 500 cobre semanas de canal movimentado
# sem deixar o arquivo grande.
MAX_SEEN = 500


class State:
    def __init__(self, path: str, readonly: bool = False):
        self.path = path
        # Em simulação o estado é lido mas nunca gravado: um teste não pode
        # fazer a rodada seguinte pular promoções que nunca foram publicadas.
        self.readonly = readonly
        self.last_post_id: int = 0
        self.seen: list[str] = []
        # Próximo update da Bot API a ler. Sem isso, os comandos já respondidos
        # voltariam a cada rodada.
        self.update_offset: int = 0
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            log.info("Nenhum estado anterior — primeira execução.")
            return
        try:
            with open(self.path, encoding="utf-8") as fp:
                data = json.load(fp)
            self.last_post_id = int(data.get("last_post_id", 0))
            self.seen = list(data.get("seen", []))
            self.update_offset = int(data.get("update_offset", 0))
            log.info(f"Estado carregado: último id {self.last_post_id}, {len(self.seen)} impressões")
        except (json.JSONDecodeError, ValueError, OSError) as e:
            log.warning(f"Estado corrompido ({e}) — recomeçando do zero.")

    def save(self):
        if self.readonly:
            return
        data = {
            "last_post_id": self.last_post_id,
            "update_offset": self.update_offset,
            "seen": self.seen[-MAX_SEEN:],
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def is_duplicate(self, fingerprint: str) -> bool:
        return fingerprint in self.seen

    def advance(self, post_id: int):
        """Marca um post como já avaliado sem registrar publicação."""
        self.last_post_id = max(self.last_post_id, post_id)
        self.save()

    def remember(self, post_id: int, fingerprint: str):
        """Marca um post como já publicado e grava em disco na hora."""
        self.last_post_id = max(self.last_post_id, post_id)
        if fingerprint not in self.seen:
            self.seen.append(fingerprint)
        del self.seen[:-MAX_SEEN]
        self.save()
