"""sprites.py - o ateliê: 5 criaturas x 4 animações x 4 frames, 48x48, paleta Sweetie 16.

Gera as folhas em assets/sprites/<MOEDA>_<SKIN>.png (192x192: linhas = garimpando,
moon, rekt, pulo; colunas = frames). Rode `python -m tamagoshi_cripto.sprites`
(precisa do Pillow) depois de mexer em qualquer desenho.
"""
import math
from pathlib import Path

from PIL import Image

from .pixel import W, Sprite, rgb

ESTADOS = ("garimpando", "moon", "rekt")
LINHAS = ESTADOS + ("pulo",)
FRAMES = 4
ASSETS = Path(__file__).parent / "assets"
PASTA = ASSETS / "sprites"

# respiração (idle) e pulo com squash & stretch: (sx, sy, dy)
IDLE = [(1.03, 0.97, 0.0), (1.0, 1.0, -0.5), (0.98, 1.03, -1.0), (1.0, 1.0, -0.5)]
PULO = [(1.2, 0.8, 0.0), (0.86, 1.18, -6.0), (1.0, 1.0, -11.0), (1.14, 0.86, 0.0)]


# ======================= peças reutilizáveis =======================
def olhos(s, x, y, gap, tipo, cor="preto"):
    for ox in (x, x + gap):
        if tipo == "normal":
            s.ret(ox, y, 2, 3, cor); s.ret(ox, y, 1, 1, "branco")
        elif tipo == "pisca":
            s.ret(ox, y + 2, 2, 1, cor)
        elif tipo == "feliz":  # ^ ^
            s.ret(ox, y + 1, 1, 1, cor); s.ret(ox + 1, y, 1, 1, cor); s.ret(ox + 2, y + 1, 1, 1, cor)
        elif tipo == "x":
            for d in range(3):
                s.ret(ox + d, y + d, 1, 1, cor); s.ret(ox + 2 - d, y + d, 1, 1, cor)
        elif tipo == "triste":
            s.ret(ox, y + 1, 2, 2, cor); s.ret(ox + (0 if ox == x else 1), y, 1, 1, cor)
    if tipo == "oculos":
        s.ret(x - 2, y - 1, gap + 6, 1, "preto")
        for ox in (x - 1, x + gap - 1):
            s.ret(ox, y, 4, 3, "preto"); s.ret(ox + 1, y, 1, 1, "ciano"); s.ret(ox + 2, y + 1, 1, 1, "celeste")


def chao(s, rampa_topo="verde", rampa_terra="papelao", tufos=True):
    s2 = s
    for x in range(4, 44):
        s2.set(x, 45, "petroleo" if rampa_topo == "verde" else "grafite", rampa_topo)
        s2.set(x, 44, "verde" if rampa_topo == "verde" else "cinza", rampa_topo)
        s2.set(x, 46, "preto")
    if tufos:
        for x in (7, 15, 33, 40):
            s2.set(x, 43, "lima" if rampa_topo == "verde" else "cinza_claro", rampa_topo)


def sombra(s, cx=24, larg=10):
    for x in range(int(cx - larg), int(cx + larg) + 1):
        if (x % 2 == 0) or abs(x - cx) < larg - 3:
            s.set(x, 45, "grafite")


def faiscas(s, pts, cores=("amarelo", "branco")):
    for i, (x, y) in enumerate(pts):
        c = cores[i % len(cores)]
        s.efeito(x, y, c)
        if i % 2 == 0:
            s.efeito(x + 1, y, cores[0]); s.efeito(x - 1, y, cores[0])
            s.efeito(x, y + 1, cores[0]); s.efeito(x, y - 1, cores[0])


def chuva(s, f):
    for i, x in enumerate((4, 11, 18, 27, 35, 42)):
        y = (i * 9 + f * 6) % 30
        s.efeito(x, y, "ciano"); s.efeito(x, y + 1, "celeste"); s.efeito(x, y + 2, "azul")


def lagrimas(s, x, y, f):
    for k in range(3):
        yy = y + 2 + ((f + k) % 4) * 2
        s.efeito(x, yy, "ciano" if k else "branco")


