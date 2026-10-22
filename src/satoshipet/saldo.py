"""saldo.py - SALDO das carteiras watch-only no painel (v1.6).

Regras da casa (inegociáveis):
- só endereço PÚBLICO. Nunca chave privada, nunca seed. O bicho só OLHA.
- o saldo vive SÓ na memória: nada em disco, nada na API local, status, card, ranking ou overlay.
- botão de pânico pra gravar vídeo: `saldo off` vira "••••".
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from .config import API_URL, MOEDAS

OCULTO = "••••"
FIATS = ("auto", "brl", "usd")
MARCOS = {"BTC": (0.001, 0.01, 0.1, 1.0), "ETH": (0.1, 1.0, 10.0), "SOL": (1.0, 10.0, 100.0)}


def fiat_efetiva(escolha: Optional[str], idioma: str) -> str:
    if escolha in ("brl", "usd"):
        return escolha
    return "brl" if idioma == "pt" else "usd"


def buscar_fiat(simbolos: Any, timeout: float = 10) -> Dict[str, Dict[str, float]]:
    """{"BTC": {"brl": 450000.0, "usd": 81000.0}, ...} numa chamada só (CoinGecko, sem chave)."""
    ids = [MOEDAS[s] for s in simbolos if s in MOEDAS]
    if not ids:
        return {}
    r = requests.get(API_URL, params={"ids": ",".join(ids), "vs_currencies": "brl,usd"}, timeout=timeout,
                     headers={"User-Agent": "SatoshiPet/1.6"})
    r.raise_for_status()
    inv = {v: k for k, v in MOEDAS.items()}
    return {inv[i]: {k: float(x) for k, x in v.items() if k in ("brl", "usd")} for i, v in r.json().items() if i in inv}


def _qtd(v: float) -> str:
    if v == 0:
        return "0"
    if v >= 100:
        return f"{v:,.2f}"
    return f"{v:.4f}" if v >= 0.01 else f"{v:.6f}".rstrip("0")


def fmt_fiat(v: float, fiat: str) -> str:
    if fiat == "brl":  # R$ 7.450 / R$ 12,34 (padrão brasileiro: ponto no milhar)
        s = f"{v:,.0f}" if v >= 100 else f"{v:,.2f}"
        return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${v:,.0f}" if v >= 100 else f"${v:,.2f}"


def linhas(saldos: Dict[str, float], fiat_precos: Dict[str, Dict[str, float]], fiat: str,
           oculto: bool) -> list:
    """saldos = {"BTC": 0.0123, "ETH": 1.5}. Retorna [(texto, cor)] pro painel."""
    out = []
    for sim, v in saldos.items():
        if v is None:
            continue
        if oculto:
            out.append((f"SALDO {OCULTO} {sim}", "#ffcd75"))
            continue
        p = (fiat_precos.get(sim) or {}).get(fiat)
        extra = f" ≈ {fmt_fiat(v * p, fiat)}" if p else ""
        out.append((f"SALDO {_qtd(v)} {sim}{extra}", "#ffcd75"))
    return out


def marco_novo(sim: str, antes: Optional[float], agora: float) -> Optional[float]:
    """Cruzou um marco pra cima (ex.: 0.01 BTC)? Retorna o marco. Na 1ª leitura não comemora."""
    if antes is None:
        return None
    cruzados = [m for m in MARCOS.get(sim, ()) if antes < m <= agora]
    return cruzados[-1] if cruzados else None


class Backoff:
    """Intervalo de atualização: 3 min normal; erro dobra até 30 min; acerto volta pro normal."""

    def __init__(self, base: float = 180, teto: float = 1800, relogio=time.time):
        self.base, self.teto, self.relogio = base, teto, relogio
        self.intervalo, self.proximo = base, 0.0

    def hora(self) -> bool:
        return self.relogio() >= self.proximo

    def ok(self) -> None:
        self.intervalo = self.base
        self.proximo = self.relogio() + self.base

    def erro(self) -> None:
        self.intervalo = min(self.teto, self.intervalo * 2)
        self.proximo = self.relogio() + self.intervalo
