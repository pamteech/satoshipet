"""ranking.py (cliente) - leaderboard OPCIONAL. Desligado por padrão; liga com `rank on <apelido>`.

O que sai do seu computador: device_id aleatório (uuid4, nada a ver com hardware), apelido, xp, nível,
estágio, blocos comidos, nº de conquistas e a moeda. Só. Nada de carteira, preço, e-mail ou IP guardado.
"""
import re
import uuid

import requests

RE_NICK = re.compile(r"^[A-Za-z0-9_\-]{3,16}$")


def ligado(cfg):
    return bool(cfg.get("ranking") and cfg.get("ranking_url") and cfg.get("nick"))


def device_id(cfg):
    if not re.fullmatch(r"[0-9a-f]{32}", cfg.get("device_id") or ""):
        cfg["device_id"] = uuid.uuid4().hex
    return cfg["device_id"]


def payload(cfg, st):
    """Lista branca: é exatamente isso que vai pro servidor."""
    conq = str(st.get("conquistas", "0")).split("/")[0]
    return {"device_id": device_id(cfg), "nick": cfg.get("nick", ""), "xp": int(st.get("xp") or 0),
            "nivel": int(st.get("nivel") or 1), "estagio": st.get("estagio", "OVO"),
            "blocos": int((st.get("btc") or {}).get("comidos") or 0), "conquistas": int(conq or 0),
            "moeda": st.get("moeda", "BTC")}


def enviar(cfg, st, timeout=6):
    r = requests.post(cfg["ranking_url"].rstrip("/") + "/api/stats", json=payload(cfg, st), timeout=timeout)
    if r.status_code == 429:
        return None
    r.raise_for_status()
    return r.json().get("posicao")


def top(url, n=10, timeout=6):
    r = requests.get(url.rstrip("/") + f"/api/top?n={n}", timeout=timeout)
    r.raise_for_status()
    return r.json()["top"]


def comando(cfg, st, args, salvar=lambda c: None):
    """Implementação do `rank` (console da janela e do TUI). Retorna linhas."""
    if args[:1] == ["off"]:
        cfg["ranking"] = False
        salvar(cfg)
        return ["ranking desligado. você voltou a ser um anon de verdade."]
    if args[:1] == ["on"]:
        if len(args) < 2 or not RE_NICK.match(args[1]):
            return ["uso: rank on <apelido>  (3-16 letras/números/_/-; NUNCA seu nome real ou endereço)"]
        if not cfg.get("ranking_url"):
            return ["defina \"ranking_url\" na config (ex.: http://127.0.0.1:8740) antes de ligar."]
        cfg.update({"ranking": True, "nick": args[1]})
        device_id(cfg)
        salvar(cfg)
        linhas = [f"ranking ligado como {args[1]}. enviado: apelido, xp, nível, estágio, blocos, conquistas."]
    elif args[:1] == ["url"] and len(args) > 1:
        cfg["ranking_url"] = args[1]
        salvar(cfg)
        return [f"ranking_url = {args[1]}"]
    else:
        linhas = []
        if not ligado(cfg):
            linhas += ["ranking é opt-in (desligado). ligue com: rank on <apelido>",
                       "privacidade: só apelido + stats do bicho. sem carteira, sem e-mail."]
    url = cfg.get("ranking_url")
    if not url:
        return linhas
    try:
        if ligado(cfg):
            pos = enviar(cfg, st)
            if pos:
                linhas.append(f"você está em #{pos}")
        lista = top(url, 10)
    except Exception as e:
        return linhas + [f"servidor de ranking offline ({type(e).__name__}). o bicho continua feliz."]
    linhas.append("#   apelido          LV  estágio")
    for j in lista:
        linhas.append(f"{j['pos']:<3} {j['nick']:<16} {j['nivel']:<3} {j['estagio']}")
    return linhas or ["ninguém no ranking ainda. seja o satoshi."]