def chama(s, x, y, f, direcao=-1, tam=1.0):
    """Fogo de foguete com 4 frames de turbulência (para a esquerda por padrão)."""
    comp = [9, 11, 8, 12][f] * tam
    for i in range(int(comp)):
        meia = max(0, int((1 - i / comp) * 3.5 * tam + (0.5 if (i + f) % 3 == 0 else 0)))
        for j in range(-meia, meia + 1):
            t = i / comp + abs(j) / (meia + 1) * 0.5
            cor = "branco" if t < 0.2 else "amarelo" if t < 0.45 else "laranja" if t < 0.75 else "vinho"
            s.efeito(x + direcao * i, y + j, cor)
    for k in range(3):
        s.efeito(x + direcao * (comp + 2 + (f * 3 + k * 4) % 6), y + (k - 1) * 2, "laranja")


# ======================= Satoshinho (BTC) =======================
def satoshinho(s, e, f, k):
    if e == "rekt":
        chao(s)
        # túmulo com musgo e rachadura
        s.esfera(24, 17, 12, 9, "pedra", clip=lambda x, y: y < 18)
        s.caixa(12, 17, 36.5, 44, "pedra", raio=0)
        s.texto(16, 20, "HODL", "grafite"); s.texto(16, 21, "HODL", "cinza_claro")
        s.texto(16, 20, "HODL", "grafite")
        s.linha([(31, 27), (29, 31), (31, 34)], "grafite")
        s.texto(20, 29, "RIP", "cinza")
        for x in range(12, 37, 2):
            s.set(x, 43 - (x % 3 == 0), "verde", "verde")
        # capacete repousando no topo
        s.esfera(24, 9, 7, 5, "laranja", clip=lambda x, y: y < 10)
        s.caixa(16, 9, 32.5, 11, "laranja", raio=0)
        s.ret(23, 6, 2, 2, "ciano")
        # picareta fincada
        s.linha([(40, 44), (40, 30)], "vinho", "madeira", 2)
        s.poly([(34, 30), (41, 28), (47, 31), (41, 30)], "metal", 0.75)
        chuva(s, f)
        # fantasminha do Satoshinho subindo
        gy = 6 - f
        if f >= 2:
            s.efeito(5, gy + 4, "branco"); s.efeito(6, gy + 3, "branco"); s.efeito(7, gy + 4, "branco")
            s.efeito(6, gy + 4, "cinza_claro")
        s.marcar_ancora(24, 5, 7)
        return
    if e == "moon":
        # bloco-foguete: cubo laranja com ₿, nariz de metal, aletas
        s.poly([(10, 31), (13, 27), (39, 27), (36, 31)], "laranja", 0.95)  # tampa
        s.caixa(10, 31, 36, 43, "laranja", raio=0)
        s.poly([(36, 31), (39, 27), (39, 39), (36, 43)], "laranja", 0.15)  # lateral
        s.ret(20, 33, 1, 8, "branco"); s.ret(23, 33, 1, 8, "branco")
        s.ret(19, 34, 7, 1, "branco"); s.ret(19, 37, 7, 1, "branco"); s.ret(19, 40, 7, 1, "branco")
        s.ret(25, 35, 1, 2, "branco"); s.ret(25, 38, 1, 2, "branco")
        s.poly([(39, 29), (46, 34), (39, 40)], "metal", 0.7, grad=0.4)
        s.poly([(12, 43), (8, 47), (16, 43)], "vermelho", 0.6)
        s.ret(8, 33, 2, 8, "grafite")
        chama(s, 7, 37, f)
        for i in range(4):  # linhas de velocidade
            y = 6 + i * 6 + (f % 2)
            for x in range(1 + (i * 5 + f * 3) % 6, 5 + (i * 5 + f * 3) % 6):
                s.efeito(x, y, "celeste")
        top = 5
    else:
        chao(s, "verde")
        sombra(s)
        top = 9
    # ----- o anão -----
    s.esfera(24, top + 18, 10, 8, "azul")  # túnica
    if e != "moon":
        s.caixa(14, top + 22, 34, top + 24, "escuro", raio=0)  # cinto
        s.ret(22, top + 22, 4, 2, "amarelo", "ouro")
        s.esfera(19, top + 31, 4, 3, "escuro"); s.esfera(29, top + 31, 4, 3, "escuro")  # botas
    s.esfera(24, top + 13, 9.5, 7, "barba")  # barbão
    s.esfera(24, top + 8, 7, 5.5, "pele")  # rosto
    s.esfera(24, top + 4, 9, 7, "laranja", clip=lambda x, y: y < top + 4.5)  # capacete
    s.caixa(13.5, top + 3.5, 34.5, top + 6, "laranja", raio=1)
    s.esfera(24, top + 1, 2.2, 2, "ciano")
    s.ret(23, top, 1, 1, "branco")
    s.esfera(24, top + 10, 2.2, 1.8, "laranja")  # narigão
    if e == "moon":
        olhos(s, 20, top + 7, 6, "oculos")
        s.ret(22, top + 12, 5, 1, "vinho")
        braco = -1 if f % 2 else 0
        s.linha([(15, top + 16), (10, top + 9 + braco), (9, top + 7 + braco)], "azul", "azul", 2)
        s.linha([(33, top + 16), (38, top + 9 - braco), (39, top + 7 - braco)], "azul", "azul", 2)
        s.esfera(9, top + 6 + braco, 1.6, 1.6, "pele"); s.esfera(39, top + 6 - braco, 1.6, 1.6, "pele")
        faiscas(s, [(4 + f, 4), (44 - f, 7), (2, 20 - f), (45, 18 + f)], ("amarelo", "branco"))
    else:
        olhos(s, 20, top + 7, 6, "pisca" if f == 3 else "normal")
        # picareta: ciclo de 4 frames (levanta, topo, golpe, recupera)
        ang = [-50, -75, 20, -10][f]
        hx, hy = 33, top + 17
        a = math.radians(ang)
        ex, ey = hx + math.cos(a) * 13, hy + math.sin(a) * 13
        s.linha([(hx, hy), (ex, ey)], "vinho", "madeira", 2)
        px_, py_ = -math.sin(a), math.cos(a)
        s.poly([(ex - px_ * 6, ey - py_ * 6), (ex + math.cos(a) * 2, ey + math.sin(a) * 2),
                (ex + px_ * 6, ey + py_ * 6), (ex - math.cos(a) * 1, ey - math.sin(a) * 1)], "metal", 0.8)
        s.esfera(hx, hy, 2, 2, "pele")
        if f == 2:
            faiscas(s, [(44, 41), (46, 38), (41, 37), (45, 43), (47, 40)])
        elif f == 3:
            faiscas(s, [(45, 36), (47, 34)], ("laranja", "amarelo"))
            for x, y in ((40, 43), (42, 42)):
                s.efeito(x, y, "laranja")
    s.marcar_ancora(24, top - 2, 9)


