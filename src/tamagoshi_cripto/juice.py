"""juice.py - o tempero: chapéus de época, paleta dia/noite, partículas e tremidinha.

Tudo em PIL/Canvas puro, pixel a pixel, na grade de 48x48 (o chapéu é desenhado ANTES de ampliar,
então fica no mesmo pixel do bicho - nada de pixel torto).
"""
import datetime as dt
import random

from .pixel import rgb


# ---------------- chapéus de época ----------------
def chapeu_do_dia(hoje=None):
    d = hoje or dt.date.today()
    if (d.month == 10 and d.day >= 1) or (d.month == 11 and d.day <= 2):
        return "halloween"
    if d.month == 12 and d.day <= 26:
        return "natal"
    return None


def _topo_cabeca(fr, min_larg=10):
    """(cx, y_topo) da primeira linha 'larga' do sprite (ignora antena, raio de sol, picareta)."""
    a = fr.getchannel("A")
    for y in range(48):
        xs = [x for x in range(48) if a.getpixel((x, y))]
        if not xs:
            continue
        # maior trecho contínuo da linha
        melhor, ini = (0, 0, 0), xs[0]
        for i in range(1, len(xs) + 1):
            if i == len(xs) or xs[i] != xs[i - 1] + 1:
                if xs[i - 1] - ini + 1 > melhor[0]:
                    melhor = (xs[i - 1] - ini + 1, ini, xs[i - 1])
                if i < len(xs):
                    ini = xs[i]
        if melhor[0] >= min_larg or (len(xs) >= min_larg and xs[-1] - xs[0] < 30):
            # centro = meio do contorno das 6 linhas seguintes (olhos do sapo, orelhas do doge)
            faixa = [x for yy in range(y, min(48, y + 6)) for x in range(48) if a.getpixel((x, yy))]
            cx = (min(faixa) + max(faixa)) // 2
            # topo de verdade na coluna central (cabeça entre as orelhas fica mais baixa)
            for yy in range(y, 48):
                if any(a.getpixel((x, yy)) for x in range(max(0, cx - 3), min(48, cx + 4))):
                    return cx, yy
            return cx, y
    return 24, 10


BRUXA = [  # 1 contorno, 2 roxo, 3 roxo claro, 4 faixa laranja, 5 fivela amarela
    "........11........",
    ".......1221.......",
    "......12231.......",
    ".....122231.......",
    ".....1222231......",
    "....12222231......",
    "....122222231.....",
    "...1222222231.....",
    "...14444444441....",
    "..1444455444441...",
    ".1122222222222211.",
    "111111111111111111",
]
NOEL = [
    "..............111.",
    "..........1111555.",
    "........11222215551",
    "......112222221551.",
    ".....12222222221...",
    "....1222222222221..",
    "...122222222222221.",
    "..12222222222222221",
    ".155555555555555551",
    ".155555555555555551",
    "..1111111111111111.",
]
CORES_CHAPEU = {
    "halloween": {"1": "preto", "2": "roxo", "3": "vinho", "4": "laranja", "5": "amarelo"},
    "natal": {"1": "preto", "2": "vinho", "3": "laranja", "5": "branco"},
}


def aplicar_chapeu(fr, tipo):
    """fr: frame RGBA 48x48 (cópia é devolvida)."""
    if tipo not in CORES_CHAPEU:
        return fr
    arte = BRUXA if tipo == "halloween" else NOEL
    cores = CORES_CHAPEU[tipo]
    out = fr.copy()
    cx, topo = _topo_cabeca(fr)
    w, h = max(len(l) for l in arte), len(arte)
    x0 = cx - w // 2
    # v1.5: perfil do topo embaixo da aba. Cabeça com "vale" (olhos do sapo, orelhas do doge): o chapéu
    # apoia nos picos em vez de afundar entre eles (antes cobria os olhos do Pepe). A ponta pode sair
    # do quadro, mas a aba nunca desce pra cara.
    al = fr.getchannel("A")
    tops = [next((y for y in range(48) if al.getpixel((x, y))), 48) for x in range(max(0, x0 + 1), min(48, x0 + w - 1))]
    pico = min(tops) if tops else topo
    y0 = max(-3, pico - h + 2 if topo - pico >= 3 else topo - h + 4)  # no máx. 3px da ponta saem do quadro
    px = out.load()
    for j, linha in enumerate(arte):
        for i, ch in enumerate(linha):
            if ch in cores:
                X, Y = x0 + i, y0 + j
                if 0 <= X < 48 and 0 <= Y < 48:
                    px[X, Y] = rgb(cores[ch]) + (255,)
    return out


