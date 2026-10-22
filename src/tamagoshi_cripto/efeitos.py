"""efeitos.py - v1.6: transições pixel, evolução estilo Pokémon, idle (piscar/bocejo/olhar) e dicas.

Tudo desenhado com retângulos grossos no Canvas (nada de alfa!): funciona igual na janela
transparente do Mac (sprites pintados via put), no Windows (cor-chave) e no Linux. Barato:
cada transição dura ~6 frames e usa blocos de 12 px (~600 retângulos no pior frame).
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable, List, Optional, Tuple

# Bayer 4x4: a ordem "pontilhada" clássica de dissolve 16-bit
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
TIPOS = ("dissolve", "wipe", "mosaico")
COR_TRANS = "#1a1c2c"


class Transicao:
    """Começa TUDO coberto e vai revelando a tela nova em `duracao` frames."""

    def __init__(self, tipo: str = "dissolve", duracao: int = 6, bloco: int = 12, cor: str = COR_TRANS):
        self.tipo = tipo if tipo in TIPOS else "dissolve"
        self.duracao, self.bloco, self.cor = max(2, duracao), bloco, cor
        self.t = 0

    @property
    def viva(self) -> bool:
        return self.t < self.duracao

    def tick(self) -> None:
        self.t += 1

    def cobertos(self, largura: int, altura: int) -> List[Tuple[int, int, int]]:
        """[(x, y, tamanho)] dos blocos ainda cobertos neste frame."""
        p = self.t / self.duracao  # 0 = tudo coberto, 1 = tudo revelado
        B = self.bloco
        cols, lins = -(-largura // B), -(-altura // B)
        out = []
        if self.tipo == "mosaico":  # blocos encolhem do centro de cada célula (efeito "pixelate out")
            tam = int(B * (1 - p))
            if tam <= 0:
                return []
            off = (B - tam) // 2
            return [(c * B + off, r * B + off, tam) for r in range(lins) for c in range(cols)]
        for r in range(lins):
            for c in range(cols):
                if self.tipo == "wipe":  # diagonal: canto sup-esq revela primeiro
                    lim = (c + r + 0.5) / max(1, cols + lins - 1)
                else:
                    lim = (BAYER[r % 4][c % 4] + 0.5) / 16
                if lim >= p:
                    out.append((c * B, r * B, B))
        return out

    def desenhar(self, cv: Any, largura: int, altura: int) -> int:
        n = 0
        for x, y, s in self.cobertos(largura, altura):
            cv.create_rectangle(x, y, x + s, y + s, fill=self.cor, width=0, tags=("fx",))
            n += 1
        return n


class Evolucao:
    """Silhueta piscando forma velha/nova cada vez mais rápido, flash branco, brilhos e 'EVOLUIU!'."""

    DURACAO = 26  # ~4,7 s a 180 ms

    def __init__(self, sil_velha: Any, sil_nova: Any, nome: str = "", semente: int = 0):
        self.sil_velha, self.sil_nova, self.nome = sil_velha, sil_nova, nome
        self.t = 0
        self.rng = random.Random(semente)

    @property
    def viva(self) -> bool:
        return self.t < self.DURACAO

    def tick(self) -> None:
        self.t += 1

    def fase(self) -> str:
        if self.t < 16:
            return "pisca"
        if self.t < 18:
            return "flash"
        return "revela"

    def qual(self) -> str:
        """Qual silhueta mostrar: alterna devagar no começo, rápido no fim (2,2,1,1,...)."""
        if self.fase() != "pisca":
            return "nova"
        periodo = 3 if self.t < 6 else 2 if self.t < 11 else 1
        return "velha" if (self.t // periodo) % 2 == 0 else "nova"

    def imagem(self, normal: Any) -> Any:
        """Imagem pro lugar do sprite neste frame (na fase final volta o sprite colorido)."""
        if self.fase() == "pisca":
            return self.sil_velha if self.qual() == "velha" else self.sil_nova
        if self.fase() == "flash":
            return self.sil_nova
        return normal

    def brilhos(self, cx: int, cy: int, raio: int) -> List[Tuple[int, int, int]]:
        """[(x, y, tam)] estrelinhas em órbita que crescem até o flash e depois explodem pra fora."""
        n = 8
        out = []
        for i in range(n):
            ang = i * (2 * math.pi / n) + self.t * 0.35
            r = raio * (1.0 + (max(0, self.t - 16) * 0.25))
            tam = 2 + (i + self.t) % 3
            out.append((int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r * 0.8), tam))
        return out

    def desenhar(self, cv: Any, largura: int, altura: int, cx: int, cy: int, raio: int, E: int,
                 txt: Callable[..., None]) -> None:
        if self.fase() == "flash":
            cv.create_rectangle(0, 0, largura, altura, fill="#f4f4f4", width=0, tags=("fx",))
        cor = "#ffcd75" if self.t % 2 else "#f4f4f4"
        for x, y, s in self.brilhos(cx, cy, raio):
            q = s * E // 2 or 1
            cv.create_rectangle(x - q, y, x + q + 1, y + 1 + E // 2, fill=cor, width=0, tags=("fx",))
            cv.create_rectangle(x, y - q, x + 1 + E // 2, y + q + 1, fill=cor, width=0, tags=("fx",))
        if self.fase() == "revela" or self.t % 4 < 2:
            txt(largura // 2, max(8, cy - raio - 18), "EVOLUIU!" if self.fase() != "pisca" else "?!",
                "#ffcd75", escala=2, sombra=COR_TRANS)
        if self.fase() == "revela" and self.nome:
            txt(largura // 2, max(8, cy - raio - 18) + 18, self.nome, "#73eff7", sombra=COR_TRANS)


# ---------------- idle ----------------
class Idle:
    """Vida quando ninguém mexe: piscar, olhar pro mouse, fidget, bocejo (parado muito tempo / de noite)."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.prox_piscada = self.rng.randint(15, 35)  # frames
        self.piscando = 0
        self.bocejo = 0
        self.fidget = 0
        self.t = 0

    def tick(self, parado_s: float, noite: bool) -> None:
        self.t += 1
        if self.piscando:
            self.piscando -= 1
        elif self.t >= self.prox_piscada:
            self.piscando = 1 if self.rng.random() > 0.2 else 3  # às vezes pisca duas vezes
            self.prox_piscada = self.t + self.rng.randint(18, 40)
        if self.bocejo:
            self.bocejo -= 1
        elif (parado_s > 300 or noite) and self.rng.random() < (0.01 if parado_s > 300 else 0.004):
            self.bocejo = 10
        if self.fidget:
            self.fidget -= 1
        elif self.rng.random() < 0.015:
            self.fidget = 4

    def olhos_fechados(self) -> bool:
        return self.piscando in (1, 3) or 2 <= self.bocejo <= 8

    def deslocamento(self, sx: int, sy: int, mx: Optional[int], my: Optional[int], E: int) -> Tuple[int, int]:
        """Cabeça segue o mouse (até 2 'pixels' grandes) + espreguiçada/fidget. Sem mouse: só fidget."""
        dx = dy = 0
        if mx is not None and my is not None:
            vx, vy = mx - sx, my - sy
            d = math.hypot(vx, vy)
            if 8 < d < 900:
                dx, dy = round(vx / d * 2) * E, round(vy / d * 1) * E
        if self.bocejo:  # espreguiça: sobe 1 px grande no meio do bocejo
            dy -= E if 3 <= self.bocejo <= 7 else 0
        if self.fidget:
            dx += (E if self.fidget % 2 else -E)
        return dx, dy