# ======================= Vitalikinho (ETH) =======================
def vitalikinho(s, e, f, k):
    chao(s, "pedra")
    sombra(s)
    if e == "rekt":
        s.caixa(15, 22, 33, 33, "metal", raio=2)
        s.caixa(17, 24, 31, 31, "tela", raio=1)
        olhos(s, 19, 26, 7, "x", "vinho")
        s.caixa(16, 33, 32, 41, "metal", raio=1)
        s.ret(18, 41, 4, 3, "grafite"); s.ret(26, 41, 4, 3, "grafite")
        # chapéu de cristal derretido escorrendo
        s.poly([(13, 22), (16, 15), (24, 12 + f % 2), (32, 15), (35, 22)], "cristal", 0.65, grad=0.3)
        for x, h in ((14, 6), (18, 3), (22, 8), (27, 4), (31, 9), (34, 5)):
            hh = h + (f % 2)
            s.caixa(x, 21, x + 2, 22 + hh, "cristal", raio=0)
            s.esfera(x + 1, 22 + hh, 1.4, 1.4, "cristal")
        s.esfera(10, 44, 6, 1.6, "cristal"); s.esfera(37, 44, 5, 1.4, "cristal")
        s.texto(18, 3, "999", "vinho"); s.texto(18, 2, "999", "laranja")
        for i in range(3):  # fumacinha
            y = 10 - ((f + i * 2) % 6)
            s.efeito(38 + i, y, "cinza_claro"); s.efeito(39 + i, y - 1, "cinza")
        s.marcar_ancora(24, 13, 10)
        return
    # corpo
    s.caixa(16, 31, 32, 40, "metal", raio=2)
    s.poly([(24, 32), (27, 35.5), (24, 39), (21, 35.5)], "cristal", 0.8)
    s.ret(18, 40, 4, 4, "grafite"); s.ret(26, 40, 4, 4, "grafite")
    s.ret(17, 43, 6, 1, "cinza"); s.ret(25, 43, 6, 1, "cinza")
    # cabeça-monitor
    s.caixa(14, 18, 34, 30, "metal", raio=2)
    s.caixa(16.5, 20, 31.5, 28, "tela", raio=1)
    for y in (21, 23, 25, 27):
        s.ret(17, y, 14, 1, "marinho")
    if e == "moon":
        olhos(s, 19, 22, 7, "oculos")
        s.ret(21, 26, 6, 1, "ciano")
    else:
        if f == 3:
            olhos(s, 19, 23, 7, "pisca", "ciano")
        else:
            s.ret(19, 22, 3, 3, "ciano", "ciano"); s.ret(26, 22, 3, 3, "ciano", "ciano")
            s.ret(19, 22, 1, 1, "branco"); s.ret(26, 22, 1, 1, "branco")
        s.ret(22, 26, 4, 1, "celeste")
    # chapéu de cristal (octaedro do ETH) com aba
    s.esfera(24, 18, 13, 2.6, "cristal", luz=-0.15)
    s.poly([(24, 0), (32, 15), (24, 18)], "cristal", 0.45, grad=0.15)  # faceta escura
    s.poly([(24, 0), (16, 15), (24, 18)], "cristal", 0.85, grad=0.25)  # faceta clara
    s.linha([(24, 1), (24, 16)], "branco", "cristal")
    s.ret(21, 8, 1, 2, "branco")
    if e == "moon":
        a = -1 if f % 2 else 0
        s.linha([(15, 33), (9, 26 + a), (8, 23 + a)], "cinza_claro", "metal", 2)
        s.linha([(33, 33), (39, 26 - a), (40, 23 - a)], "cinza_claro", "metal", 2)
        pts = [(5 + f, 6), (42 - f, 4), (3, 14 + f), (44, 13 - f), (6, 30 - f), (43, 28 + f)]
        faiscas(s, pts, ("amarelo", "branco", "ciano"))
        s.texto(1, 40 - f * 2, "GAS", "amarelo") if f < 2 else s.texto(33, 42 - f * 3, "Ξ", "ciano")
    else:
        # cajado com orbe brilhando
        s.linha([(34, 34), (40, 20)], "vinho", "madeira", 2)
        s.esfera(41, 18, 2.6, 2.6, "ciano")
        if f in (1, 2):
            faiscas(s, [(44, 14 + f), (38, 13), (45, 21)], ("branco", "ciano"))
        s.esfera(34, 34, 1.8, 1.8, "metal")
    s.marcar_ancora(24, 17, 11)


