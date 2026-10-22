"""pixel.py - mini engine de pixel art: volumes sombreados, dithering, sel-out e glow.

Tudo é desenhado em coordenadas "lógicas" de 48x48 que passam por uma transformação
(pivô nos pés + squash & stretch + deslocamento sub-pixel), então o mesmo desenho
serve pra respirar, pular e amassar sem redesenhar nada à mão.
"""
import math

from PIL import Image

W = 48

# Paleta Sweetie 16 (by GrafxKid), CC0 - o tempero oficial do bicho
P = {
    "preto": "#1a1c2c", "roxo": "#5d275d", "vinho": "#b13e53", "laranja": "#ef7d57",
    "amarelo": "#ffcd75", "lima": "#a7f070", "verde": "#38b764", "petroleo": "#257179",
    "marinho": "#29366f", "azul": "#3b5dc9", "celeste": "#41a6f6", "ciano": "#73eff7",
    "branco": "#f4f4f4", "cinza_claro": "#94b0c2", "cinza": "#566c86", "grafite": "#333c57",
}

# rampas escuro -> claro (sombra, base, luz, brilho)
RAMPAS = {
    "laranja": ["roxo", "vinho", "laranja", "amarelo"],
    "ouro": ["vinho", "laranja", "amarelo", "branco"],
    "sol": ["vinho", "laranja", "laranja", "amarelo", "amarelo"],
    "pele": ["vinho", "laranja", "amarelo", "amarelo"],
    "creme": ["laranja", "amarelo", "branco"],
    "barba": ["cinza", "cinza_claro", "branco"],
    "pedra": ["grafite", "cinza", "cinza_claro", "branco"],
    "metal": ["grafite", "cinza", "cinza_claro", "branco"],
    "escuro": ["preto", "grafite", "cinza"],
    "azul": ["marinho", "azul", "celeste", "ciano"],
    "cristal": ["marinho", "azul", "celeste", "ciano", "branco"],
    "verde": ["petroleo", "verde", "lima"],
    "barriga": ["verde", "lima", "branco"],
    "papelao": ["roxo", "vinho", "laranja"],
    "madeira": ["roxo", "vinho"],
    "terno": ["preto", "grafite", "cinza"],
    "tela": ["preto", "marinho"],
    "nuvem": ["cinza", "cinza_claro", "branco"],
    "fogo": ["vinho", "laranja", "amarelo", "branco"],
    "ciano": ["celeste", "ciano", "branco"],
    "vermelho": ["roxo", "vinho", "laranja"],
}

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def rgb(nome_ou_hex):
    if nome_ou_hex not in P and nome_ou_hex in RAMPAS:  # nome de rampa -> tom do meio
        r = RAMPAS[nome_ou_hex]
        nome_ou_hex = r[len(r) // 2]
    h = P.get(nome_ou_hex, nome_ou_hex).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


FONTE35 = {
    "H": "101101111101101", "O": "111101101101111", "D": "110101101101110", "L": "100100100100111",
    "9": "111101111001111", "B": "110101110101110", "Z": "111001010100111", "$": "011110010011110",
    "W": "101101101111101", "G": "111100101101111", "A": "010101111101101", "S": "111100111001111",
    "E": "111100110100111", "I": "111010010010111", "X": "101101010101101", "R": "110101110101101",
    "P": "110101110100100", "!": "010010010000010", "Ξ": "111000111000111", "K": "101101110101101",
}


class Sprite:
    def __init__(self, sx=1.0, sy=1.0, dx=0.0, dy=0.0, piv=(24, 44)):
        self.cor = [[None] * W for _ in range(W)]
        self.mat = [[None] * W for _ in range(W)]
        self.fx = []
        self.tf = (piv[0], piv[1], sx, sy, dx, dy)
        self.ancora = (24, 8, 8)

    # ---------- transformação ----------
    def T(self, x, y):
        px, py, sx, sy, dx, dy = self.tf
        return px + (x - px) * sx + dx, py + (y - py) * sy + dy

    def Ti(self, x, y):
        px, py, sx, sy, dx, dy = self.tf
        return px + (x - dx - px) / sx, py + (y - dy - py) / sy

    def marcar_ancora(self, cx, topo, meia):
        x, y = self.T(cx, topo)
        self.ancora = (x, y, meia * self.tf[2])

    # ---------- pixel básico ----------
    def set(self, x, y, cor, mat="escuro"):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < W:
            self.cor[y][x] = rgb(cor)
            self.mat[y][x] = mat

    def _rampa_idx(self, v, n, x, y):
        """v em 0..1 -> índice da rampa, com dithering Bayer só na faixa de transição."""
        t = max(0.0, min(0.999, v)) * n
        base = int(t)
        frac = t - base
        if 0.3 < frac < 0.7 and base + 1 < n:  # zona de dithering
            if (frac - 0.3) / 0.4 * 16 > BAYER[y % 4][x % 4]:
                base += 1
        elif frac >= 0.7 and base + 1 < n:
            base += 1
        return min(base, n - 1)

    def _pintar(self, x, y, v, rampa, mat=None):
        r = RAMPAS[rampa]
        self.set(x, y, r[self._rampa_idx(v, len(r), x, y)], mat or rampa)

    # ---------- volumes ----------
    def esfera(self, cx, cy, rx, ry, rampa, luz=0.0, clip=None):
        """Elipse com sombreamento de esfera (luz vindo de cima-esquerda-frente)."""
        sx, sy = self.tf[2], self.tf[3]
        cx, cy = self.T(cx, cy)
        rx, ry = rx * sx, ry * sy
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                d = nx * nx + ny * ny
                if d > 1:
                    continue
                if clip and not clip(*self.Ti(x + 0.5, y + 0.5)):
                    continue
                nz = math.sqrt(1 - d)
                v = (-0.45 * nx - 0.6 * ny + 0.66 * nz) * 0.5 + 0.34 + luz
                self._pintar(x, y, v, rampa)

    def caixa(self, x0, y0, x1, y1, rampa, raio=1, luz=0.0, clip=None):
        """Retângulo arredondado com sombreamento cilíndrico + gradiente vertical."""
        X0, Y0 = self.T(x0, y0)
        X1, Y1 = self.T(x1, y1)
        w, h = max(1.0, X1 - X0), max(1.0, Y1 - Y0)
        for y in range(round(Y0), round(Y1)):
            for x in range(round(X0), round(X1)):
                # cantos arredondados
                cx = min(x - X0 + 0.5, X1 - x - 0.5)
                cy = min(y - Y0 + 0.5, Y1 - y - 0.5)
                if raio and cx < raio and cy < raio and (raio - cx) ** 2 + (raio - cy) ** 2 > raio * raio:
                    continue
                if clip and not clip(*self.Ti(x + 0.5, y + 0.5)):
                    continue
                nx = (x + 0.5 - X0) / w * 2 - 1
                ny = (y + 0.5 - Y0) / h
                v = 0.7 - 0.42 * ny - 0.26 * nx + luz
                if x - X0 < 1:
                    v += 0.15  # quina iluminada
                self._pintar(x, y, v, rampa)

    def poly(self, pts, rampa, luz=0.5, grad=0.0):
        """Polígono com tom fixo (luz) e gradiente opcional de cima pra baixo."""
        pts = [self.T(*p) for p in pts]
        ys = [p[1] for p in pts]
        y_min, y_max = min(ys), max(ys)
        for y in range(int(y_min), int(y_max) + 1):
            yc = y + 0.5
            xs = []
            for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]):
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                for x in range(round(a), round(b)):
                    t = (yc - y_min) / max(1, y_max - y_min)
                    self._pintar(x, y, luz - grad * t, rampa)

    def linha(self, pts, cor, mat=None, larg=1):
        pts = [self.T(*p) for p in pts]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            n = int(max(abs(xb - xa), abs(yb - ya))) + 1
            for i in range(n + 1):
                x = xa + (xb - xa) * i / n
                y = ya + (yb - ya) * i / n
                for k in range(larg):
                    self.set(x + (k if abs(yb - ya) > abs(xb - xa) else 0),
                             y + (0 if abs(yb - ya) > abs(xb - xa) else k), cor, mat or "escuro")

    def ret(self, x, y, w, h, cor, mat="escuro"):
        """Retângulo de pixels exatos (olhos, detalhes) - só a origem é transformada."""
        X, Y = self.T(x, y)
        X, Y = round(X), round(Y)
        for j in range(h):
            for i in range(w):
                self.set(X + i, Y + j, cor, mat)

    def texto(self, x, y, s, cor, mat="escuro"):
        X, Y = self.T(x, y)
        X, Y = round(X), round(Y)
        for ch in s:
            g = FONTE35.get(ch)
            if g:
                for j in range(5):
                    for i in range(3):
                        if g[j * 3 + i] == "1":
                            self.set(X + i, Y + j, cor, mat)
            X += 4

    def efeito(self, x, y, cor):
        """Partículas: desenhadas depois do contorno e sem transformação."""
        self.fx.append((int(x), int(y), rgb(cor)))

    # ---------- acabamento ----------
    def finalizar(self, contorno="preto", glow=None):
        out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        preto = rgb(contorno)
        cor = [row[:] for row in self.cor]
        borda = [[False] * W for _ in range(W)]
        for y in range(W):
            for x in range(W):
                if self.cor[y][x] is not None:
                    continue
                viz = None
                lado_luz = False
                for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < W and self.cor[ny][nx] is not None:
                        viz = self.mat[ny][nx]
                        lado_luz = lado_luz or dx > 0 or dy > 0  # vazio à esquerda/acima do desenho
                if viz:
                    # sel-out: lado iluminado ganha contorno na cor escura do material
                    r = RAMPAS.get(viz)
                    if lado_luz and r and contorno == "preto":
                        cor[y][x] = rgb(r[0]) if rgb(r[0]) != rgb("amarelo") else preto
                    else:
                        cor[y][x] = preto
                    borda[y][x] = True
        # contorno nas quinas de baixo/direita sempre preto (peso visual)
        for y in range(W):
            for x in range(W):
                if borda[y][x] and ((x > 0 and self.cor[y][x - 1] is not None) or
                                    (y > 0 and self.cor[y - 1][x] is not None)):
                    cor[y][x] = preto
        if glow:  # brilho neon: anel dithered em volta do contorno
            g1, g2 = rgb(glow[0]), rgb(glow[1])
            base = [[c is not None for c in row] for row in cor]
            for y in range(W):
                for x in range(W):
                    if base[y][x]:
                        continue
                    dmin = 9
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < W and 0 <= ny < W and base[ny][nx]:
                                dmin = min(dmin, abs(dx) + abs(dy))
                    if dmin == 1:
                        cor[y][x] = g1
                    elif dmin == 2 and (x + y) % 2 == 0:
                        cor[y][x] = g2
        for y in range(W):
            for x in range(W):
                c = cor[y][x]
                if c is not None:
                    out.putpixel((x, y), c + (255,))
        for x, y, c in self.fx:
            if 0 <= x < W and 0 <= y < W:
                out.putpixel((x, y), c + (255,))
        return out