# ---------------- dia / noite ----------------
PERIODOS = {
    #            painel,    painel2,  sombra,   destaque, ícone
    "manha":     ("#2b2f5a", "#41508a", "#1b1d3a", "#ffcd75", "sol"),
    "tarde":     ("#3d2848", "#6a3e5d", "#241628", "#ef7d57", "sol"),
    "noite":     ("#29213f", "#3e3466", "#1d1730", "#73eff7", "lua"),
    "madrugada": ("#161a2c", "#262d4a", "#0d0f1a", "#94b0c2", "lua"),
}
ALTO_CONTRASTE = ("#000000", "#ffffff", "#000000", "#ffff00", "sol")


def periodo(hora=None):
    h = dt.datetime.now().hour if hora is None else hora
    return "madrugada" if h < 5 else "manha" if h < 12 else "tarde" if h < 18 else "noite"


def desenhar_icone_ceu(cv, x, y, tipo, frame, E=2):
    """Solzinho ou lua minguante 7x7 'pixels' no canto do painel."""
    if tipo == "sol":
        cor, raio = "#ffcd75", ["..1.1..", ".11111.", "1111111", ".11111.", "1111111", ".11111.", "..1.1.."]
    else:
        cor, raio = "#f4f4f4", ["..111..", ".11....", "111....", "111....", "111....", ".11....", "..111.."]
    for j, l in enumerate(raio):
        for i, ch in enumerate(l):
            if ch == "1":
                cv.create_rectangle(x + i * E, y + j * E, x + (i + 1) * E, y + (j + 1) * E, fill=cor, width=0)
    if tipo == "lua" and frame % 2 == 0:  # estrelinha piscando
        cv.create_rectangle(x + 10 * E, y, x + 11 * E, y + E, fill="#73eff7", width=0)


# ---------------- partículas + tremor ----------------
class Particulas:
    MAX = 60

    def __init__(self, semente=None):
        self.p = []
        self.tremor = 0
        self.rnd = random.Random(semente)

    def emitir(self, tipo, cx, cy, E=3):
        r = self.rnd
        if tipo == "moon":  # moedinhas douradas e estrelas subindo
            for _ in range(18):
                self.p.append([cx + r.randint(-30, 30), cy + r.randint(-10, 20), r.uniform(-2, 2), r.uniform(-7, -3),
                               r.choice(("#ffcd75", "#ffcd75", "#f4f4f4", "#a7f070")), r.randint(8, 14), E * 2, .35])
            self.tremor = 5
        elif tipo == "rekt":  # cacos vermelhos caindo + tremor forte
            for _ in range(22):
                self.p.append([cx + r.randint(-35, 35), cy - r.randint(10, 40), r.uniform(-3, 3), r.uniform(-2, 1),
                               r.choice(("#b13e53", "#b13e53", "#5d275d", "#566c86")), r.randint(8, 14), E * 2, .9])
            self.tremor = 9
        elif tipo == "sats":
            for _ in range(8):
                self.p.append([cx, cy, r.uniform(-4, 4), r.uniform(-5, -1), "#ffcd75", 6, E, .6])
        self.p = self.p[-self.MAX:]

    def tick(self):
        vivos = []
        for q in self.p:
            q[0] += q[2]
            q[1] += q[3]
            q[3] += q[7]
            q[5] -= 1
            if q[5] > 0:
                vivos.append(q)
        self.p = vivos
        if self.tremor:
            self.tremor -= 1

    def deslocamento(self):
        return (self.rnd.randint(-self.tremor, self.tremor) // 2, self.rnd.randint(-self.tremor, self.tremor) // 3) \
            if self.tremor else (0, 0)

    def desenhar(self, cv):
        for x, y, _, _, cor, vida, tam, _ in self.p:
            t = tam if vida > 3 else max(1, tam // 2)
            cv.create_rectangle(int(x), int(y), int(x) + t, int(y) + t, fill=cor, width=0)

    @property
    def ativo(self):
        return bool(self.p or self.tremor)