# ======================= Solzinho (SOL) =======================
def solzinho(s, e, f, k):
    cx, cy, r = 24, 24, 11
    if e == "rekt":
        sombra(s, 24, 9)
        s.esfera(cx, cy, r, r, "pedra", luz=-0.15)
        for i in range(8):  # raios caídos, sem energia
            a = math.radians(i * 45 + 22)
            x0, y0 = cx + math.cos(a) * (r + 1), cy + math.sin(a) * (r + 1)
            s.linha([(x0, y0), (x0 + math.cos(a) * 3, y0 + 3)], "cinza", "pedra")
        olhos(s, 18, 21, 9, "x", "preto")
        s.ret(21, 29, 7, 1, "grafite")
        # tomada desconectada
        s.linha([(24, 35), (22, 40), (16, 42)], "grafite", "escuro", 2)
        s.caixa(11, 40, 17, 45, "escuro", raio=1)
        s.caixa(31, 38, 40, 45.5, "metal", raio=1)
        s.ret(34, 40, 1, 2, "preto"); s.ret(37, 40, 1, 2, "preto")
        if f in (1, 3):
            faiscas(s, [(19, 39), (20, 37)], ("amarelo", "branco"))
        s.texto(36, 6 - f % 2, "Z", "cinza_claro"); s.texto(41, 2 - f % 2, "Z", "cinza")
        s.marcar_ancora(24, cy - r, 9)
        return
    sombra(s, 24, 9)
    girando = e == "moon"
    rot = (f * 22.5) if girando else (math.sin(f * math.pi / 2) * 6)
    for i in range(8):
        a = math.radians(i * 45 + rot)
        comp = (8 if i % 2 == 0 else 6) + (1 if (f + i) % 2 else 0)
        base = r + 1.5
        p0 = (cx + math.cos(a) * base, cy + math.sin(a) * base)
        p1 = (cx + math.cos(a) * (base + comp), cy + math.sin(a) * (base + comp))
        n = (-math.sin(a) * 2.6, math.cos(a) * 2.6)
        s.poly([(p0[0] + n[0], p0[1] + n[1]), p1, (p0[0] - n[0], p0[1] - n[1])], "laranja", 0.6 if i % 2 else 0.8)
    s.esfera(cx, cy, r, r, "sol", luz=0.08)
    s.ret(17, 17, 2, 2, "branco", "sol"); s.ret(19, 16, 2, 1, "branco", "sol"); s.ret(16, 19, 1, 1, "branco", "sol")
    if girando:
        for i in range(3):  # rastro de giro
            a = math.radians(rot + 200 + i * 15)
            s.efeito(cx + math.cos(a) * (r + 12), cy + math.sin(a) * (r + 12), "amarelo")
        olhos(s, 18, 21, 10, "oculos")
        s.ret(20, 28, 9, 2, "vinho"); s.ret(21, 30, 7, 1, "roxo"); s.ret(23, 29, 3, 1, "laranja")
    else:
        olhos(s, 19, 21, 8, "pisca" if f == 3 else "normal")
        s.ret(21, 28, 1, 1, "roxo"); s.ret(22, 29, 5, 1, "roxo"); s.ret(27, 28, 1, 1, "roxo")
        for x, y in ((16, 26), (17, 27), (31, 26), (32, 27)):
            s.set(x, y, "laranja", "ouro")
    s.marcar_ancora(24, cy - r, 9)


