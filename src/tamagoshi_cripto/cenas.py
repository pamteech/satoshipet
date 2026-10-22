"""cenas.py - telas que tomam o widget inteiro: onboarding (ovo chocando) e o mini-game "Pega os Sats".

Cada cena recebe o app (pra usar _txt/_moldura/cv/cfg) e expõe:
  desenhar()  tecla(e)  clique(x, y)  tick() -> bool (False = acabou)
"""
import random
import re

from PIL import Image

from . import arts, config, recursos
from .sprites import nome_folha

MOEDAS = ["BTC", "ETH", "SOL", "DOGE", "PEPE"]
TINTA, PAPEL = "#1a1c2c", "#f4f4f4"


def _frame_png(moeda, estagio, linha, f, escala):
    sh = Image.open(recursos.ASSETS / "sprites" / nome_folha(moeda, "padrao", estagio)).convert("RGBA")
    j = {"garimpando": 0, "moon": 1, "rekt": 2, "pulo": 3}[linha]
    return sh.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48)).resize((48 * escala, 48 * escala), Image.NEAREST)


class _Cena:
    def __init__(self, app):
        self.app, self.t = app, 0
        self.imgs = {}

    def img(self, chave, fabrica):
        if chave not in self.imgs:
            from .main import _png_para_tk
            self.imgs[chave] = _png_para_tk(fabrica())
        return self.imgs[chave]

    def botao(self, x0, y0, x1, y1, texto, fundo="#38b764", ativo=True, tag=None):
        a = self.app
        a._moldura(x0, y0, x1, y1, fundo if ativo else "#566c86", luz="#a7f070" if ativo else None,
                   sombra="#257179" if ativo else None, tags=(tag,) if tag else ())
        a._txt((x0 + x1) // 2, (y0 + y1) // 2 + 1, texto, TINTA if ativo else "#333c57", tags=(tag,) if tag else ())
        self.alvos.append((x0, y0, x1, y1, tag))

    def clique(self, x, y):
        for x0, y0, x1, y1, tag in reversed(getattr(self, "alvos", [])):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return self.acao(tag)
        return None

    def acao(self, tag):
        pass


# ======================= ONBOARDING =======================
class Onboarding(_Cena):
    PASSOS = ("ovo", "moeda", "nome", "dicas", "optins", "fim")

    def __init__(self, app):
        super().__init__(app)
        self.passo = "ovo"
        self.sel = 0
        self.nome = ""
        self.som = not app.cfg.get("mudo")
        self.rank = bool(app.cfg.get("ranking"))
        self.acabou = False
        self.alvos = []
        self.p_ovo = 0  # ticks dentro do passo ovo

    # ---- navegação ----
    def proximo(self):
        i = self.PASSOS.index(self.passo)
        self.passo = self.PASSOS[min(i + 1, len(self.PASSOS) - 1)]
        if self.passo == "fim":
            self.concluir()

    def pular(self):
        self.concluir(pulou=True)

    def concluir(self, pulou=False):
        a, cfg = self.app, self.app.cfg
        if not pulou:
            m = MOEDAS[self.sel]
            if m == "BTC" or a.pro:
                cfg["moeda"] = m
            nome = self.nome.strip()
            cfg["nome_pet"] = nome
            cfg["mudo"] = not self.som
            a.som.mudo = cfg["mudo"]
            if self.rank and cfg.get("ranking_url"):
                nick = re.sub(r"[^A-Za-z0-9_\-]", "_", nome or "anon")[:16]
                cfg.update({"ranking": True, "nick": nick if len(nick) >= 3 else nick + "_pet"})
        cfg["onboarding_ok"] = True
        config.salvar(cfg)
        a.cache_sprites.clear()
        self.acabou = True
        a.som.tocar("conquista" if not pulou else "clique")

    def tecla(self, e):
        k = e.keysym
        if k == "Escape":
            return self.pular()
        if self.passo == "ovo":
            if k in ("Return", "space"):
                self.p_ovo = max(self.p_ovo, 30)
                if self.p_ovo >= 34:
                    self.proximo()
        elif self.passo == "moeda":
            if k in ("Left", "h"):
                self.sel = (self.sel - 1) % 5
            elif k in ("Right", "l"):
                self.sel = (self.sel + 1) % 5
            elif k in ("Return", "space"):
                self.proximo()
        elif self.passo == "nome":
            if k == "Return":
                self.proximo()
            elif k == "BackSpace":
                self.nome = self.nome[:-1]
            elif e.char and e.char.isprintable() and len(self.nome) < 12:
                self.nome += e.char
        elif self.passo == "optins":
            if k in ("s", "S"):
                self.som = not self.som
            elif k in ("r", "R"):
                self.rank = not self.rank
            elif k == "Return":
                self.proximo()
        elif k in ("Return", "space"):
            self.proximo()

    def acao(self, tag):
        if tag == "pular":
            return self.pular()
        if tag == "ok":
            if self.passo == "ovo" and self.p_ovo < 34:
                self.p_ovo = 34
                return
            return self.proximo()
        if tag and tag.startswith("moeda"):
            self.sel = int(tag[5:])
        elif tag == "som":
            self.som = not self.som
        elif tag == "rank":
            self.rank = not self.rank

    def tick(self):
        self.t += 1
        if self.passo == "ovo":
            self.p_ovo += 1
            if self.p_ovo == 30:
                self.app.som.tocar("eclodir")
                self.app.juice.emitir("moon", self.app.LARG // 2, self.app.Y_SPRITE + self.app.S // 2, self.app.escala)
        return not self.acabou

    # ---- desenho ----
    def desenhar(self):
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#1d1730", borda=TINTA, luz="#3e3466", sombra="#0d0f1a")
        # estrelas do fundo
        rnd = random.Random(42)
        for i in range(26):
            x, y = rnd.randint(10, L - 10), rnd.randint(10, H - 60)
            if (i + self.t // 2) % 7:
                c.create_rectangle(x, y, x + 2, y + 2, fill="#566c86" if i % 3 else PAPEL, width=0)
        getattr(self, "_" + self.passo, lambda: None)()
        self.botao(L - 74, 8, L - 10, 30, "PULAR", fundo="#94b0c2", tag="pular")
        # bolinhas de progresso
        n = self.PASSOS.index(self.passo)
        for i in range(5):
            x = L // 2 - 40 + i * 20
            c.create_rectangle(x, H - 16, x + 8, H - 10, fill="#ffcd75" if i <= n else "#333c57", width=0)

    def _titulo(self, y, texto, cor="#ffcd75"):
        self.app._txt(self.app.LARG // 2, y, texto, cor, sombra=TINTA, max_chars=(self.app.LARG - 20) // 8)

    def _ovo(self):
        a, L, E = self.app, self.app.LARG, self.app.escala
        cy = 46 + a.S // 2
        p = self.p_ovo
        if p < 30:  # balançando cada vez mais, com trincas aparecendo
            amp = min(6, 1 + p // 5)
            dx = (amp if (p // 2) % 2 else -amp) if p > 6 else 0
            img = self.img(("ovo", p % 4), lambda: _frame_png("BTC", "ovo", "garimpando", p % 4, E))
            a.cv.create_image(L // 2 + dx, cy, image=img)
            trincas = [(0, -8, 3, -4), (3, -4, -1, 0), (-1, 0, 4, 4), (-6, -2, -2, 2), (-2, 2, -5, 6)]
            for k, (x0, y0, x1, y1) in enumerate(trincas[:max(0, (p - 8) // 4)]):
                a.cv.create_line(L // 2 + dx + x0 * E, cy + y0 * E, L // 2 + dx + x1 * E, cy + y1 * E,
                                 fill=TINTA, width=E)
            self._titulo(a.Y_SPRITE + a.S + 26, "...?" if p < 15 else "TEM ALGUÉM AÍ DENTRO!")
        else:  # flash e o bebê aparece
            if p < 33:
                a.cv.create_rectangle(4, 4, L - 4, a.ALT - 4, fill=PAPEL, width=0)
            img = self.img(("bebe", self.t % 4), lambda: _frame_png("BTC", "bebe", "pulo", self.t % 4, E))
            a.cv.create_image(L // 2, cy, image=img)
            self._titulo(a.Y_SPRITE + a.S + 20, "NASCEU! gm, fren!", "#a7f070")
            a.juice.desenhar(a.cv)
            self.botao(L // 2 - 60, a.ALT - 60, L // 2 + 60, a.ALT - 32, "VAMOS!", tag="ok")

    def _moeda(self):
        a, L = self.app, self.app.LARG
        self._titulo(48, "ESCOLHA SUA MOEDA")
        passo = (L - 20) // 5
        for i, m in enumerate(MOEDAS):
            x = 10 + i * passo + passo // 2
            sel = i == self.sel
            if sel:
                a._moldura(x - passo // 2 + 2, 66, x + passo // 2 - 2, 66 + 48 * 1 + 30, "#3e3466", borda="#ffcd75")
            img = self.img(("m", m, sel, self.t % 4 if sel else 0),
                           lambda m=m, sel=sel: _frame_png(m, "bebe", "pulo" if sel else "garimpando",
                                                           self.t % 4 if sel else 0, 1))
            a.cv.create_image(x, 66 + 26, image=img)
            a._txt(x, 66 + 56, m, "#ffcd75" if sel else "#94b0c2")
            self.alvos.append((x - passo // 2, 66, x + passo // 2, 66 + 78, f"moeda{i}"))
        m = MOEDAS[self.sel]
        a._txt(L // 2, 170, arts.NOMES[m], "#f4f4f4", sombra=TINTA)
        livre = m == "BTC" or a.pro
        a._txt(L // 2, 188, "grátis" if livre else "Pro na janela (grátis no --tui)",
               "#a7f070" if livre else "#ef7d57", max_chars=(L - 20) // 8)
        a._txt(L // 2, 210, "< > escolhe - ENTER confirma", "#566c86")
        self.botao(L // 2 - 60, a.ALT - 60, L // 2 + 60, a.ALT - 32, "ESSA!" if livre else "USAR BTC", tag="ok")

    def _nome(self):
        a, L = self.app, self.app.LARG
        self._titulo(48, "QUAL O NOME DELE?")
        m = MOEDAS[self.sel] if (MOEDAS[self.sel] == "BTC" or a.pro) else "BTC"
        img = self.img(("n", m, self.t % 4), lambda: _frame_png(m, "bebe", "garimpando", self.t % 4, 2))
        a.cv.create_image(L // 2, 120, image=img)
        a._moldura(20, 172, L - 20, 200, "#0b0f14", borda="#38b764")
        cursor = "_" if self.t % 4 < 2 else " "
        a._txt(L // 2, 187, (self.nome or "") + cursor if self.nome else cursor + " ", "#a7f070")
        a._txt(L // 2, 214, f"vazio = {arts.NOMES[m]}", "#566c86")
        a._txt(L // 2, 230, "ENTER confirma", "#566c86")
        self.botao(L // 2 - 60, a.ALT - 60, L // 2 + 60, a.ALT - 32, "BATIZAR", tag="ok")

    def _dicas(self):
        a, L = self.app, self.app.LARG
        self._titulo(48, "DICAS RÁPIDAS")
        dicas = [("CLIQUE", "carinho (+XP)", "#ef7d57"), ("CRASE `", "console hacker", "#a7f070"),
                 ("BOTÃO DIR.", "menu de tudo", "#73eff7"), ("P", "mini-game: pega sats", "#ffcd75"),
                 ("h j k l", "move o widget", "#94b0c2")]
        for i, (k, d, cor) in enumerate(dicas):
            y = 74 + i * 34
            a._moldura(14, y, 108, y + 26, "#333c57", luz="#566c86")
            a._txt(61, y + 13, k, cor)
            a._txt(118, y + 13, d, "#f4f4f4", anchor="w", max_chars=(L - 130) // 8)
        self.botao(L // 2 - 60, a.ALT - 60, L // 2 + 60, a.ALT - 32, "ENTENDI", tag="ok")

    def _optins(self):
        a, L = self.app, self.app.LARG
        self._titulo(48, "SUAS ESCOLHAS")
        tem_rank = bool(a.cfg.get("ranking_url"))
        for i, (tag, rot, val, desc) in enumerate([
                ("som", "SONS 8-BIT", self.som, "jingles chiptune (S)"),
                ("rank", "RANKING", self.rank and tem_rank,
                 "apelido + stats, anônimo (R)" if tem_rank else "sem servidor (ver config)")]):
            y = 80 + i * 62
            a._moldura(14, y, L - 14, y + 50, "#333c57", luz="#566c86")
            a._moldura(24, y + 12, 50, y + 38, "#a7f070" if val else "#1a1c2c", borda="#f4f4f4")
            if val:
                a._txt(37, y + 25, "x", TINTA)
            a._txt(62, y + 18, rot, "#ffcd75", anchor="w")
            a._txt(62, y + 34, desc, "#94b0c2", anchor="w", max_chars=(L - 80) // 8)
            self.alvos.append((14, y, L - 14, y + 50, tag))
        a._txt(L // 2, 218, "tudo opcional, muda depois no menu", "#566c86", max_chars=(L - 20) // 8)
        self.botao(L // 2 - 60, a.ALT - 60, L // 2 + 60, a.ALT - 32, "COMEÇAR!", tag="ok")


# ======================= MINI-GAME =======================
class PegaSats(_Cena):
    """20 s: ← → (ou h/l, ou mouse) pra pegar sats caindo. FUD vermelho tira ponto. XP = 3 por sat."""
    DURACAO = 20.0
    DT = 0.05  # 50 ms por tick (só enquanto o jogo roda)

    def __init__(self, app, semente=None):
        super().__init__(app)
        self.rnd = random.Random(semente)
        self.x = app.LARG // 2
        self.vx = 0
        self.itens = []  # [x, y, vy, tipo]
        self.pontos = 0
        self.pegos = 0
        self.tempo = self.DURACAO
        self.fim = None
        self.alvos = []
        self.chao = app.ALT - 70

    def tecla(self, e):
        k = e.keysym
        if self.fim is not None:
            if k in ("Return", "space", "Escape"):
                self.fim = -1
            return
        if k == "Escape":
            self.tempo = 0
        elif k in ("Left", "h", "a"):
            self.x -= 18
        elif k in ("Right", "l", "d"):
            self.x += 18
        self.x = max(24, min(self.app.LARG - 24, self.x))

    def mouse(self, x):
        self.x = max(24, min(self.app.LARG - 24, x))

    def acao(self, tag):
        if tag == "ok":
            self.fim = -1

    def tick(self):
        self.t += 1
        if self.fim is not None:
            if self.fim == -1:
                return False
            self.fim += 1
            return True
        self.tempo -= self.DT
        dific = 1 + (self.DURACAO - self.tempo) / 10
        if self.rnd.random() < 0.09 * dific:
            tipo = "fud" if self.rnd.random() < 0.2 else "sat"
            self.itens.append([self.rnd.randint(16, self.app.LARG - 16), 40, self.rnd.uniform(3, 5) * dific, tipo])
        vivos = []
        for it in self.itens:
            it[1] += it[2]
            if it[1] >= self.chao - 20 and abs(it[0] - self.x) < 26:
                if it[3] == "sat":
                    self.pontos += 1
                    self.pegos += 1
                    self.app.som.tocar("pegou")
                    self.app.juice.emitir("sats", it[0], it[1], 2)
                else:
                    self.pontos = max(0, self.pontos - 2)
                    self.app.som.tocar("errou")
                    self.app.juice.tremor = 4
                continue
            if it[1] < self.app.ALT - 40:
                vivos.append(it)
        self.itens = vivos
        if self.tempo <= 0:
            self.fim = 0
            self.app.som.tocar("fim_jogo")
            self.app.fim_minigame(self.pontos, self.pegos)
        return True

    @property
    def xp(self):
        return min(90, self.pontos * 3)

    def desenhar(self):
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#1d1730", borda=TINTA, luz="#3e3466")
        a._txt(12, 12, f"SATS {self.pontos}", "#ffcd75", anchor="nw", sombra=TINTA)
        a._txt(L - 12, 12, f"{max(0, self.tempo):04.1f}s", "#73eff7", anchor="ne", sombra=TINTA)
        # barra de tempo
        c.create_rectangle(12, 26, L - 12, 30, fill="#333c57", width=0)
        c.create_rectangle(12, 26, 12 + int((L - 24) * max(0, self.tempo) / self.DURACAO), 30, fill="#38b764", width=0)
        for x, y, _, tipo in self.itens:
            x, y = int(x), int(y)
            if tipo == "sat":  # moedinha laranja 8x8 com S
                c.create_rectangle(x - 7, y - 5, x + 7, y + 5, fill=TINTA, width=0)
                c.create_rectangle(x - 5, y - 7, x + 5, y + 7, fill=TINTA, width=0)
                c.create_rectangle(x - 5, y - 5, x + 5, y + 5, fill="#ef7d57", width=0)
                c.create_rectangle(x - 5, y - 5, x + 3, y - 3, fill="#ffcd75", width=0)
                a._txt(x, y + 1, "S", PAPEL)
            else:  # FUD: bloco vermelho
                c.create_rectangle(x - 12, y - 7, x + 12, y + 7, fill=TINTA, width=0)
                c.create_rectangle(x - 10, y - 5, x + 10, y + 5, fill="#b13e53", width=0)
                a._txt(x, y + 1, "FUD", PAPEL)
        # chão de blocos
        for bx in range(4, L - 4, 24):
            a._moldura(bx, self.chao + 26, bx + 22, self.chao + 40, "#ef7d57", luz="#ffcd75")
        frames = a._sprites_mini()
        img = frames[("pulo" if self.juice_pulo() else "moon", self.t // 3 % 4)]
        c.create_image(self.x, self.chao, image=img)
        a.juice.desenhar(c)
        a._txt(L // 2, H - 16, "< > pega sats - evita FUD", "#566c86")
        if self.fim is not None:
            a._moldura(20, 80, L - 20, 200, "#ffcd75", luz="#fff4c0", sombra="#ef7d57")
            a._txt(L // 2, 100, "FIM DE JOGO!", "#b13e53")
            a._txt(L // 2, 124, f"{self.pegos} sats pegos", TINTA)
            a._txt(L // 2, 144, f"+{self.xp} XP", "#257179", escala=2)
            self.botao(L // 2 - 50, 166, L // 2 + 50, 192, "BELEZA", tag="ok")

    def juice_pulo(self):
        return bool(self.app.juice.p)


# ======================= v1.4: GENES, CEMITÉRIO, CRUZAMENTO, BATALHA =======================
def _frame_genes(moeda, estagio, linha, f, escala, genes=None, fantasma=False, espelhar=False):
    from . import genetica
    fr = _frame_png(moeda, estagio, linha, f, 1)
    fr = genetica.fantasma(fr) if fantasma else genetica.aplicar(fr, genes)
    if espelhar:
        fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
    return fr.resize((48 * escala, 48 * escala), Image.NEAREST)


def _lapide_png(escala=2):
    """Lápide 24x28 em pixel art (pedra cinza, RIP, gramadinho)."""
    arte = ["......11111111......",
            "....112222222211....",
            "...12222222222221...",
            "..1223333333333221..",
            "..1222222222222221..",
            ".122444242444222221.",
            ".122424242424222221.",
            ".122442242444222221.",
            ".122424242422222221.",
            ".122424242422222221.",
            ".122222222222222221.",
            ".122222225522222221.",
            ".122222555555222221.",
            ".122222225522222221.",
            ".122222225522222221.",
            ".122222225522222221.",
            ".122222222222222221.",
            ".122222222222222221.",
            "1111111111111111111.",
            "6676767766767767767.",
            ]
    cores = {"1": (26, 28, 44), "2": (148, 176, 194), "3": (244, 244, 244), "4": (51, 60, 87),
             "5": (86, 108, 134), "6": (56, 183, 100), "7": (167, 240, 112)}
    im = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    for y, l in enumerate(arte):
        for x, ch in enumerate(l):
            if ch in cores:
                im.putpixel((x, y), cores[ch] + (255,))
    return im.resize((20 * escala, 20 * escala), Image.NEAREST)


class Cemiterio(_Cena):
    """Cemitério de Honra: uma lápide por página, com epitáfio e stats. < > navega, ESC sai."""

    def __init__(self, app):
        super().__init__(app)
        self.i = max(0, len(app.cfg.get("cemiterio", [])) - 1)
        self.acabou = False
        self.alvos = []

    def tecla(self, e):
        n = len(self.app.cfg.get("cemiterio", []))
        if e.keysym in ("Left", "h"):
            self.i = max(0, self.i - 1)
        elif e.keysym in ("Right", "l"):
            self.i = min(max(0, n - 1), self.i + 1)
        elif e.keysym in ("Escape", "Return", "q"):
            self.acabou = True

    def acao(self, tag):
        if tag == "sair":
            self.acabou = True
        elif tag == "ant":
            self.i = max(0, self.i - 1)
        elif tag == "prox":
            self.i = min(len(self.app.cfg.get("cemiterio", [])) - 1, self.i + 1)
        elif tag == "renascer":
            self.app.renascer()
            self.acabou = True

    def tick(self):
        self.t += 1
        return not self.acabou

    def desenhar(self):
        import time as _t
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#1d1730", borda=TINTA, luz="#333c57", sombra="#0d0f1a")
        # lua e névoa
        for k, (dx, w) in enumerate(((4, 6), (2, 10), (0, 14), (0, 14), (0, 14), (2, 10), (4, 6))):  # lua minguante
            y = 38 + k * 3
            c.create_rectangle(L - 34 + dx, y, L - 34 + dx + w, y + 3, fill="#f4f4f4", width=0)
            c.create_rectangle(L - 28 + dx, y, L - 28 + dx + w, y + 3, fill="#1d1730", width=0)
        a._txt(L // 2, 18, "CEMITÉRIO DE HONRA", "#94b0c2", sombra=TINTA)
        lista = a.cfg.get("cemiterio", [])
        if not lista:
            a._txt(L // 2, H // 2 - 20, "ninguém morreu (ainda)", "#f4f4f4", sombra=TINTA)
            a._txt(L // 2, H // 2 + 4, "modo hardcore: " + ("LIGADO" if a.cfg.get("hardcore") else "desligado"),
                   "#b13e53" if a.cfg.get("hardcore") else "#566c86")
        else:
            r = lista[self.i]
            lap = self.img(("lap", 3), lambda: _lapide_png(3))
            c.create_image(L // 2, 72, image=lap)
            fant = self.img(("fant", r.get("moeda"), self.t // 4 % 4), lambda: _frame_genes(
                r.get("moeda", "BTC"), "adulto", "garimpando", self.t // 4 % 4, 1, fantasma=True))
            c.create_image(L // 2 + 56, 52 - (self.t // 3) % 3 * 2, image=fant)
            a._txt(L // 2, 116, r["nome"], "#ffcd75", escala=2, sombra=TINTA)
            data = lambda ts: _t.strftime("%d/%m/%y", _t.localtime(ts))
            a._txt(L // 2, 136, f"{data(r['nasceu'])} - {data(r['morreu'])}", "#94b0c2")
            a._txt(L // 2, 158, '"' + r["epitafio"] + '"', "#f4f4f4", max_chars=(L - 24) // 8, sombra=TINTA)
            y = 186
            for k, v in (("estágio", f"{r['estagio']} LV{r['nivel']}"),
                         ("blocos/crashes", f"{r['blocos']}/{r['crashes']}"), ("viveu", f"{r['dias']} dias"),
                         ("DNA", (r.get("genes") or {}).get("paleta", "?"))):
                a._txt(30, y, k, "#566c86", anchor="w")
                a._txt(L - 30, y, str(v), "#f4f4f4", anchor="e")
                y += 13
            a._txt(L // 2, 30, f"{self.i + 1}/{len(lista)}", "#566c86")
            if self.i > 0:
                self.botao(10, 60, 38, 84, "<", fundo="#94b0c2", tag="ant")
            if self.i < len(lista) - 1:
                self.botao(L - 38, 60, L - 10, 84, ">", fundo="#94b0c2", tag="prox")
        if a.cfg.get("fantasma"):
            self.botao(20, H - 70, L - 20, H - 44, "RENASCER DO OVO", fundo="#ffcd75", tag="renascer")
        self.botao(L // 2 - 40, H - 38, L // 2 + 40, H - 12, "SAIR", fundo="#94b0c2", tag="sair")


class Cruzamento(_Cena):
    """Mostra pai + mãe -> ovo chocando -> filhote com genes (e mutações destacadas)."""

    def __init__(self, app, pai, mae, filho, mutou):
        super().__init__(app)
        self.pai, self.mae, self.filho, self.mutou = pai, mae, filho, mutou
        self.acabou = False
        self.alvos = []

    def tecla(self, e):
        if e.keysym in ("Escape", "Return", "space"):
            self.acabou = True

    def acao(self, tag):
        if tag == "ok":
            self.acabou = True

    def tick(self):
        self.t += 1
        if self.t == 14:
            self.app.som.tocar("eclodir")
            self.app.juice.emitir("moon", self.app.LARG // 2, 230, 2)
        return not self.acabou

    def desenhar(self):
        from . import genetica
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#1d1730", borda=TINTA, luz="#3e3466", sombra="#0d0f1a")
        a._txt(L // 2, 18, "LABORATÓRIO DE DNA", "#a7f070", sombra=TINTA)
        for i, p in enumerate((self.pai, self.mae)):
            g = p["genes"]
            x = L // 4 + i * L // 2
            im = self.img(("p", i, self.t // 3 % 4), lambda g=g, i=i: _frame_genes(
                g.get("moeda", "BTC"), p.get("estagio", "adulto") if p.get("estagio") != "ovo" else "adulto",
                "garimpando", self.t // 3 % 4, 1, g, espelhar=i == 1))
            c.create_image(x, 54, image=im)
            a._txt(x, 86, p.get("nome", "?")[:10], "#f4f4f4", sombra=TINTA)
        a._txt(L // 2, 54, "+", "#b13e53", escala=2, sombra=TINTA)
        g = self.filho
        if self.t < 14:  # ovo balançando
            off = (-3, 0, 3, 0)[self.t % 4]
            ovo = self.img(("ovo", self.t % 4), lambda: _frame_genes(g["moeda"], "ovo", "garimpando", 0, 2, g))
            c.create_image(L // 2 + off, 146, image=ovo)
            a._txt(L // 2, 206, "chocando" + "." * (self.t // 3 % 4), "#ffcd75")
        else:
            bebe = self.img(("bebe", self.t // 3 % 4), lambda: _frame_genes(
                g["moeda"], "bebe", "pulo" if self.t < 26 else "garimpando", self.t // 3 % 4, 2, g))
            c.create_image(L // 2, 144, image=bebe)
            nome, pts = genetica.raridade(g)
            a._txt(L // 2, 200, nome.upper() + f" - geração {g.get('geracao', 1)}", genetica.COR_RARIDADE[nome],
                   sombra=TINTA)
            y = 218
            for k in genetica.GENES:
                mut = k in self.mutou
                a._txt(30, y, k, "#566c86", anchor="w")
                a._txt(L - 30, y, g[k] + (" *MUTOU*" if mut else ""), "#ffcd75" if mut else "#f4f4f4", anchor="e")
                y += 13
            self.botao(L // 2 - 50, H - 36, L // 2 + 50, H - 10, "LINDO!", tag="ok")
        a.juice.desenhar(c)


class Batalha(_Cena):
    """Batalha por turnos animada. Você escolhe o golpe (1-4 ou clique); o rival é IA."""
    BOTOES = ("PUMP", "HODL", "FUD", "ESPECIAL")

    def __init__(self, app, eu, rival, var_eu=0.0, var_rival=0.0, semente=None, auto=False):
        from . import batalha
        super().__init__(app)
        import random as _r
        self.B, self.rnd = batalha, _r.Random(semente)
        self.eu_pet, self.rival_pet = eu, rival
        self.a, self.b = batalha.Lutador(eu, var_eu), batalha.Lutador(rival, var_rival)
        self.vez = "a" if self.a.s["spd"] >= self.b.s["spd"] else "b"
        self.log = [f"{self.a.nome} VS {self.b.nome}!"]
        self.anim = 0        # frames de animação do golpe atual
        self.atacante = None
        self.dano_txt = None
        self.fim = None
        self.auto = auto     # demo/teste: IA joga pelos dois
        self.acabou = False
        self.alvos = []
        self.espera = 6

    def jogar(self, golpe):
        if self.fim or self.vez != "a" or self.anim:
            return
        if golpe == "ESPECIAL":
            golpe = self.a.s["especial"]
        self._executar(self.a, self.b, golpe)

    def _executar(self, at, df, golpe):
        at.defendendo = False
        hp = df.hp
        dano, txt = self.B._golpe(at, df, golpe, self.rnd)
        if at.fud and golpe != "FUD":
            at.fud = max(0, at.fud - 1)
        self.log = (self.log + [txt])[-3:]
        self.atacante, self.anim = at, 6
        self.dano_txt = f"-{hp - df.hp}" if hp > df.hp else None
        self.app.som.tocar("errou" if dano and at is self.b else "pegou" if dano else "clique")
        if dano:
            self.app.juice.tremor = 3 if df is self.a else 2
        self.vez = "b" if at is self.a else "a"
        if not df.vivo:
            self.fim = "a" if df is self.b else "b"
            self.app.fim_batalha(self.fim == "a", self.rival_pet)

    def tecla(self, e):
        if self.fim:
            if e.keysym in ("Return", "space", "Escape"):
                self.acabou = True
            return
        if e.keysym == "Escape":
            self.acabou = True
        elif e.char in "1234" and e.char:
            self.jogar(self.BOTOES[int(e.char) - 1])

    def acao(self, tag):
        if tag == "ok":
            self.acabou = True
        elif tag and tag.startswith("g:"):
            self.jogar(tag[2:])

    def tick(self):
        self.t += 1
        if self.anim:
            self.anim -= 1
        elif not self.fim:
            if self.espera:
                self.espera -= 1
            elif self.vez == "b":
                self._executar(self.b, self.a, self.B.escolher_ia(self.b, self.a, self.rnd))
                self.espera = 3
            elif self.auto:
                self._executar(self.a, self.b, self.B.escolher_ia(self.a, self.b, self.rnd))
                self.espera = 3
        return not self.acabou

    def _barra(self, x0, y, w, lut, cor):
        c = self.app.cv
        c.create_rectangle(x0, y, x0 + w, y + 10, fill=TINTA, width=0)
        c.create_rectangle(x0 + 2, y + 2, x0 + w - 2, y + 8, fill="#333c57", width=0)
        f = lut.hp / lut.s["max_hp"]
        cor = "#38b764" if f > .5 else "#ffcd75" if f > .2 else "#b13e53"
        if lut.hp:
            c.create_rectangle(x0 + 2, y + 2, x0 + 2 + int((w - 4) * f), y + 8, fill=cor, width=0)

    def desenhar(self):
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#29366f", borda=TINTA, luz="#3b5dc9", sombra="#1a1c2c")
        yl = H - 108           # topo da caixa de log
        chao = yl - 10
        # arena: chão quadriculado + plataformas
        for i, x in enumerate(range(6, L - 6, 16)):
            c.create_rectangle(x, chao - 8, x + 16, chao + 4, fill="#38b764" if i % 2 else "#257179", width=0)
        c.create_rectangle(6, chao + 4, L - 6, chao + 7, fill=TINTA, width=0)
        c.create_rectangle(L - 130, 112, L - 14, 118, fill="#257179", width=0)
        c.create_rectangle(L - 130, 118, L - 14, 121, fill=TINTA, width=0)
        # HP: rival em cima à esquerda, eu embaixo à direita (clássico)
        for lut, x, y in ((self.b, 10, 10), (self.a, L - 132, chao - 52)):
            a._txt(x, y, f"{lut.nome[:9]} LV{lut.pet.get('nivel', 1)}", "#f4f4f4", anchor="nw", sombra=TINTA)
            self._barra(x, y + 13, 122, lut, None)
            a._txt(x + 122, y + 26, f"{lut.hp}/{lut.s['max_hp']}", "#94b0c2", anchor="ne")
        for lut, x, y, esp in ((self.b, L - 72, 116 - 36, True), (self.a, 66, chao - 40, False)):
            dx = 0
            if self.anim and self.atacante is lut and self.anim > 3:
                dx = 12 if lut is self.a else -12
            apanhou = self.anim and self.atacante is not None and self.atacante is not lut and self.dano_txt
            morto = not lut.vivo
            if not (apanhou and self.anim % 2):  # pisca quando apanha
                g = lut.pet.get("genes") or {}
                est = lut.pet.get("estagio", "adulto")
                est = "adulto" if est == "ovo" else est
                linha = "rekt" if morto or lut.hp < lut.s["max_hp"] * .25 else \
                    "moon" if (self.fim and lut.vivo) else "garimpando"
                f = self.t // 3 % 4
                im = self.img((id(lut), linha, f, morto), lambda: _frame_genes(
                    g.get("moeda", "BTC"), est, linha, f, 2 if lut is self.a else 1, g, fantasma=morto,
                    espelhar=esp))
                c.create_image(x + dx, y - (self.t // 3 % 2 * 2 if morto else 0), image=im, anchor="center")
            if apanhou:
                a._txt(x + 30, y - (40 if lut is self.a else 20) - (6 - self.anim) * 3, self.dano_txt, "#b13e53", escala=2, sombra=PAPEL)
        # caixa de log
        a._moldura(6, yl, L - 6, yl + 50, PAPEL, luz="#ffffff", sombra="#94b0c2")
        for i, l in enumerate(self.log[-3:]):
            mx = (L - 24) // 8
            a._txt(12, yl + 7 + i * 13, l if len(l) <= mx else l[:mx - 2] + "..", TINTA, anchor="nw")
        if self.fim:
            ganhou = self.fim == "a"
            a._moldura(30, 40, L - 30, 150, "#ffcd75" if ganhou else "#94b0c2", luz="#fff4c0",
                       sombra="#ef7d57" if ganhou else "#566c86")
            a._txt(L // 2, 60, "VITÓRIA!" if ganhou else "DERROTA...", "#b13e53" if ganhou else TINTA, escala=2)
            a._txt(L // 2, 86, f"+{40 if ganhou else 10} XP", "#257179")
            v = a.cfg.get("batalhas", {})
            a._txt(L // 2, 102, f"recorde: {v.get('vitorias', 0)}V {v.get('derrotas', 0)}D", TINTA)
            self.botao(L // 2 - 36, 116, L // 2 + 36, 140, "OK", tag="ok")
        esp = "LASER" if self.a.s["especial"] == "LASER EYES" else "MOON"
        for i, gname in enumerate(self.BOTOES):
            w = (L - 20) // 2
            x0 = 10 + (i % 2) * w
            y0 = H - 54 + (i // 2) * 24
            rot = f"{i + 1} {esp if gname == 'ESPECIAL' else gname}"
            ativo = not self.fim and self.vez == "a" and not self.anim and \
                not (gname == "ESPECIAL" and self.a.recarga)
            self.botao(x0, y0, x0 + w - 4, y0 + 22, rot, fundo="#ef7d57" if gname == "ESPECIAL" else "#38b764",
                       ativo=ativo, tag="g:" + gname)
        a.juice.desenhar(c)


class Corretora(_Cena):
    """Paper trading: compra/vende a moeda atual com DINHEIRO FICTÍCIO. Faixa de aviso sempre visível."""
    PASSOS = (100, 1000)

    def __init__(self, app):
        super().__init__(app)
        self.acabou = False
        self.alvos = []
        self.msg = "preço real, dinheiro de mentira"

    def tecla(self, e):
        if e.keysym in ("Escape", "q"):
            self.acabou = True
        elif e.char in ("b", "c"):
            self.acao("buy:100")
        elif e.char in ("s", "v"):
            self.acao("sell:all")

    def acao(self, tag):
        a = self.app
        if tag == "sair":
            self.acabou = True
        elif tag and ":" in tag:
            lado, v = tag.split(":")
            self.msg = a.paper([lado, a.cfg["moeda"], v])[0]
            self.t = 0

    def tick(self):
        self.t += 1
        return not self.acabou

    def desenhar(self):
        from . import papel
        a, c, L, H = self.app, self.app.cv, self.app.LARG, self.app.ALT
        self.alvos = []
        c.delete("all")
        a._moldura(2, 2, L - 2, H - 2, "#1a1c2c", borda=TINTA, luz="#333c57")
        # faixa zebrada de aviso
        for i, x in enumerate(range(4, L - 4, 12)):
            c.create_rectangle(x, 6, x + 12, 26, fill="#ffcd75" if i % 2 else "#1a1c2c", width=0)
        a._moldura(30, 6, L - 30, 26, "#ffcd75", luz="#fff4c0")
        a._txt(L // 2, 17, papel.AVISO, "#b13e53")
        m = a.cfg["moeda"]
        preco = a.precos.get(m)
        r = papel.resumo(a.corretora(), a.precos)
        a._txt(L // 2, 40, "CORRETORA DE MENTIRINHA", "#94b0c2", sombra=TINTA)
        a._txt(12, 58, m, "#f4f4f4", anchor="nw", escala=2, sombra=TINTA)
        a._txt(L - 12, 62, a._fmt_preco(m, preco) if preco else "...", "#ffcd75", anchor="ne")
        a._sparkline(m, 12, 80, L - 12, 104, "#38b764" if r["pnl"] >= 0 else "#b13e53")
        # bicho reagindo ao PnL
        h = papel.humor(r["pnl_pct"]) or "garimpando"
        frames = a._sprites_mini()
        c.create_image(L - 50, 150, image=frames[(h, self.t // 3 % 4)])
        cor = "#38b764" if r["pnl"] >= 0 else "#b13e53"
        y = 116
        for k, v, cr in (("caixa", f"${r['usd']:,.2f}", "#f4f4f4"), ("total", f"${r['total']:,.2f}", "#f4f4f4"),
                         ("PnL", f"{r['pnl']:+,.2f}", cor), ("", f"{r['pnl_pct']:+.2f}%", cor)):
            a._txt(12, y, k, "#566c86", anchor="nw")
            a._txt(60, y, v, cr, anchor="nw")
            y += 14
        pos = r["pos"].get(m)
        a._txt(12, y + 2, f"{m}: {pos['qtd']:.6g}" if pos else f"sem {m}", "#73eff7", anchor="nw")
        hist = a.corretora().get("hist", [])[-3:]
        y = 196
        for x in reversed(hist):
            a._txt(12, y, f"{x['lado'][:1].upper()} {x['moeda']} ${x['usd']:,.0f}" +
                   (f" {x['lucro']:+.0f}" if "lucro" in x else ""), "#94b0c2", anchor="nw")
            y += 12
        a._txt(L // 2, H - 92, self.msg[:60], "#ffcd75", max_chars=(L - 20) // 8)
        w = (L - 24) // 3
        for i, (rot, tag, cor_b) in enumerate((("+$100", "buy:100", "#38b764"), ("+$1K", "buy:1000", "#38b764"),
                                                ("VENDER", "sell:all", "#ef7d57"))):
            self.botao(10 + i * (w + 2), H - 66, 10 + i * (w + 2) + w, H - 40, rot, fundo=cor_b, tag=tag)
        self.botao(L // 2 - 40, H - 36, L // 2 + 40, H - 10, "SAIR", fundo="#94b0c2", tag="sair")
