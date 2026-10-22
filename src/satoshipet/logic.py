# logic.py - o cérebro do bicho (sem GUI, dá pra testar à vontade)
from typing import Any, Dict, List, Optional

import requests

from .config import API_URL, MOEDAS


def estado_do_bicho(variacao: float, limite_alta: float=2.0, limite_queda: float=-2.0) -> str:
    """Psicólogo de trader: decide o humor com base na variação %."""
    if variacao > limite_alta:
        return "moon"
    if variacao < limite_queda:
        return "rekt"
    return "garimpando"


def variacao_pct(preco: float, referencia: float) -> float:
    if not referencia:
        return 0.0
    return (preco - referencia) / referencia * 100


class RateLimit(Exception):
    """O CoinGecko mandou a gente sentar e respirar."""


def buscar_precos(simbolos: Any, timeout: float = 10) -> Dict[str, Any]:
    """Busca TODAS as moedas numa chamada só. Retorna {"BTC": 65000.0, ...}."""
    ids = [MOEDAS[s] for s in simbolos if s in MOEDAS]
    r = requests.get(API_URL, params={"ids": ",".join(ids), "vs_currencies": "usd"},
                     timeout=timeout, headers={"User-Agent": "SatoshiPet/1.0"})
    if r.status_code == 429:
        raise RateLimit("429: calma, apressadinho")
    r.raise_for_status()
    dados = r.json()
    inverso = {v: k for k, v in MOEDAS.items()}
    return {inverso[i]: float(v["usd"]) for i, v in dados.items() if "usd" in v}


def formatar_preco(p: float) -> str:
    """PEPE vale 0,00001 dólar, então nada de 2 casas pra todo mundo."""
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.10f}".rstrip("0")


def checar_alerta(preco: float, alvo: Dict[str, Any]) -> Optional[str]:
    """alvo = {"acima": x, "abaixo": y}. Retorna texto do alerta ou None."""
    if not alvo:
        return None
    if alvo.get("acima") and preco >= alvo["acima"]:
        return f"passou de {formatar_preco(alvo['acima'])}!"
    if alvo.get("abaixo") and preco <= alvo["abaixo"]:
        return f"caiu abaixo de {formatar_preco(alvo['abaixo'])}!"
    return None


class Historico:
    """Guarda as últimas amostras de preço (30s x 480 = 4 horas) pra sparkline."""

    def __init__(self, maximo: int=480):
        from collections import deque
        self.maximo = maximo
        self.dados: Dict[str, Any] = {}
        self._deque = deque

    def adicionar(self, moeda: str, preco: float, t: Optional[float]=None) -> None:
        import time as _t
        self.dados.setdefault(moeda, self._deque(maxlen=self.maximo)).append((t or _t.time(), preco))

    def serie(self, moeda: str, pontos: int=40) -> List[float]:
        """Reamostra em `pontos` colunas (média por balde) pra caber no painel."""
        xs = [p for _, p in self.dados.get(moeda, ())]
        if len(xs) <= pontos:
            return xs
        passo = len(xs) / pontos
        return [sum(xs[int(i * passo):int((i + 1) * passo)]) / max(1, len(xs[int(i * passo):int((i + 1) * passo)]))
                for i in range(pontos)]