# ======================= Doguinho (DOGE) =======================
def doguinho(s, e, f, k):
    if e != "moon":
        chao(s, "verde")
        sombra(s, 24, 11)
    else:
        sombra(s, 24, 7)
    cab_y = 16 if e != "rekt" else 17
    # rabinho enrolado (abana)
    t = [0, 1, 2, 1][f]
    s.esfera(36 + t * 0.5, 31 - t, 4, 4, "laranja")
    s.esfera(36.5 + t * 0.5, 30 - t, 2, 2, "creme")
    # corpo sentado
    s.esfera(24, 34, 10, 9, "laranja")
    s.esfera(24, 36, 6, 7, "creme")
    s.esfera(19, 42, 3.4, 2.4, "creme"); s.esfera(29, 42, 3.4, 2.4, "creme")
    # orelhas
    caida = 4 if e == "rekt" else 0
    s.poly([(14, cab_y - 1 + caida), (15, cab_y - 11 + caida * 1.5), (21, cab_y - 5)], "laranja", 0.75)
    s.poly([(34, cab_y - 1 + caida), (33, cab_y - 11 + caida * 1.5), (27, cab_y - 5)], "laranja", 0.45)
    s.poly([(16, cab_y - 3 + caida), (16, cab_y - 8 + caida), (19.5, cab_y - 5)], "vermelho", 0.7)
    s.poly([(32, cab_y - 3 + caida), (32, cab_y - 8 + caida), (28.5, cab_y - 5)], "vermelho", 0.7)
    # cabeça
    s.esfera(24, cab_y, 11, 8.5, "laranja")
    s.esfera(24, cab_y + 4, 7.5, 4.6, "creme")
    s.esfera(15.5, cab_y + 2, 3, 3, "creme"); s.esfera(32.5, cab_y + 2, 3, 3, "creme")
    s.ret(19, cab_y - 5, 2, 1, "amarelo", "creme"); s.ret(27, cab_y - 5, 2, 1, "amarelo", "creme")  # sobrancelhas
    s.esfera(24, cab_y + 2, 2, 1.4, "escuro")  # nariz
    s.ret(23, cab_y + 1, 1, 1, "cinza")
    if e == "moon":
        olhos(s, 18, cab_y - 3, 9, "oculos")
        s.ret(22, cab_y + 5, 4, 1, "preto"); s.ret(23, cab_y + 6, 2, 3, "vinho", "vermelho")
        s.ret(23, cab_y + 6, 1, 1, "laranja")
        chama(s, 19, 47, f, direcao=0, tam=0.5) if False else None
        for x in (19, 29):  # botinhas-foguete
            for i in range(2 + f % 2):
                s.efeito(x, 46 + i, "amarelo" if i == 0 else "laranja")
        s.texto(1, 3 + f % 2, "WOW", "amarelo")
        faiscas(s, [(42, 6 + f), (6, 22 - f), (44, 24)], ("amarelo", "branco"))
    elif e == "rekt":
        olhos(s, 18, cab_y - 2, 9, "triste")
        s.ret(22, cab_y + 6, 4, 1, "preto"); s.ret(21, cab_y + 7, 1, 1, "preto"); s.ret(26, cab_y + 7, 1, 1, "preto")
        lagrimas(s, 18, cab_y, f); lagrimas(s, 29, cab_y, f)
        # nuvem de chuva particular
        s.esfera(12, 4, 5, 2.6, "nuvem"); s.esfera(19, 3, 5, 3, "nuvem"); s.esfera(15, 1.5, 4, 2.4, "nuvem")
        for i, x in enumerate((9, 12, 15, 18, 21)):
            y = 7 + ((f * 2 + i * 3) % 5)
            s.efeito(x, y, "celeste"); s.efeito(x, y + 1, "azul")
    else:
        olhos(s, 18, cab_y - 3, 9, "pisca" if f == 3 else "normal")
        s.ret(22, cab_y + 5, 1, 1, "preto"); s.ret(23, cab_y + 6, 2, 1, "preto"); s.ret(25, cab_y + 5, 1, 1, "preto")
    s.marcar_ancora(24, cab_y - 8, 9)


