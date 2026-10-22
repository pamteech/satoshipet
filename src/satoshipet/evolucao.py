"""evolucao.py - XP, níveis e estágios: ovo -> bebê -> adulto -> Whale ou Diamond Hands."""
import math
from typing import Any, Optional, Tuple

XP = {"bloco": 25, "minuto": 1, "crash": 50, "carinho": 2, "jogo": 1}
ESTAGIOS = [("ovo", 0), ("bebe", 100), ("adulto", 500), ("final", 2000)]
NOMES = {"ovo": "OVO", "bebe": "BEBE", "adulto": "ADULTO", "whale": "WHALE", "diamond": "DIAMOND HANDS"}


def nivel(xp: float) -> int:
    return int(math.sqrt(max(0, xp) / 10)) + 1


def xp_do_nivel(n: int) -> int:
    return (n - 1) ** 2 * 10


def progresso_nivel(xp: int) -> float:
    """0..1 dentro do nível atual."""
    n = nivel(xp)
    a, b = xp_do_nivel(n), xp_do_nivel(n + 1)
    return (xp - a) / (b - a)


def estagio(xp: int, crashes: int=0) -> str:
    """Forma final: 3+ crashes sobrevividos = Diamond Hands; senão, Whale."""
    atual = "ovo"
    for nome, minimo in ESTAGIOS:
        if xp >= minimo:
            atual = nome
    if atual == "final":
        return "diamond" if crashes >= 3 else "whale"
    return atual


def proximo_estagio(xp: float) -> Tuple[Optional[str], Optional[int]]:
    for nome, minimo in ESTAGIOS:
        if xp < minimo:
            return nome, minimo
    return None, None


class Evolucao:
    def __init__(self, dados: Any=None):
        self.d = {"xp": 0, "minutos_frac": 0.0}
        self.d.update(dados or {})

    def ganhar(self, motivo: str, qtd: int=1) -> bool:
        """Soma XP. Retorna (subiu_nivel, novo_estagio_ou_None, crashes não usado)."""
        antes_n = nivel(self.d["xp"])
        self.d["xp"] += XP[motivo] * qtd
        return nivel(self.d["xp"]) > antes_n

    def tick_minutos(self, segundos: int) -> bool:
        self.d["minutos_frac"] += segundos / 60
        inteiros = int(self.d["minutos_frac"])
        self.d["minutos_frac"] -= inteiros
        return self.ganhar("minuto", inteiros) if inteiros else False

    @property
    def xp(self) -> float:
        return self.d["xp"]
