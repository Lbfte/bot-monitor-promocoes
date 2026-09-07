"""
Monitor de promoções — uma rodada.

Lê as mensagens novas do canal fonte, aplica os filtros e reposta no canal de
destino. Feito para rodar de forma descartável (GitHub Actions a cada 5 min):
começa, publica o que apareceu desde a última vez, grava o estado e encerra.

Uso:
    python run_monitor.py                      # roda de verdade
    python run_monitor.py --check              # só testa token e acesso ao canal
    python run_monitor.py --dry-run --backfill 5   # simula, sem publicar nada
"""

import argparse
import logging
import sys
import time

from monitor import config, filters, inbox, source
from monitor.publisher import Publisher
from monitor.state import State
from monitor.subscriptions import Subscriptions

# No Windows a saída padrão usa cp1252 quando é redirecionada para arquivo ou
# pipe, e os emojis das promoções derrubam o programa com UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("monitor")


def build_html(post, cfg) -> str:
    """Monta o texto final da mensagem, com rodapé opcional."""
    parts = [post.html] if post.html else []
    if cfg.include_source_link:
        parts.append(f'<a href="{post.url}">Ver no canal original</a>')
    if cfg.footer_text:
        parts.append(cfg.footer_text)
    return "\n\n".join(parts)


def parse_args() -> argparse.Namespace:
    """
    Flags equivalentes às variáveis de ambiente, para funcionar igual em
    qualquer shell — o PowerShell não aceita a sintaxe 'VAR=valor comando'.

    O padrão None significa 'não informado': nesse caso vale o que está no
    monitor_config.env, em vez da flag apagar a configuração.
    """
    parser = argparse.ArgumentParser(
        description="Reposta as promoções de um canal público do Telegram no seu canal.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="confere o token, o acesso ao canal de destino e a leitura do canal fonte",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=None,
        help="mostra o que seria publicado, sem publicar",
    )
    parser.add_argument(
        "--backfill", type=int, metavar="N",
        help="na primeira execução, publica as últimas N mensagens",
    )
    parser.add_argument(
        "--limit", type=int, metavar="N", dest="max_posts_per_run",
        help="máximo de publicações nesta rodada",
    )
    return parser.parse_args()


def check(cfg) -> int:
    """Diagnóstico: valida as credenciais sem publicar nada."""
    log.info("Verificando configuração...")

    publisher = Publisher(cfg.bot_token, cfg.dest_chat_id)
    destino_ok = publisher.check_access()

    fonte_ok = False
    try:
        posts = source.fetch(cfg.source_channel)
        fonte_ok = bool(posts)
    except Exception as e:
        log.error(f"Canal fonte: {e}")

    log.info("-" * 56)
    log.info(f"  Canal fonte:      {'OK' if fonte_ok else 'FALHOU'}")
    log.info(f"  Bot e destino:    {'OK' if destino_ok else 'FALHOU'}")
    if fonte_ok and destino_ok:
        log.info("Tudo certo. Pode rodar: python run_monitor.py")
        return 0
    log.error("Corrija os itens acima antes de rodar o monitor.")
    return 1


def build_alert(post, palavra: str, teto, preco, message_id: int, cfg) -> str:
    """Monta o aviso privado de quem monitora essa palavra."""
    partes = [f"🔔 Promoção de <b>{palavra}</b>", post.html]

    if teto and preco is None:
        partes.append("<i>(o post não trazia preço legível — confira antes de comprar)</i>")

    # O link só existe quando o destino é um canal público com @username.
    if message_id and cfg.dest_chat_id.startswith("@"):
        canal = cfg.dest_chat_id.lstrip("@")
        partes.append(f'<a href="https://t.me/{canal}/{message_id}">Ver no canal</a>')

    partes.append(f"<i>Para cancelar: /parar {palavra}</i>")
    return "\n\n".join(p for p in partes if p)


def send_alerts(publisher, subs, post, message_id: int, cfg) -> int:
    """Avisa no privado quem monitora alguma palavra que casa com o post."""
    if subs is None:
        return 0

    enviados = 0
    for chat_id, palavra, teto, preco in subs.match_post(post):
        if cfg.dry_run:
            log.info(f"  [DRY-RUN] alertaria {chat_id} sobre '{palavra}'")
            enviados += 1
            continue

        if publisher.send_to(chat_id, build_alert(post, palavra, teto, preco, message_id, cfg)):
            enviados += 1
        elif publisher.blocked_by_user:
            # Quem bloqueou o bot nunca mais vai receber nada: manter a
            # inscrição só gera erro em toda rodada.
            log.info(f"  {chat_id} bloqueou o bot — removendo as inscrições dele")
            subs.remove_chat(chat_id)
        time.sleep(0.2)

    if enviados:
        log.info(f"  🔔 {enviados} alerta(s) enviado(s)")
    return enviados