# ======================= Sapo Degen (PEPE) =======================
def sapo_degen(s, e, f, k):
    y0 = 0 if e != "rekt" else 3
    if e != "rekt":
        chao(s, "verde")
        sombra(s, 24, 13)
    # corpo + olhos saltados
    s.esfera(24, 31 + y0, 15, 10, "verde")
    if e != "moon":
        s.esfera(24, 35 + y0, 10, 6, "barriga")
    for ex in (15, 33):
        s.esfera(ex, 20 + y0, 6, 5.5, "verde")
        s.esfera(ex, 20 + y0, 4, 3.6, "creme", luz=0.3)
    s.ret(9, 29 + y0, 2, 1, "petroleo"); s.ret(37, 29 + y0, 2, 1, "petroleo")
    # bocão
    s.linha([(12, 29 + y0), (16, 31 + y0), (32, 31 + y0), (36, 29 + y0)], "roxo")
    s.esfera(12, 28 + y0, 1.8, 1.2, "vermelho", luz=0.2); s.esfera(36, 28 + y0, 1.8, 1.2, "vermelho", luz=0.2)
    if e == "moon":
        s.ret(10, 18, 6, 3, "preto"); s.ret(31, 18, 6, 3, "preto"); s.ret(16, 18, 15, 1, "preto")
        s.ret(11, 18, 1, 1, "ciano"); s.ret(32, 18, 1, 1, "ciano")
        # terno + gravata + cordão de ouro
        s.esfera(24, 39, 13, 6.5, "terno")
        s.poly([(19, 33), (24, 41), (29, 33)], "barba", 0.95)
        s.poly([(23, 34), (25, 34), (26, 39), (24, 41), (22, 39)], "vermelho", 0.7)
        for i in range(13):
            x = 13 + i * 1.8
            y = 34 + math.sin(i / 12 * math.pi) * 5
            s.set(x, y, "amarelo" if (i + f) % 4 else "branco", "ouro")
        s.esfera(24, 39.5, 2.2, 2.2, "ouro")
        s.texto(23, 38, "$", "vinho") if False else s.ret(24, 38, 1, 3, "laranja", "ouro")
        for i, (x, y) in enumerate(((5, 10), (42, 6), (44, 22), (3, 26))):  # moedinhas caindo
            yy = (y + f * 3) % 30
            s.efeito(x, yy, "amarelo"); s.efeito(x + 1, yy, "laranja"); s.efeito(x, yy + 1, "laranja")
    elif e == "rekt":
        for ex in (14, 31):
            s.ret(ex, 20 + y0, 3, 3, "preto"); s.ret(ex, 20 + y0, 1, 1, "branco")
            s.ret(ex - 2, 18 + y0, 7, 1, "verde", "verde")  # pálpebra caída
        lagrimas(s, 14, 22 + y0, f)
        # caixa de papelão
        s.caixa(5, 31, 43, 46, "papelao", raio=0)
        s.poly([(5, 31), (0, 24 + (f % 2)), (3, 22 + (f % 2)), (10, 31)], "papelao", 0.85)
        s.poly([(43, 31), (47, 25 - (f % 2)), (44, 23 - (f % 2)), (38, 31)], "papelao", 0.6)
        s.ret(21, 36, 7, 2, "roxo", "papelao")
        s.texto(12, 40, "HODL", "roxo")
        a = f * math.pi / 2  # mosquinha rodeando
        mx, my = 38 + math.cos(a) * 5, 12 + math.sin(a) * 3
        s.efeito(mx, my, "preto"); s.efeito(mx + 1, my - 1, "branco")
    else:
        for ex in (14, 32):
            if f == 3:
                s.ret(ex - 1, 21, 4, 1, "petroleo")
            else:
                s.ret(ex, 19, 2, 3, "preto"); s.ret(ex, 19, 1, 1, "branco")
        s.esfera(17, 43, 4, 1.8, "verde"); s.esfera(31, 43, 4, 1.8, "verde")
        if f == 1:  # linguada!
            s.linha([(24, 31), (32, 26), (40, 20)], "vermelho", "vermelho", 2)
            s.esfera(41, 19, 1.5, 1.5, "vermelho")
        else:
            s.efeito(41, 12 + f, "preto"); s.efeito(42, 11 + f, "cinza_claro"); s.efeito(40, 11 + f, "cinza_claro")
    s.marcar_ancora(24, 15 + y0, 13)


