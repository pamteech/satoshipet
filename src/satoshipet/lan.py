"""lan.py - v1.7: bichos amigos na rede local (OPT-IN, desligado por padrão).

Protocolo: broadcast UDP na porta 47474, um JSON pequeno a cada ~60 s:
  {"t": "tama", "v": 1, "id": "<8 hex aleatório>", "nome": "...", "moeda": "BTC", "skin": "padrao",
   "humor": "moon", "emote": "gm"}
SÓ isso. Nunca carteira, saldo, e-mail, licença, IP ou nome do computador. O id é sorteado a
cada abertura do app (não rastreia ninguém). Pacote estranho/grande/malformado = ignorado.
Mac/Windows podem perguntar "permitir conexões de rede?" na 1ª vez: é o firewall pedindo pra
receber os pacotes UDP. Negou? Tudo segue funcionando, só sem amigos.
"""
from __future__ import annotations

import json
import re
import secrets
import socket
import time
from typing import Any, Callable, Dict, Optional

PORTA = 47474
MAX_BYTES = 512
MOEDAS_OK = ("BTC", "ETH", "SOL", "DOGE", "PEPE")
HUMORES = ("moon", "rekt", "garimpando")
EMOTES = ("gm", "<3", "wagmi", "hodl", "gn", "ngmi?", "lfg")
RE_NOME = re.compile(r"^[\w .\-!?]{1,12}$", re.UNICODE)
RE_SKIN = re.compile(r"^[a-z0-9_]{1,20}$")


def novo_id() -> str:
    return secrets.token_hex(4)


def montar(pid: str, nome: str, moeda: str, skin: str, humor: str, emote: Optional[str] = None) -> bytes:
    sk = skin if RE_SKIN.match(skin or "") else "padrao"  # skins de loja/plugin viram "padrao" pros outros
    d = {"t": "tama", "v": 1, "id": pid, "nome": (nome or "bicho")[:12], "moeda": moeda if moeda in MOEDAS_OK else "BTC",
         "skin": sk, "humor": humor if humor in HUMORES else "garimpando"}
    if emote in EMOTES:
        d["emote"] = emote
    return json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode()


def ler(dados: bytes) -> Optional[Dict[str, Any]]:
    """Valida TUDO. Retorna dict limpo ou None."""
    if not dados or len(dados) > MAX_BYTES:
        return None
    try:
        d = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(d, dict) or d.get("t") != "tama" or d.get("v") != 1:
        return None
    pid, nome, moeda, skin, humor = (d.get(k) for k in ("id", "nome", "moeda", "skin", "humor"))
    if not (isinstance(pid, str) and re.fullmatch(r"[0-9a-f]{8}", pid)):
        return None
    if not (isinstance(nome, str) and RE_NOME.match(nome)) or moeda not in MOEDAS_OK:
        return None
    if not (isinstance(skin, str) and RE_SKIN.match(skin)) or humor not in HUMORES:
        return None
    out = {"id": pid, "nome": nome, "moeda": moeda, "skin": skin, "humor": humor}
    if d.get("emote") in EMOTES:
        out["emote"] = d["emote"]
    return out


class Vizinhos:
    """Quem está por perto. Limite de taxa por id e de tamanho; esquece quem sumiu há 5 min."""

    def __init__(self, meu_id: str, agora: Callable = time.time, maximo: int = 16):
        self.meu_id, self.agora, self.maximo = meu_id, agora, maximo
        self.d: Dict[str, Dict[str, Any]] = {}
        self.ultimo_pacote: Dict[str, float] = {}

    def receber(self, dados: bytes) -> Optional[Dict[str, Any]]:
        p = ler(dados)
        if not p or p["id"] == self.meu_id:
            return None
        t = self.agora()
        if t - self.ultimo_pacote.get(p["id"], -1e9) < 20:  # rate limit: 1 pacote/20 s por amigo
            return None
        if p["id"] not in self.d and len(self.d) >= self.maximo:
            return None
        self.ultimo_pacote[p["id"]] = t
        p["visto"] = t
        self.d[p["id"]] = p
        return p

    def limpar(self) -> None:
        t = self.agora()
        for k in [k for k, v in self.d.items() if t - v["visto"] > 300]:
            self.d.pop(k, None)
            self.ultimo_pacote.pop(k, None)

    def lista(self) -> list:
        self.limpar()
        return list(self.d.values())


def abrir_socket(porta: int = PORTA) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("", porta))
    s.settimeout(1.0)
    return s


def anunciar(s: socket.socket, pacote: bytes, porta: int = PORTA) -> None:
    s.sendto(pacote, ("255.255.255.255", porta))


class Visita:
    """Amigo entrando pela borda, parando do lado do nosso bicho, trocando emote e indo embora."""

    def __init__(self, amigo: Dict[str, Any], largura: int, lado: int = 1, emote_meu: str = "gm"):
        self.amigo, self.L, self.lado = amigo, largura, (1 if lado >= 0 else -1)
        self.t = 0
        self.emote_meu = emote_meu
        self.DURACAO = 40

    @property
    def viva(self) -> bool:
        return self.t < self.DURACAO

    def tick(self) -> None:
        self.t += 1

    def x(self, centro: int, dist: int) -> int:
        """Entra em 10 frames, fica 20, sai em 10."""
        fora = self.L // 2 + dist + 40
        alvo = dist
        if self.t < 10:
            off = fora - (fora - alvo) * self.t / 10
        elif self.t < 30:
            off = alvo
        else:
            off = alvo + (fora - alvo) * (self.t - 30) / 10
        return int(centro + self.lado * off)

    def emote(self) -> Optional[tuple]:
        """(quem, texto) no balãozinho."""
        if 12 <= self.t < 20:
            return ("amigo", self.amigo.get("emote") or "gm")
        if 20 <= self.t < 28:
            return ("eu", self.emote_meu)
        return None
