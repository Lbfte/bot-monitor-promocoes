"""
Descobre o ID do canal de destino.

Como usar:
  1. Crie o bot com o @BotFather e copie o token.
  2. Crie o canal e adicione o bot como ADMINISTRADOR (com permissão de
     publicar mensagens).
  3. Poste qualquer coisa no canal ("teste", por exemplo).
  4. Rode:  python tools/get_chat_id.py 123456789:AAE-seu-token

O bot só enxerga mensagens de canais onde ele é administrador — se nada
aparecer, quase sempre é porque esse passo faltou.
"""

import sys

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def call(token: str, method: str, **params):
    resp = requests.get(API.format(token=token, method=method), params=params, timeout=20)
    data = resp.json()
    if not data.get("ok"):
        print(f"✗ {method}: {data.get('description')}")
        return None
    return data["result"]


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        import os
        from dotenv import load_dotenv
        load_dotenv("monitor_config.env")
        token = os.getenv("BOT_TOKEN", "").strip()

    if not token:
        print("Uso: python tools/get_chat_id.py <BOT_TOKEN>")
        print("(ou preencha BOT_TOKEN no monitor_config.env)")
        return 1

    me = call(token, "getMe")
    if not me:
        print("\nToken inválido. Confira se copiou o token inteiro do @BotFather.")
        return 1
    print(f"✓ Bot: @{me['username']} ({me['first_name']})\n")

    updates = call(token, "getUpdates", limit=100)
    if updates is None:
        return 1

    encontrados = {}
    for update in updates:
        for chave in ("channel_post", "message", "edited_channel_post", "my_chat_member"):
            evento = update.get(chave)
            if evento and "chat" in evento:
                chat = evento["chat"]
                encontrados[chat["id"]] = chat

    if not encontrados:
        print("Nenhum chat encontrado. Checklist:")
        print("  1. O bot foi adicionado ao canal COMO ADMINISTRADOR?")
        print("  2. Você postou alguma mensagem no canal DEPOIS de adicionar o bot?")
        print("  3. O canal não é um grupo com modo privacidade ligado?")
        print("\nDica: se o canal for público, você nem precisa do ID numérico —")
        print("basta usar DEST_CHAT_ID=@seucanal")
        return 1

    print("Chats encontrados:\n")
    for chat_id, chat in encontrados.items():
        titulo = chat.get("title") or chat.get("first_name") or "(sem título)"
        username = f" @{chat['username']}" if chat.get("username") else ""
        print(f"  {titulo}{username}")
        print(f"    tipo:  {chat['type']}")
        print(f"    ID:    {chat_id}")
        print(f"    →  DEST_CHAT_ID={chat.get('username') and '@' + chat['username'] or chat_id}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
