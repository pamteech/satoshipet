"""desenho.py - tudo que pinta o widget: molduras, textos, corações, sparkline, painel e console.

Mixin do Tamagoshi (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import math
import random
import time

from . import (
    arts,
    evolucao,
    genetica,
    juice,
    logic,
    onchain,
    papel,
    recursos,
)
from .console import SPRITE
from .graficos import (
    C_PAPEL,
    C_TINTA,
    carregar_frames,
)
from .sprites import FRAMES, nome_folha


class MixinDesenho:
    # ---------- layout (depende da escala) ----------
    def _medidas(self):
        S = 48 * self.escala
        self.S = S
        self.LARG = max(272, S + 48)
        self.Y_SPRITE = 58
        y = self.Y_SPRITE + S + 4
        self.Y_NOME, self.Y_VIDA = y, y + 14
        self.Y_XP = y + 36
        self.Y_PAINEL = y + 52
        self.Y_BOTAO = self.Y_PAINEL + 66
        self.ALT = self.Y_BOTAO + 40
        cx = self.LARG // 2
        self.SPRITE_BOX = (cx - S // 2, self.Y_SPRITE, cx + S // 2, self.Y_SPRITE + S)

    def _txt(self, x, y, texto, cor, anchor="center", escala=1, max_chars=None, sombra=None, tags=()):
        img = self.fonte.imagem(texto, cor, escala, max_chars, sombra)
        self.cv.create_image(x, y, image=img, anchor=anchor, tags=tags)

    def _moldura(self, x0, y0, x1, y1, fundo, borda=C_TINTA, luz=None, sombra=None, tags=()):
        """Caixa 16-bit: borda com cantos mordidos, brilho em cima e sombra embaixo."""
        P, c = 3, self.cv
        c.create_rectangle(x0 + P, y0, x1 - P, y1, fill=borda, width=0, tags=tags)
        c.create_rectangle(x0, y0 + P, x1, y1 - P, fill=borda, width=0, tags=tags)
        c.create_rectangle(x0 + P, y0 + P, x1 - P, y1 - P, fill=fundo, width=0, tags=tags)
        if luz:
            c.create_rectangle(x0 + P, y0 + P, x1 - P, y0 + 2 * P - 1, fill=luz, width=0, tags=tags)
        if sombra:
            c.create_rectangle(x0 + P, y1 - 2 * P + 1, x1 - P, y1 - P, fill=sombra, width=0, tags=tags)
        if self.cfg.get("crt"):  # scanlines sólidas (stipple não funciona no Mac)
            h = fundo.lstrip("#")
            escuro = "#{:02x}{:02x}{:02x}".format(*tuple(int(h[i:i + 2], 16) * 17 // 20 for i in (0, 2, 4)))
            for y in range(y0 + P + 2, y1 - P, 3):
                c.create_line(x0 + P, y, x1 - P, y, fill=escuro, tags=tags)

    def _coracao(self, x, y, esq, dir_, P=3):
        forma = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
        for j, row in enumerate(forma):
            for i, b in enumerate(row):
                if b == "1":
                    self.cv.create_rectangle(x + i * P, y + j * P, x + i * P + P - 1, y + j * P + P - 1,
                                             fill=esq if i < 4 else dir_, width=0)
        self.cv.create_rectangle(x + P, y + P, x + 2 * P - 1, y + 2 * P - 1, fill="#ffffff", width=0)

    def _sparkline(self, moeda, x0, y0, x1, y1, cor):
        serie = self.historico.serie(moeda, (x1 - x0) // 3)
        c = self.cv
        c.create_rectangle(x0, y0, x1, y1, fill="#1a1428", width=0)
        if len(serie) < 2:
            self._txt((x0 + x1) // 2, (y0 + y1) // 2, "...", "#6a5a8a")
            return
        lo, hi = min(serie), max(serie)
        h = (y1 - y0 - 3) // 3
        ant = None
        for i, v in enumerate(serie):
            n = 0 if hi == lo else round((v - lo) / (hi - lo) * h)
            x, y = x0 + 1 + i * 3, y1 - 2 - n * 3
            topo, base = (y, y) if ant is None else (min(y, ant), max(y, ant))
            c.create_rectangle(x, topo - 1, x + 2, base + 1, fill=cor, width=0)
            ant = y

    def _paleta(self):
        """(painel, painel2, sombra, destaque, ícone) conforme hora local / alto contraste."""
        if self.cfg.get("alto_contraste"):
            return juice.ALTO_CONTRASTE
        if not self.cfg.get("dia_noite", True):
            return juice.PERIODOS["noite"]
        return juice.PERIODOS[juice.periodo()]

    def _desenhar(self):
        if self.cena:
            self.cena.desenhar()
            return
        moeda = self.cfg["moeda"]
        ac = bool(self.cfg.get("alto_contraste"))
        pal = self._paleta()
        dormindo = self.estomago.dormindo() and moeda == "BTC" and not self.reacao
        with self.lock:
            preco = self.precos.get(moeda)
        if preco is not None:
            var = self._variacao(moeda, preco)
            novo = logic.estado_do_bicho(var, self.cfg["limite_alta"], self.cfg["limite_queda"])
            if self.estado_forcado and time.time() < self.estado_forcado[1]:
                novo = self.estado_forcado[0]  # sudo moon
            if novo != self.estado:
                self.estado = novo
                self.som.tocar(novo)
                self._nova_frase()
                if novo in ("moon", "rekt") and self.cfg.get("juice", True):
                    self.juice.emitir(novo, self.LARG // 2, self.Y_SPRITE + self.S // 2, self.escala)
            linha_preco, linha_var = self._fmt_preco(moeda, preco), f"{'+' if var >= 0 else ''}{var:.2f}%"
        else:
            linha_preco, linha_var = "carregando", "..."
        cor = arts.CORES[self.estado]
        c, L = self.cv, self.LARG
        c.delete("all")
        mc = (L - 30) // 8  # colunas que cabem no balão
        # ----- balão / toast -----
        if dormindo and not self.toast and not self.console_aberto:
            self.frase_atual = "esperando bloco... zzz"
        if self.toast:
            fundo = "#ffff00" if ac else ("#73eff7" if len(self.toast) > 2 and self.update else "#ffcd75")
            self._moldura(6, 2, L - 6, 48, fundo, luz=None if ac else "#fff4c0", sombra=None if ac else "#ef7d57")
            self._txt(L // 2, 16, self.toast[2] if len(self.toast) > 2 else "CONQUISTA!", C_TINTA if ac else "#b13e53")
            self._txt(L // 2, 32, self.toast[0], C_TINTA, max_chars=mc)
        else:
            fundo = "#ffffff" if ac else C_PAPEL
            self._moldura(6, 2, L - 6, 48, fundo, luz="#ffffff", sombra=None if ac else "#94b0c2")
            self._txt(L // 2, 25, self.frase_atual, C_TINTA, max_chars=mc)
        m = L // 2
        for i, w in enumerate((8, 5, 2)):
            c.create_rectangle(m - w - 3, 45 + i * 3, m + w + 3, 48 + i * 3, fill=C_TINTA, width=0)
            c.create_rectangle(m - w, 45 + i * 3, m + w, 48 + i * 3, fill=fundo, width=0)
        # ----- bicho -----
        frames = self._sprites()
        if self.reacao or (self.comendo and self.comendo <= 4):
            img = frames[("pulo", (FRAMES * 2 - max(self.reacao, self.comendo)) % FRAMES)]
        elif dormindo:
            img = frames[("garimpando", 3)]  # olhinho fechado
        else:
            img = frames[(self.estado, self.frame)]
        tremor = random.randint(-3, 3) if self.panico_t else 0
        sx, sy = self.juice.deslocamento() if self.cfg.get("juice", True) else (0, 0)
        cy = self.Y_SPRITE + self.S // 2
        c.create_image(L // 2 + tremor + sx, cy + sy, image=img)
        if self.cfg.get("juice", True):
            self.juice.desenhar(c)
        E = self.escala
        if dormindo:  # Zzz subindo
            for i in range(3):
                k = (self.frame + i * 2) % 6
                self._txt(L // 2 + self.S // 3 + i * 8, cy - self.S // 3 - k * 4 - i * 6, "z" if i < 2 else "Z",
                          "#94b0c2", sombra=C_TINTA)
        if onchain.fome_por_fee(self.fee)[0] >= 2 and not dormindo:  # suando de fome (fee alta)
            for i, dx in enumerate((-self.S // 4, self.S // 4)):
                yy = cy - self.S // 4 + ((self.frame + i * 2) % 4) * E * 2
                c.create_rectangle(L // 2 + dx, yy, L // 2 + dx + E, yy + E * 2, fill="#73eff7", width=0)
        if self.comendo > 4:  # bloquinho laranja voando até a boca
            t = (10 - self.comendo) / 6
            bx = int(L - 24 - (L - 24 - L // 2) * t)
            by = int(self.Y_SPRITE + 8 + (self.S // 2 - 8) * t * t)
            tam = 4 * E
            c.create_rectangle(bx - tam, by - tam, bx + tam, by + tam, fill="#1a1c2c", width=0)
            c.create_rectangle(bx - tam + E, by - tam + E, bx + tam - E, by + tam - E, fill="#ef7d57", width=0)
            c.create_rectangle(bx - tam + E, by - tam + E, bx + tam - E, by - tam + 2 * E, fill="#ffcd75", width=0)
            self._txt(bx, by, "B", "#f4f4f4")
        elif self.comendo:  # migalhas
            for i in range(5):
                ang = i * 1.3 + self.comendo
                r = (5 - self.comendo) * E * 3
                c.create_rectangle(L // 2 + int(math.cos(ang) * r), cy + int(math.sin(ang) * r) - E * 4,
                                   L // 2 + int(math.cos(ang) * r) + E, cy + int(math.sin(ang) * r) - E * 3,
                                   fill="#ef7d57", width=0)
        if self.reacao:
            k = FRAMES * 2 - self.reacao
            for dx, ph in ((-self.S // 2 - 6, 0), (self.S // 2 - 8, 2), (-self.S // 2 + 10, 4)):
                self._coracao(L // 2 + dx, self.Y_SPRITE + self.S // 2 - (k + ph) * 6, "#b13e53", "#b13e53")
        # ----- nome e vida -----
        nome = self.nome_pet()
        if ac:
            cor = {"moon": "#00ff00", "rekt": "#ff5555", "garimpando": "#ffff00"}[self.estado]
        titulo = "FANTASMA" if self.cfg.get("fantasma") else arts.TITULOS[self.estado]
        self._txt(L // 2, self.Y_NOME, f"{nome} - {titulo}", "#94b0c2" if self.cfg.get("fantasma") else cor,
                  max_chars=(L - 12) // 8, sombra=C_TINTA)
        pk = self.pack_ativo()
        if pk and pk["tipo"] == "patrocinado":  # transparência: marca sempre aparece como PATROCINADO
            self._moldura(8, self.Y_SPRITE, 8 + 11 * 8 + 10, self.Y_SPRITE + 16, "#ffcd75", luz="#fff4c0")
            self._txt(13, self.Y_SPRITE + 4, "PATROCINADO", C_TINTA, anchor="nw")
        self._txt(10, self.Y_VIDA + 2, "VIDA", "#f4f4f4", anchor="nw", sombra=C_TINTA)
        vida = self.conq.vida
        for i in range(5):
            r = vida - i * 2
            self._coracao(48 + i * 24, self.Y_VIDA, "#b13e53" if r >= 1 else "#4a3a5a",
                          "#b13e53" if r >= 2 else "#4a3a5a")
        # ----- nível + barra de XP -----
        y = self.Y_XP
        nv = evolucao.nivel(self.evo.xp)
        self._txt(10, y, f"LV{nv:<2}", "#ffcd75", anchor="nw", sombra=C_TINTA)
        bx0, bx1 = 48, L - 10 - 8 * min(13, len(evolucao.NOMES[self.estagio])) - 6
        c.create_rectangle(bx0, y, bx1, y + 8, fill=C_TINTA, width=0)
        c.create_rectangle(bx0 + 2, y + 2, bx1 - 2, y + 6, fill="#333c57", width=0)
        cheio = int((bx1 - bx0 - 4) * evolucao.progresso_nivel(self.evo.xp))
        if cheio > 0:
            c.create_rectangle(bx0 + 2, y + 2, bx0 + 2 + cheio, y + 6, fill="#41a6f6", width=0)
            c.create_rectangle(bx0 + 2, y + 2, bx0 + 2 + cheio, y + 3, fill="#73eff7", width=0)
        self._txt(L - 10, y, evolucao.NOMES[self.estagio][:13], "#73eff7", anchor="ne", sombra=C_TINTA)
        # ----- painel -----
        y = self.Y_PAINEL
        self._moldura(6, y, L - 6, y + 60, pal[0], borda="#ffffff" if ac else C_TINTA, luz=pal[1], sombra=pal[2])
        if not ac:
            juice.desenhar_icone_ceu(c, L // 2 - 7, y + 8, pal[4], self.frame)
        self._txt(16, y + 10, ("PRO " if self.pro else "") + moeda, "#ffcd75" if self.pro else "#f4f4f4", anchor="nw")
        self._txt(L - 16, y + 10, linha_var, cor, anchor="ne")
        if self.update and not self.toast:
            self._txt(L // 2 + 12, y + 10, "UPD", "#73eff7", anchor="nw")
        self._txt(16, y + 26, self.erro or linha_preco, "#ef7d57" if self.erro else "#f4f4f4", anchor="nw")
        if self.pro:
            self._sparkline(moeda, L - 92, y + 22, L - 16, y + 38, cor)
        else:
            self._txt(L - 16, y + 26, "PRO:graf", "#566c86", anchor="ne")
        info = self._infos_nerd(moeda)
        if info:
            txt, cor_i = info[(self.rodizio // 22) % len(info)]
            self._txt(16, y + 42, txt[:(L - 32) // 8], cor_i, anchor="nw")
        # ----- botão de afiliado -----
        y = self.Y_BOTAO
        self._moldura(6, y, L - 6, y + 36, "#ef7d57", luz="#ffcd75", sombra="#b13e53", tags=("botao",))
        self._txt(L // 2, y + 18, "COMPRAR A QUEDA ANTES\nQUE ELE MORRA!", C_TINTA, tags=("botao",))
        if self.console_aberto:
            self._desenhar_console()

    def _infos_nerd(self, moeda):
        """Linhas que se revezam no painel: F&G, fee, bloco, hashrate, gas, carteira."""
        out = []
        if self.fng:
            v, rot = self.fng
            out.append((f"F&G {v} {rot}", "#38b764" if v >= 55 else "#b13e53" if v <= 45 else "#ffcd75"))
        if self.fee is not None:
            out.append((f"FEE {self.fee} sat/vB {onchain.fome_por_fee(self.fee)[1]}", "#ef7d57"))
        if self.estomago.d.get("altura"):
            out.append((f"BLOCO {self.estomago.d['altura']} NHAC:{self.estomago.comidos}", "#94b0c2"))
        if self.hash:
            out.append((f"HASH {onchain.formatar_hashrate(self.hash)}", "#a7f070"))
        if moeda == "ETH" and self.gas:
            out.append((f"GAS {self.gas:.1f} gwei", "#73eff7"))
        if self.saldo:
            out.append((f"WALLET {self.saldo['total']:,} sats".replace(",", "."), "#ffcd75"))
        for rede, v in self.saldos_multi.items():
            out.append((f"WALLET {v:.4f} {rede.upper()}", "#ffcd75"))
        if (self.cfg.get("papel") or {}).get("hist"):
            r = papel.resumo(self.cfg["papel"], self.precos)
            out.append((f"PAPEL {r['pnl_pct']:+.2f}% (ficticio)", "#38b764" if r["pnl"] >= 0 else "#b13e53"))
        return out

    def _desenhar_console(self):
        """Terminal verde-fósforo por cima do bicho. Fonte pixel, cursor piscando."""
        c, L = self.cv, self.LARG
        y0, y1 = 2, self.Y_PAINEL - 4
        self._moldura(4, y0, L - 4, y1, "#0b0f14", borda="#38b764", luz="#122018")
        cols = (L - 20) // 8
        linhas_vis = (y1 - y0 - 30) // 10
        render = []
        for ln in self.console_linhas:
            if ln == SPRITE:
                render.append(SPRITE)
            else:
                render += self.fonte.quebrar(ln, cols) or [""]
        render = render[-linhas_vis:]
        y = y0 + 8
        for ln in render:
            if ln == SPRITE:  # neofetch: o próprio bicho no terminal
                img = self.__dict__.setdefault("_mini", {}).get((self.cfg["moeda"], self.cfg["skin"], self.estagio))
                if img is None:
                    caminho = (self.plugins[self.cfg["skin"]]["_folha"] if self.cfg["skin"].startswith("plugin:")
                               else recursos.ASSETS / "sprites" / nome_folha(self.cfg["moeda"], self.cfg["skin"], self.estagio))
                    img = carregar_frames(caminho, 1)[("garimpando", 0)]
                    self._mini[(self.cfg["moeda"], self.cfg["skin"], self.estagio)] = img
                c.create_image(L - 12, y, image=img, anchor="ne")
                continue
            cor = "#a7f070" if ln.startswith(">") else "#38b764"
            self._txt(12, y, ln, cor, anchor="nw")
            y += 10
        cursor = "_" if self.frame % 2 == 0 else " "
        self._txt(12, y1 - 18, ("$ " + self.console_input + cursor)[-cols:], "#f4f4f4", anchor="nw")

    def _sprites(self):
        chave = (self.cfg["moeda"], self.cfg["skin"], self.cfg.get("crt"), self.estagio, self._chapeu(),
                 self._chave_dna())
        if chave not in self.cache_sprites:
            self.cache_sprites[chave] = carregar_frames(self._caminho_folha(), self.escala, self.cfg.get("crt"),
                                                        self._chapeu(), **self._dna())
        return self.cache_sprites[chave]

    def _sprites_mini(self):
        chave = ("mini", self.cfg["moeda"], self.cfg["skin"], self.estagio, self._chapeu(), self._chave_dna())
        if chave not in self.cache_sprites:
            self.cache_sprites[chave] = carregar_frames(self._caminho_folha(), 2, chapeu=self._chapeu(),
                                                        **self._dna())
        return self.cache_sprites[chave]

    def _chapeu(self):
        return juice.chapeu_do_dia() if self.cfg.get("chapeus", True) else None

    def _caminho_folha(self):
        moeda, skin = self.cfg["moeda"], self.cfg["skin"]
        if skin.startswith("plugin:"):
            return self.plugins[skin]["_folha"]
        if skin.startswith("loja:") and skin[5:] in self.catalogo:
            from . import loja
            return loja.folha(self.catalogo[skin[5:]], moeda)
        caminho = recursos.ASSETS / "sprites" / nome_folha(moeda, skin, self.estagio)
        if not caminho.exists():  # estágio sem folha? volta pro adulto, ninguém fica invisível
            caminho = recursos.ASSETS / "sprites" / nome_folha(moeda, skin, "adulto")
        return caminho

    def _dna(self):
        # skins de plugin/secretas mantêm as cores do artista; o DNA vale pras skins oficiais
        g = self.genes() if not self.cfg["skin"].startswith(("plugin:", "loja:")) else None
        return {"genes": g, "fantasma": bool(self.cfg.get("fantasma"))}

    def _chave_dna(self):
        d = self._dna()
        return (tuple(sorted((k, v) for k, v in (d["genes"] or {}).items() if k in genetica.GENES)), d["fantasma"])

    def _fmt_preco(self, moeda, preco):
        if not preco:
            return "carregando"
        if self.cfg.get("unidade") == "sats":
            btc = self.precos.get("BTC")
            if moeda == "BTC":
                return f"1$={onchain.sats_por_dolar(preco):,}sat".replace(",", ".")
            if btc:
                sats = preco / btc * 1e8
                return f"{sats:,.2f} sats".replace(",", "X").replace(".", ",").replace("X", ".") if sats < 100 \
                    else f"{sats:,.0f} sats".replace(",", ".")
        return logic.formatar_preco(preco)

    # ---------- desenho ----------
    def _variacao(self, moeda, preco):
        refs = self.cfg["preco_referencia"]
        if not self.pro or moeda not in refs:
            refs = self.__dict__.setdefault("_refs_sessao", {})
            refs.setdefault(moeda, preco)
        return logic.variacao_pct(preco, refs[moeda])

    def nome_pet(self):
        if self.cfg.get("nome_pet"):
            return self.cfg["nome_pet"][:12]
        return (self.plugins[self.cfg["skin"]]["nome"] if self.cfg["skin"].startswith("plugin:")
                else arts.NOMES[self.cfg["moeda"]])
