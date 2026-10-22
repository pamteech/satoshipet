"""licencas.py - o porteiro da balada Pro, agora com vários crachás.

Provedores (escolha em config: "licenca_provedor"):
  - "hmac"          offline: chave = HMAC(e-mail) gerada pelo tools/keygen.py (padrão, funciona sem internet)
  - "gumroad"       POST https://api.gumroad.com/v2/licenses/verify   (precisa "licenca_produto" = product_id)
  - "lemonsqueezy"  POST https://api.lemonsqueezy.com/v1/licenses/activate e /validate (instance_id em cache)
  - "servidor"      seu servidor de chaves (server/licencas.py). É o caminho do Hotmart: o webhook de compra
                    aprovada gera a chave e manda por e-mail; o app valida em GET {url}/api/licenca/validar.

Cache: depois de validar online, guardamos {provedor, hash da chave, validado_em} na config. Sem internet,
o Pro continua valendo por GRACA_DIAS dias (período de graça) a partir da última validação boa.
Revalida online no máximo a cada REVALIDAR_H horas. Erros sempre em pt-BR e sem jargão.
"""
import hashlib
import time

import requests

from . import license

GRACA_DIAS = 14
REVALIDAR_H = 24
PROVEDORES = ("hmac", "gumroad", "lemonsqueezy", "servidor")
GUMROAD_URL = "https://api.gumroad.com/v2/licenses/verify"
LEMON_URL = "https://api.lemonsqueezy.com/v1/licenses"


class Resultado:
    def __init__(self, ok, msg, fonte="online", extra=None):
        self.ok, self.msg, self.fonte, self.extra = ok, msg, fonte, extra or {}

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"Resultado({self.ok}, {self.msg!r}, {self.fonte})"


class SemRede(Exception):
    """Não deu pra falar com o provedor (offline, timeout, 5xx). Ativa o período de graça."""


def _hash(chave):
    return hashlib.sha256((chave or "").strip().encode()).hexdigest()[:24]


def _post(http, url, dados, timeout=10):
    try:
        r = http.post(url, data=dados, timeout=timeout, headers={"Accept": "application/json"})
    except Exception as e:  # requests.ConnectionError, Timeout...
        raise SemRede(str(e)) from e
    if r.status_code >= 500:
        raise SemRede(f"HTTP {r.status_code}")
    try:
        return r.status_code, r.json()
    except ValueError:
        raise SemRede("resposta não é JSON") from None


# ---------------- provedores ----------------
def _gumroad(cfg, email, chave, http):
    produto = cfg.get("licenca_produto")
    if not produto:
        return Resultado(False, "Configuração incompleta: falta o product_id do Gumroad (licenca_produto).")
    _cod, d = _post(http, GUMROAD_URL, {"product_id": produto, "license_key": chave.strip(),
                                       "increment_uses_count": "false"})
    if not d.get("success"):
        return Resultado(False, "Chave não encontrada no Gumroad. Confere se copiou inteira (com os traços).")
    p = d.get("purchase") or {}
    if p.get("refunded") or p.get("chargebacked"):
        return Resultado(False, "Essa compra foi reembolsada/contestada, então a chave foi desativada.")
    if p.get("subscription_ended_at") or p.get("subscription_cancelled_at") or p.get("subscription_failed_at"):
        return Resultado(False, "A assinatura dessa chave terminou. Renove no Gumroad pra voltar ao Pro.")
    if email and p.get("email") and p["email"].strip().lower() != email.strip().lower():
        return Resultado(False, "Essa chave é de outro e-mail. Use o e-mail da compra no Gumroad.")
    return Resultado(True, "Pro ativado via Gumroad!")


