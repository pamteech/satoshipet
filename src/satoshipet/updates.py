"""updates.py - pergunta pro GitHub se saiu versão nova. Só avisa; NUNCA baixa nem instala nada sozinho."""
import re

import requests

from . import __version__

REPO = "pamteech/satoshipet"
API = "https://api.github.com/repos/{repo}/releases/latest"


def _tupla(v):
    nums = re.findall(r"\d+", str(v))[:3]
    return tuple(int(n) for n in nums) + (0,) * (3 - len(nums))


def mais_nova(remota, local=__version__):
    return _tupla(remota) > _tupla(local)


def checar(repo=REPO, local=__version__, http=requests, timeout=8):
    """{"versao", "url", "notas"} se houver versão nova; None se não houver, offline ou repo placeholder."""
    if "OWNER" in repo:
        return None  # ainda sem repo público: não incomoda o GitHub
    try:
        r = http.get(API.format(repo=repo), timeout=timeout, headers={"Accept": "application/vnd.github+json"})
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception:
        return None
    if d.get("draft") or d.get("prerelease"):
        return None
    tag = d.get("tag_name") or ""
    if not tag or not mais_nova(tag, local):
        return None
    return {"versao": tag.lstrip("v"), "url": d.get("html_url") or f"https://github.com/{repo}/releases/latest",
            "notas": (d.get("body") or "").strip().splitlines()[:3]}
