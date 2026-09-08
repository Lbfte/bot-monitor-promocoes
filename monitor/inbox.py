"""
Comandos recebidos no privado do bot.

Não existe processo escutando 24/7: a cada rodada o monitor chama getUpdates,
processa o que chegou desde a última vez e segue. É por isso que a resposta ao
usuário pode demorar alguns minutos — o mesmo atraso do cron.

Só mensagens privadas são consideradas. Um bot só recebe mensagens de quem
iniciou conversa com ele, então não há como alguém ser inscrito sem querer.
"""

import logging
import re

log = logging.getLogger("monitor.inbox")

AJUDA = (
    "👋 Eu aviso quando aparecer promoção do que te interessa.\n\n"
    "<b>Comandos</b>\n"
    "/monitorar <i>palavra</i> — ex: <code>/monitorar notebook</code>\n"
    "/monitorar <i>palavra valor</i> — só avisa até esse preço:\n"
    "     <code>/monitorar notebook 3000</code>\n"
    "/parar <i>palavra</i> — cancela o aviso\n"
    "/lista — mostra o que você monitora\n"
    "/status — mostra a última promoção lida e quantas palavras você monitora"
)

# Aceita "3000", "3.000", "3000,50" ou "R$ 3.000,00".
TETO_RE = re.compile(r"^R?\$?\s*(\d[\d.]*(?:,\d{1,2})?)$", re.IGNORECASE)


def _parse_teto(texto: str) -> float | None:
    match = TETO_RE.match(texto.strip())
    if not match:
        return None
    try:
        return float(match.group(1).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def process(publisher, subs, state) -> int:
    """Lê e responde os comandos pendentes. Devolve quantos foram processados."""
    updates = publisher.get_updates(state.update_offset)
    if not updates:
        return 0

    processados = 0
    for update in updates:
        state.update_offset = update["update_id"] + 1
        mensagem = update.get("message")
        if not mensagem or mensagem.get("chat", {}).get("type") != "private":
            continue
        texto = (mensagem.get("text") or "").strip()
        if not texto.startswith("/"):
            continue

        chat_id = mensagem["chat"]["id"]
        resposta = _responder(texto, chat_id, subs, state)
        publisher.send_to(chat_id, resposta)
        processados += 1

    state.save()
    if processados:
        log.info(f"{processados} comando(s) respondido(s)")
    return processados


def _responder(texto: str, chat_id: int, subs, state) -> str:
    partes = texto.split()
    # "/monitorar@MeuBot" também é válido quando o bot está num grupo.
    comando = partes[0].split("@")[0].casefold()
    args = partes[1:]

    if comando in ("/start", "/ajuda", "/help"):
        return AJUDA

    if comando in ("/status",):
        qtd = len(subs.list_for(chat_id))
        return f"Última promoção lida: {state.last_post_id}\nVocê monitora {qtd} palavra(s)."

    if comando in ("/monitorar", "/watch"):
        if not args:
            return "Faltou a palavra. Ex: <code>/monitorar notebook</code>"
        teto = _parse_teto(args[-1]) if len(args) > 1 else None
        palavra = " ".join(args[:-1] if teto is not None else args)
        ok, mensagem = subs.add(chat_id, palavra, teto)
        if ok and teto:
            return f"{mensagem} Só aviso se estiver até R$ {teto:.2f}."
        return mensagem

    if comando in ("/parar", "/unwatch"):
        if not args:
            return "Faltou a palavra. Ex: <code>/parar notebook</code>"
        palavra = " ".join(args)
        if subs.remove(chat_id, palavra):
            return f"Parei de monitorar <b>{palavra}</b>."
        return f"Você não monitorava <b>{palavra}</b>. Veja sua lista com /lista"

    if comando in ("/lista", "/list"):
        itens = subs.list_for(chat_id)
        if not itens:
            return "Você ainda não monitora nada. Ex: <code>/monitorar notebook</code>"
        linhas = []
        for item in itens:
            teto = f" — até R$ {item['teto']:.2f}" if item.get("teto") else ""
            linhas.append(f"• <b>{item['palavra']}</b>{teto}")
        return "<b>Você monitora:</b>\n" + "\n".join(linhas)

    return f"Não conheço esse comando.\n\n{AJUDA}"
