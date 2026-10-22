"""lore.py - o lado nerd: Fear & Greed, altura de bloco, halving, código konami."""
import requests

FNG_URL = "https://api.alternative.me/fng/?limit=1"
BLOCO_URL = "https://mempool.space/api/blocks/tip/height"
HALVING = 210_000
KONAMI = ["Up", "Up", "Down", "Down", "Left", "Right", "Left", "Right", "b", "a"]

ROTULO_FNG = {"Extreme Fear": "MEDO EXTREMO", "Fear": "MEDO", "Neutral": "NEUTRO",
              "Greed": "GANANCIA", "Extreme Greed": "GANANCIA EXTREMA"}


def fear_greed(timeout=10):
    """Índice Fear & Greed (alternative.me, grátis, sem chave). Retorna (valor, rótulo pt-BR)."""
    d = requests.get(FNG_URL, timeout=timeout).json()["data"][0]
    return int(d["value"]), ROTULO_FNG.get(d["value_classification"], d["value_classification"].upper())


def altura_bloco(timeout=10):
    return int(requests.get(BLOCO_URL, timeout=timeout).text.strip())


def halving(altura):
    """(blocos que faltam, dias estimados a 10 min/bloco, número do próximo halving)."""
    prox = (altura // HALVING + 1) * HALVING
    faltam = prox - altura
    return faltam, faltam * 10 / 1440, prox // HALVING


def ajuste_vida_fng(valor):
    """Ganância extrema anima o bicho, medo extremo deprime (por minuto)."""
    if valor is None:
        return 0.0
    if valor >= 75:
        return 0.1
    if valor <= 25:
        return -0.1
    return 0.0


class Konami:
    """Detector de ↑↑↓↓←→←→BA. alimentar(tecla) -> True quando completa."""

    def __init__(self):
        self.pos = 0

    def alimentar(self, tecla):
        tecla = tecla if len(tecla) > 1 else tecla.lower()
        if tecla == KONAMI[self.pos]:
            self.pos += 1
            if self.pos == len(KONAMI):
                self.pos = 0
                return True
        else:
            self.pos = 1 if tecla == KONAMI[0] else 0
        return False
