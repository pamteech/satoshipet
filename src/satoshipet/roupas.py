"""roupas.py - v1.8: roupinhas de época pintadas por cima do sprite (qualquer estágio, qualquer moeda).

A arte fica em juice.ARTES (mesma grade 48x48 e mesma paleta dos chapéus da v1.1). Aqui mora só
o calendário: qual roupinha vale em qual dia. `--date AAAA-MM-DD` / SATOSHIPET_DATE simulam o dia.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Optional

from . import calendario

# id -> nome mostrado em Ajustes/CLI
NOMES = {
    "halloween": "Halloween (chapéu de bruxa)",
    "whitepaper": "Halloween + Whitepaper Day (bruxa com o paper)",
    "natal": "Natal (gorro do Noel)",
    "ano_novo": "Ano Novo (cartola dourada)",
    "pizza": "Bitcoin Pizza Day (chapéu de pizza)",
    "genesis": "Genesis Block (coroa de bloco 0)",
    "carnaval": "Carnaval (tiara de plumas)",
    "halving": "Halving (chapéu de festa)",
}


def hoje() -> dt.date:
    """Dia 'de verdade' do app: SATOSHIPET_DATE (debug/preview) vence o relógio."""
    v = os.environ.get("SATOSHIPET_DATE", "").strip()
    if v:
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            pass
    return dt.date.today()


def roupa_do_dia(d: Optional[dt.date] = None, altura: Optional[int] = None) -> Optional[str]:
    """Prioridade: halving > genesis > ano novo > carnaval > pizza > whitepaper > halloween > natal."""
    d = d or hoje()
    h = calendario.halving(altura)
    if h and h["agora"]:
        return "halving"
    md = (d.month, d.day)
    if md == (1, 3):
        return "genesis"
    if md in ((12, 31), (1, 1), (1, 2)):
        return "ano_novo"
    c = calendario.carnaval(d.year)
    if c - dt.timedelta(days=3) <= d <= c + dt.timedelta(days=1):  # sábado até quarta de cinzas
        return "carnaval"
    if md == (5, 22):
        return "pizza"
    if md == (10, 31):
        return "whitepaper"  # 31/10/2008: whitepaper + halloween no mesmo dia
    if (d.month == 10 and d.day >= 27) or (d.month == 11 and d.day <= 2):
        return "halloween"
    if d.month == 12:
        return "natal"
    return None
