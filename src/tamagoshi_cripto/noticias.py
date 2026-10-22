"""noticias.py - manchetes cripto via RSS público (sem chave, sem conta). O bicho lê pra você.

Só título + link. Clicar no balão abre a matéria no navegador. Nada de rastreamento.
"""
import html
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

FEEDS = {"CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
         "Cointelegraph": "https://cointelegraph.com/rss"}
UA = {"User-Agent": "TamagoshiCripto/1.4 (+github)"}


def limpar(t: Optional[str]) -> str:
    """Tira HTML e caracteres que a fonte pixel não tem (fica só Latin-1)."""
    t = html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2014", "-").replace("\u2013", "-").replace("\u2026", "...")
    t = "".join(ch for ch in unicodedata.normalize("NFC", t) if ord(ch) < 256)
    return re.sub(r"\s+", " ", t).strip()


def parse(xml_texto: bytes, fonte: str) -> Any:
    raiz = ET.fromstring(xml_texto)
    itens = []
    for it in raiz.iter("item"):
        tit, link = limpar(it.findtext("title")), (it.findtext("link") or "").strip()
        if tit and link.startswith("https://"):
            itens.append({"titulo": tit, "link": link, "fonte": fonte})
    return itens[:15]


def buscar(timeout: float = 10) -> List[Dict[str, Any]]:
    todas = []
    for fonte, url in FEEDS.items():
        try:
            r = requests.get(url, timeout=timeout, headers=UA)
            r.raise_for_status()
            todas += parse(r.content, fonte)
        except Exception as e:
            print("RSS deu ruim:", fonte, e)
    return todas