PERSONAGENS = {"BTC": satoshinho, "ETH": vitalikinho, "SOL": solzinho, "DOGE": doguinho, "PEPE": sapo_degen}

# ======================= skins =======================
SKINS = ["padrao", "cyberpunk", "gato", "sapo", "satoshi"]  # "satoshi" = secreta (código konami)
SKINS_SECRETAS = {"satoshi"}

NEON = ["#1a1c2c", "#2b1650", "#5b2a9c", "#a43fd6", "#ff5fd2", "#ffc4f2"]
DOURADO = ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75", "#fff4c0"]


def _remap_lum(img, rampa, contorno=None):
    out = img.copy()
    px = out.load()
    alvo = [rgb(c) for c in rampa]
    for y in range(W):
        for x in range(W):
            r, g, b, a = px[x, y]
            if not a:
                continue
            if contorno and (r, g, b) == rgb("#1a1c2c"):
                px[x, y] = rgb(contorno) + (255,)
                continue
            lum = ((r * 3 + g * 6 + b) / 10 / 256) ** 1.5  # gama: segura o brilho
            px[x, y] = alvo[min(len(alvo) - 1, int(lum * len(alvo) * 1.05))] + (255,)
    return out


def _tingir(img, cor, forca):
    out = img.copy()
    px = out.load()
    a_ = rgb(cor)
    for y in range(W):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a and (r, g, b) != rgb("#1a1c2c"):
                px[x, y] = tuple(int(c * (1 - forca) + t * forca) for c, t in zip((r, g, b), a_)) + (255,)
    return out


def _glow(img, c1, c2):
    out = img.copy()
    src = img.load()
    px = out.load()
    for y in range(W):
        for x in range(W):
            if src[x, y][3]:
                continue
            d = 9
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < W and src[nx, ny][3]:
                        d = min(d, abs(dx) + abs(dy))
            if d == 1:
                px[x, y] = rgb(c1) + (255,)
            elif d == 2 and (x + y) % 2 == 0:
                px[x, y] = rgb(c2) + (255,)
    return out


def acessorio(s, skin):
    cx, t, w = s.ancora
    t = max(t, 6)
    L, R = cx - w, cx + w
    if skin == "gato":
        for x0, lado in ((L, 1), (R, -1)):
            s.poly([(x0 - lado, t + 3), (x0 + lado * 0.5, t - 6), (x0 + lado * 6, t + 2)], "laranja", 0.75 if lado > 0 else 0.5)
            s.poly([(x0 + lado * 1, t + 1), (x0 + lado * 1.5, t - 3), (x0 + lado * 4, t + 1)], "vermelho", 0.8)
    elif skin == "sapo":
        for x0 in (L + 1, R - 1):
            s.esfera(x0, t - 2, 4, 3.6, "verde")
            s.esfera(x0, t - 2, 2.4, 2.2, "creme", luz=0.4)
            s.ret(x0, t - 2, 1, 2, "preto")
    elif skin == "cyberpunk":
        s.linha([(cx, t), (cx, t - 7)], "cinza_claro", "metal")
        s.esfera(cx, t - 8, 1.8, 1.8, "ciano")
        s.caixa(L - 2, t + 4, L + 1, t + 10, "metal", raio=1)
        s.caixa(R - 1, t + 4, R + 2, t + 10, "metal", raio=1)
    elif skin == "satoshi":  # o capuz misterioso do criador
        s.esfera(cx, t + 1, w * 0.9, 4, "escuro", clip=lambda x, y: y < t + 1.5)
        s.ret(cx - 1, t - 3, 3, 1, "amarelo", "ouro")