# ---------------- dicas (tooltips) ----------------
DICAS = {
    "vida": "Corações = vida. Alimente (blocos) e faça carinho pra encher.",
    "xp": "Barra de XP: blocos, carinho e tempo com você fazem o bicho evoluir.",
    "preco": "Preço ao vivo (CoinGecko) e variação desde que o app abriu.",
    "FEE": "Taxa da mempool (sat/vB). Fee alta = bicho com fome e suando.",
    "F&G": "Fear & Greed: 0 = pânico, 100 = euforia do mercado.",
    "HASH": "Hashrate da rede Bitcoin: o poder dos mineradores.",
    "BLOCO": "Altura do último bloco. NHAC = blocos que o bicho já comeu.",
    "GAS": "Gas do Ethereum em gwei: quanto custa mexer na rede.",
    "SALDO": "Saldo watch-only (só leitura). 'saldo off' esconde: ••••",
    "PAPEL": "Paper trading: dinheiro FICTÍCIO, só pra treinar.",
    "WALLET": "Saldo watch-only (só leitura).",
    "pro": "PRO: 5 moedas, alertas, gráfico e skins premium.",
    "botao": "Link de compra (afiliado). Use com juízo: DYOR!",
}


def zona(x: int, y: int, m: dict) -> Optional[str]:
    """Qual dica mostrar no ponto (x, y). m = medidas do layout (ver MixinDesenho._zonas)."""
    for chave, (x0, y0, x1, y1) in m.items():
        if x0 <= x <= x1 and y0 <= y <= y1:
            return chave
    return None