def main() -> int:
    args = parse_args()
    cfg = config.load(
        dry_run=args.dry_run,
        backfill=args.backfill,
        max_posts_per_run=args.max_posts_per_run,
    )

    if args.check:
        return check(cfg)

    log.info("=" * 56)
    log.info(f"  Fonte:   @{cfg.source_channel}")
    log.info(f"  Destino: {cfg.dest_chat_id or '(dry-run)'}")
    if cfg.dry_run:
        log.info("  MODO SIMULAÇÃO — nada será publicado")
    log.info("=" * 56)

    state = State(cfg.state_file, readonly=cfg.dry_run)
    publisher = Publisher(cfg.bot_token, cfg.dest_chat_id, dry_run=cfg.dry_run)

    subs = None
    if cfg.alerts_enabled:
        subs = Subscriptions(cfg.subscribers_file, cfg.subscribers_key)
        # Responder os comandos antes de publicar faz uma inscrição nova já
        # valer para as promoções desta mesma rodada.
        if not cfg.dry_run:
            inbox.process(publisher, subs, state)

    try:
        posts = source.fetch(cfg.source_channel)
    except Exception as e:
        log.error(f"Falha ao ler o canal fonte: {e}")
        return 1

    novos = [p for p in posts if p.id > state.last_post_id]

    # Primeira execução: por padrão só marca o ponto de partida, senão o canal
    # de destino levaria uma enxurrada de 20 promoções velhas de uma vez.
    if state.last_post_id == 0:
        if cfg.backfill <= 0:
            state.advance(max(p.id for p in posts))
            log.info(f"Primeira execução: marco zero no id {state.last_post_id}.")
            log.info("A partir da próxima rodada só entram mensagens novas.")
            log.info("(Para publicar as últimas N agora, use BACKFILL=N)")
            return 0
        novos = novos[-cfg.backfill:]
        log.info(f"Primeira execução: publicando as últimas {len(novos)} mensagens.")

    if not novos:
        log.info("Nenhuma mensagem nova.")
        return 0

    log.info(f"{len(novos)} mensagem(ns) nova(s) desde o id {state.last_post_id}")

    if not cfg.dry_run and not publisher.check_access():
        return 1

    lote = novos[: cfg.max_posts_per_run]
    if len(novos) > len(lote):
        log.info(f"Limitando a {len(lote)} nesta rodada; o resto vai na próxima.")

    publicados = ignorados = falhas = alertas = 0

    for post in lote:
        titulo = post.text.replace("\n", " ")[:70] or "(só imagem)"

        aprovado, motivo = filters.should_publish(post, cfg)
        if not aprovado:
            log.info(f"#{post.id} ignorado ({motivo}): {titulo}")
            state.advance(post.id)
            ignorados += 1
            continue

        impressao = filters.fingerprint(post)
        if state.is_duplicate(impressao):
            log.info(f"#{post.id} ignorado (repetido): {titulo}")
            state.advance(post.id)
            ignorados += 1
            continue

        log.info(f"#{post.id} publicando: {titulo}")
        message_id = publisher.publish(build_html(post, cfg), post.photos)
        if message_id is not None:
            # Grava a cada publicação: se a rodada morrer no meio, a próxima
            # continua de onde parou em vez de repostar tudo.
            state.remember(post.id, impressao)
            publicados += 1
            alertas += send_alerts(publisher, subs, post, message_id, cfg)
        else:
            log.warning(f"#{post.id} falhou — será tentado de novo na próxima rodada")
            falhas += 1
            break

        if post is not lote[-1]:
            time.sleep(cfg.send_delay)

    log.info("-" * 56)
    log.info(
        f"Publicados: {publicados} │ Ignorados: {ignorados} │ "
        f"Falhas: {falhas} │ Alertas: {alertas}"
    )
    return 1 if falhas and not publicados else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuário.")
        sys.exit(130)
