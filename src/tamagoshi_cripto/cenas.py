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
