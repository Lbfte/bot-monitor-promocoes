"""
Gera a chave que criptografa o arquivo de inscrições.

O arquivo subscribers.json vai commitado num repositório público, e guarda os
chat IDs de quem pediu alertas junto com as palavras que cada um monitora.
Criptografar evita expor isso.

Uso:
    python tools/gerar_chave.py

Guarde o valor em dois lugares:
  - monitor_config.env, na variável SUBSCRIBERS_KEY (para rodar localmente)
  - Settings → Secrets → Actions, como SUBSCRIBERS_KEY (para a nuvem)

Trocar a chave depois torna as inscrições existentes ilegíveis, e as pessoas
precisam se inscrever de novo.
"""

try:
    from cryptography.fernet import Fernet
except ImportError:
    raise SystemExit("Faltou instalar as dependências: pip install -r requirements.txt")

print(Fernet.generate_key().decode())
