"""calendario.py - v1.7: datas sagradas do mundo cripto (e do Brasil) com chapéu, frase e toast."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

INTERVALO_HALVING = 210_000


def _pascoa(ano: int) -> dt.date:  # algoritmo de Meeus/Butcher (gregoriano)
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mes = (h + l_ - 7 * m + 114) // 31
    dia = (h + l_ - 7 * m + 114) % 31 + 1
    return dt.date(ano, mes, dia)


def carnaval(ano: int) -> dt.date:
    """Terça de carnaval = Páscoa - 47 dias."""
    return _pascoa(ano) - dt.timedelta(days=47)


EVENTOS = {
    "genesis": {"nome": "GENESIS BLOCK", "chapeu": "festa",
                "frases": ["03/01/2009: Chancellor on brink of second bailout", "feliz aniversário, timechain!",
                           "bloco 0. o começo de tudo."]},
    "pizza": {"nome": "BITCOIN PIZZA DAY", "chapeu": None, "item": "pizza",
              "frases": ["10.000 BTC por 2 pizzas. vale a pena?", "laszlo, a gente te ama", "hoje é dia de pizza (em sats)"]},
    "whitepaper": {"nome": "WHITEPAPER DAY", "chapeu": "festa",
                   "frases": ["31/10/2008: Bitcoin: A Peer-to-Peer Electronic Cash System", "9 páginas que mudaram tudo",
                              "leu o whitepaper hoje?"]},
    "natal": {"nome": "FELIZ NATAL", "chapeu": "natal", "frases": ["ho ho HODL", "pedi um full node pro papai noel"]},
    "carnaval": {"nome": "CARNAVAL", "chapeu": "carnaval",
                 "frases": ["ô abre alas que eu quero passar (a mempool)", "bloquinho de carnaval = bloco minerado"]},
    "halving": {"nome": "HALVING!", "chapeu": "festa", "frases": ["subsídio cortado pela metade. escassez!",
                                                                    "tick tock, next block... HALVING!"]},
}


def evento_do_dia(hoje: Optional[dt.date] = None) -> Optional[str]:
    d = hoje or dt.date.today()
    if (d.month, d.day) == (1, 3):
        return "genesis"
    if (d.month, d.day) == (5, 22):
        return "pizza"
    if (d.month, d.day) == (10, 31):
        return "whitepaper"
    if d.month == 12 and 24 <= d.day <= 25:
        return "natal"
    c = carnaval(d.year)
    if c - dt.timedelta(days=4) <= d <= c:  # sábado a terça
        return "carnaval"
    return None


def halving(altura: Optional[int]) -> Optional[Dict[str, Any]]:
    """{"proximo": altura do próximo halving, "faltam": blocos, "dias": estimativa, "agora": bool}."""
    if not altura or altura < 0:
        return None
    if altura % INTERVALO_HALVING == 0:
        return {"proximo": altura, "faltam": 0, "dias": 0.0, "agora": True, "numero": altura // INTERVALO_HALVING}
    prox = (altura // INTERVALO_HALVING + 1) * INTERVALO_HALVING
    faltam = prox - altura
    return {"proximo": prox, "faltam": faltam, "dias": faltam * 10 / 1440, "agora": False,
            "numero": prox // INTERVALO_HALVING}


def contagem(h: Optional[Dict[str, Any]], perto: int = 2016) -> Optional[str]:
    """Texto curto de contagem quando falta menos de ~2 semanas (2016 blocos)."""
    if not h or h["agora"] or h["faltam"] > perto:
        return None
    if h["faltam"] <= 144:
        return f"HALVING EM {h['faltam']} BLOCOS!"
    return f"HALVING em ~{h['dias']:.1f} dias ({h['faltam']} blocos)"


def ativo(hoje: Optional[dt.date] = None, altura: Optional[int] = None) -> Optional[Dict[str, Any]]:
    h = halving(altura)
    if h and h["agora"]:
        return dict(EVENTOS["halving"], id="halving")
    eid = evento_do_dia(hoje)
    return dict(EVENTOS[eid], id=eid) if eid else None
