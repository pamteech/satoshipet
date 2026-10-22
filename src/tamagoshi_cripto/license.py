# license.py - o porteiro da balada Pro
#
# PLACEHOLDER OFFLINE: a chave é um HMAC-SHA256 do e-mail com um segredo.
# Funciona sem internet, mas quem descompilar o .exe acha o segredo. Serve pro MVP.
#
# COMO TROCAR PELO GUMROAD (recomendado quando começar a vender):
#   1. No Gumroad, ative "Generate a unique license key" no produto e pegue o product_id.
#   2. Troque o corpo de `validar()` por algo assim:
#
#       r = requests.post("https://api.gumroad.com/v2/licenses/verify",
#                         data={"product_id": "SEU_PRODUCT_ID",
#                               "license_key": chave,
#                               "increment_uses_count": "false"}, timeout=10)
#       d = r.json()
#       return d.get("success") and not d["purchase"].get("refunded") \
#              and not d["purchase"].get("chargebacked")
#
#   3. Guarde o resultado em cache na config pra não depender de internet toda vez.
#
# OPEN-CORE: o repositório é público, então o segredo NÃO fica no código.
# Ordem de busca: variável de ambiente TAMAGOSHI_LICENSE_SECRET -> módulo _segredo.py
# (gerado no build de release a partir de um GitHub Secret, e ignorado pelo git) ->
# segredo de desenvolvimento (chaves feitas com ele só valem em builds de dev).
import hashlib
import hmac
import os


def _carregar_segredo() -> bytes:
    env = os.environ.get("TAMAGOSHI_LICENSE_SECRET")
    if env:
        return env.encode()
    try:
        from ._segredo import SEGREDO as s  # gerado só no build oficial
        return s.encode() if isinstance(s, str) else s
    except ImportError:
        return b"dev-only-nao-use-em-producao"


SEGREDO = _carregar_segredo()


def _normaliza(email: str) -> str:
    return email.strip().lower()


def gerar_chave(email: str) -> str:
    """Gera a chave no formato XXXX-XXXX-XXXX-XXXX (usado pelo keygen.py)."""
    dig = hmac.new(SEGREDO, _normaliza(email).encode(), hashlib.sha256).hexdigest().upper()[:16]
    return "-".join(dig[i:i + 4] for i in range(0, 16, 4))


def validar(email: str, chave: str) -> bool:
    """True se a chave bate com o e-mail. Sem chave, sem lambo."""
    if not email or not chave:
        return False
    return hmac.compare_digest(gerar_chave(email), chave.strip().upper())