def _lemon(cfg, email, chave, http):
    cache = cfg.get("licenca_cache") or {}
    inst = cache.get("instance_id") if cache.get("chave") == _hash(chave) else None
    if inst:
        _cod, d = _post(http, f"{LEMON_URL}/validate", {"license_key": chave.strip(), "instance_id": inst})
        ok = d.get("valid")
    else:
        _cod, d = _post(http, f"{LEMON_URL}/activate", {"license_key": chave.strip(),
                                                       "instance_name": cfg.get("nome_pet") or "tamagoshi"})
        ok = d.get("activated")
        inst = (d.get("instance") or {}).get("id")
    lk = d.get("license_key") or {}
    meta = d.get("meta") or {}
    if not ok:
        erro = (d.get("error") or "").lower()
        if "limit" in erro:
            return Resultado(False, "Essa chave já atingiu o limite de ativações. Desative em outro computador "
                                    "(ou fale com o suporte).")
        if lk.get("status") in ("expired", "disabled"):
            return Resultado(False, "Essa chave está expirada ou desativada no Lemon Squeezy.")
        return Resultado(False, "Chave não reconhecida pelo Lemon Squeezy. Confere se copiou certinho.")
    if lk.get("status") in ("expired", "disabled"):
        return Resultado(False, "Essa chave está expirada ou desativada no Lemon Squeezy.")
    produto = cfg.get("licenca_produto")
    if produto and str(meta.get("product_id")) != str(produto):
        return Resultado(False, "Essa chave é de outro produto, não do Tamagoshi Cripto Pro.")
    if email and meta.get("customer_email") and meta["customer_email"].lower() != email.strip().lower():
        return Resultado(False, "Essa chave é de outro e-mail. Use o e-mail da compra.")
    return Resultado(True, "Pro ativado via Lemon Squeezy!", extra={"instance_id": inst})


def _servidor(cfg, email, chave, http):
    url = (cfg.get("licenca_url") or "").rstrip("/")
    if not url:
        return Resultado(False, "Configuração incompleta: falta a URL do servidor de licenças (licenca_url).")
    try:
        r = http.get(f"{url}/api/licenca/validar", params={"email": email or "", "chave": chave.strip()}, timeout=10)
    except Exception as e:
        raise SemRede(str(e)) from e
    if r.status_code >= 500:
        raise SemRede(f"HTTP {r.status_code}")
    d = r.json() if r.content else {}
    if d.get("valida"):
        return Resultado(True, "Pro ativado! Obrigado pela compra.")
    motivo = {"reembolso": "Essa compra foi reembolsada/cancelada, então a chave foi desativada.",
              "email": "Essa chave é de outro e-mail. Use o e-mail da compra."}.get(d.get("motivo"))
    return Resultado(False, motivo or "Chave não encontrada. Confere o e-mail e a chave do e-mail de compra.")


def _hmac(cfg, email, chave, http):
    if license.validar(email, chave):
        return Resultado(True, "Pro ativado!", fonte="offline")
    return Resultado(False, "Chave inválida. Confere o e-mail e a chave, hein?", fonte="offline")


IMPL = {"hmac": _hmac, "gumroad": _gumroad, "lemonsqueezy": _lemon, "servidor": _servidor}


# ---------------- API pública ----------------
def verificar(cfg, email, chave, http=requests, agora=None, forcar=False):
    """Valida a chave com o provedor configurado. Atualiza cfg["licenca_cache"]. Nunca levanta exceção."""
    agora = time.time() if agora is None else agora
    prov = cfg.get("licenca_provedor") or "hmac"
    if prov not in IMPL:
        return Resultado(False, f"Provedor de licença desconhecido: {prov!r}. Use um de: {', '.join(PROVEDORES)}.")
    if not chave or not str(chave).strip():
        return Resultado(False, "Cola a chave de licença (ela veio no e-mail da compra).")
    cache = cfg.get("licenca_cache") or {}
    mesmo = cache.get("provedor") == prov and cache.get("chave") == _hash(chave)
    if prov != "hmac" and mesmo and not forcar and agora - cache.get("validado_em", 0) < REVALIDAR_H * 3600:
        return Resultado(True, "Pro (validado recentemente).", fonte="cache")
    try:
        res = IMPL[prov](cfg, email, chave, http)
    except SemRede:
        if mesmo and agora - cache.get("validado_em", 0) < GRACA_DIAS * 86400:
            dias = GRACA_DIAS - int((agora - cache["validado_em"]) // 86400)
            return Resultado(True, f"Sem internet: Pro mantido no período de graça ({dias} dia(s) restantes).",
                             fonte="graca")
        return Resultado(False, "Não consegui falar com o servidor de licenças. Confere a internet e tenta de novo.",
                         fonte="offline")
    if res.ok and prov != "hmac":
        cfg["licenca_cache"] = {"provedor": prov, "chave": _hash(chave), "validado_em": agora, **res.extra}
    elif not res.ok and mesmo:
        cfg["licenca_cache"] = {}  # o provedor disse NÃO: derruba o cache na hora
    return res