def desenhar(moeda, skin, linha, frame, extra=None):
    """Renderiza um frame. linha: garimpando/moon/rekt/pulo."""
    estado = "garimpando" if linha == "pulo" else linha
    sx, sy, dy = (PULO if linha == "pulo" else IDLE)[frame]
    if linha == "rekt":
        sx, sy, dy = 1.0, 1.0, 0.0  # túmulo não respira (né?)
    s = Sprite(sx, sy, 0, dy)
    if linha == "pulo":
        s.pulo = True
    fn = extra or PERSONAGENS[moeda]
    fn(s, estado, frame if linha != "pulo" else 0, None)
    if linha == "pulo":
        # carinha feliz por cima no pulo + coraçõezinhos
        faiscas(s, [(6, 18 - frame * 3), (42, 14 - frame * 3)], ("vinho", "laranja"))
    if skin in ("gato", "sapo", "cyberpunk", "satoshi"):
        acessorio(s, skin)
    img = s.finalizar()
    if skin == "cyberpunk":
        img = _glow(_remap_lum(img, NEON, contorno="#0d0d1a"), "#41a6f6", "#29366f")
    elif skin == "gato":
        img = _tingir(img, "#ef7d57", 0.22)
    elif skin == "sapo":
        img = _tingir(img, "#38b764", 0.35)
    elif skin == "satoshi":
        img = _glow(_remap_lum(img, DOURADO), "#ffcd75", "#b13e53")
    return img


def sheet(moeda, skin):
    s = Image.new("RGBA", (W * FRAMES, W * len(LINHAS)), (0, 0, 0, 0))
    for j, linha in enumerate(LINHAS):
        for f in range(FRAMES):
            s.paste(desenhar(moeda, skin, linha, f), (f * W, j * W))
    return s


def contato(sheets, escala=3, fundo=(34, 32, 52, 255)):
    """Contact sheet: cada folha vira uma linha (16 frames lado a lado)."""
    larg = W * FRAMES * len(LINHAS) * escala
    img = Image.new("RGBA", (larg, W * escala * len(sheets)), fundo)
    for i, sh in enumerate(sheets):
        for j in range(len(LINHAS)):
            faixa = sh.crop((0, j * W, W * FRAMES, (j + 1) * W)).resize((W * FRAMES * escala, W * escala), Image.NEAREST)
            img.alpha_composite(faixa, (j * W * FRAMES * escala, i * W * escala))
    return img


def gif_demo(moeda, skin, destino, escala=4):
    sh = sheet(moeda, skin)
    frames = []
    for j, linha in enumerate(LINHAS):
        for rep in range(3 if linha != "pulo" else 2):
            for f in range(FRAMES):
                fr = Image.new("RGBA", (W, W), (34, 32, 52, 255))
                fr.alpha_composite(sh.crop((f * W, j * W, (f + 1) * W, (j + 1) * W)))
                frames.append(fr.resize((W * escala, W * escala), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
    frames[0].save(destino, save_all=True, append_images=frames[1:], duration=160, loop=0, disposal=2)


def gerar_tudo(preview=None, gifs=None):
    PASTA.mkdir(parents=True, exist_ok=True)
    sheets = []
    for m in PERSONAGENS:
        for sk in SKINS:
            sh = sheet(m, sk)
            sh.save(PASTA / f"{m}_{sk}.png")
            sheets.append(sh)
    icone = desenhar("BTC", "padrao", "garimpando", 0)
    icone.save(ASSETS / "icone.png")
    icone.resize((256, 256), Image.NEAREST).save(ASSETS / "icone.ico")
    if preview:
        contato(sheets).save(preview)
    if gifs:
        Path(gifs).mkdir(parents=True, exist_ok=True)
        for m in PERSONAGENS:
            gif_demo(m, "padrao", Path(gifs) / f"{m.lower()}.gif")
        gif_demo("ETH", "cyberpunk", Path(gifs) / "eth_cyberpunk.gif")
    return len(sheets)


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[2]
    n = gerar_tudo(raiz / "docs" / "sprites_preview.png", raiz / "docs" / "demo")
    print("Folhas geradas:", n)
