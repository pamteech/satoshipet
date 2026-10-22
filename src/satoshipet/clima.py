"""clima.py - v1.7: clima de verdade (Open-Meteo, sem chave) pra vestir o bicho.

Privacidade: por padrão DESLIGADO. Você escolhe a cidade (geocoding da Open-Meteo) ou
lat/lon; "auto" (geolocalização por IP, ipwho.is) só se você pedir. Guardamos só o nome da
cidade e lat/lon arredondados (2 casas ~ 1 km). Sem rede? usa o último clima em cache.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import requests

URL = "https://api.open-meteo.com/v1/forecast"
GEO = "https://geocoding-api.open-meteo.com/v1/search"
IPGEO = "https://ipwho.is/"
UA = {"User-Agent": "SatoshiPet/1.7"}
INTERVALO = 30 * 60
TIPOS = ("sol", "nublado", "neblina", "chuva", "neve", "tempestade")


def tipo_por_codigo(codigo: int) -> str:
    """WMO weather code -> um dos TIPOS."""
    c = int(codigo)
    if c in (0, 1):
        return "sol"
    if c in (2, 3):
        return "nublado"
    if c in (45, 48):
        return "neblina"
    if c in (71, 73, 75, 77, 85, 86):
        return "neve"
    if c in (95, 96, 99):
        return "tempestade"
    if 51 <= c <= 82:
        return "chuva"
    return "nublado"


def buscar(lat: float, lon: float, timeout: float = 8) -> Dict[str, Any]:
    r = requests.get(URL, params={"latitude": round(lat, 2), "longitude": round(lon, 2),
                                  "current": "weather_code,is_day,temperature_2m"}, timeout=timeout, headers=UA)
    r.raise_for_status()
    cur = r.json().get("current") or {}
    return {"tipo": tipo_por_codigo(cur.get("weather_code", 3)), "dia": bool(cur.get("is_day", 1)),
            "temp": float(cur["temperature_2m"]) if "temperature_2m" in cur else None, "t": time.time()}


def geocodificar(cidade: str, timeout: float = 8) -> Optional[Tuple[str, float, float]]:
    nome = (cidade or "").strip()[:60]
    if not nome:
        return None
    r = requests.get(GEO, params={"name": nome, "count": 1, "language": "pt"}, timeout=timeout, headers=UA)
    r.raise_for_status()
    res = (r.json().get("results") or [None])[0]
    if not res:
        return None
    return f"{res.get('name', nome)}", round(float(res["latitude"]), 2), round(float(res["longitude"]), 2)


def por_ip(timeout: float = 8) -> Optional[Tuple[str, float, float]]:
    """Só quando o usuário escolhe 'auto'. Retorna (cidade, lat, lon) arredondados."""
    r = requests.get(IPGEO, timeout=timeout, headers=UA)
    r.raise_for_status()
    d = r.json()
    if not d.get("success", True) or "latitude" not in d:
        return None
    return str(d.get("city") or "?")[:40], round(float(d["latitude"]), 2), round(float(d["longitude"]), 2)


def parse_latlon(txt: str) -> Optional[Tuple[float, float]]:
    try:
        a, b = (float(x) for x in txt.replace(";", ",").split(","))
    except (ValueError, TypeError):
        return None
    if -90 <= a <= 90 and -180 <= b <= 180:
        return round(a, 2), round(b, 2)
    return None


class Cache:
    def __init__(self, relogio=time.time):
        self.dado: Optional[Dict[str, Any]] = None
        self.relogio = relogio
        self.prox = 0.0
        self.erros = 0

    def hora(self) -> bool:
        return self.relogio() >= self.prox

    def ok(self, d: Dict[str, Any]) -> None:
        self.dado, self.erros = d, 0
        self.prox = self.relogio() + INTERVALO

    def erro(self) -> None:
        self.erros += 1
        self.prox = self.relogio() + min(INTERVALO, 60 * 2 ** self.erros)


def efetivo(dado: Optional[Dict[str, Any]], hora: int) -> Dict[str, Any]:
    """Sem clima (desligado/offline): só dia/noite pelo relógio."""
    if dado:
        return dado
    return {"tipo": None, "dia": 6 <= hora < 18, "temp": None}
