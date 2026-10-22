"""animacao.py - v1.6: liga os efeitos (efeitos.py) e o modo economia (energia.py) no app."""
from __future__ import annotations

import threading
import time

from . import efeitos, energia, evolucao, i18n
from .graficos import C_TINTA, silhueta


class MixinAnimacao:
    def _init_efeitos(self):
        self.fx_trans = None        # efeitos.Transicao em andamento
        self.fx_evo = None          # efeitos.Evolucao em andamento
        self.idle = efeitos.Idle()
        self.mouse = None           # (x, y) relativo ao canvas, ou None
        self.dica = None            # [chave, frames parado em cima]
        self.ultimo_toque = time.time()
        self.modo_energia = "normal"
        self._assin_cena = None

    def _iniciar_efeitos(self):
        self.cv.bind("<Motion>", self._mouse_move, add="+")
        self.cv.bind("<Leave>", self._mouse_sai, add="+")
        threading.Thread(target=self.loop_energia, daemon=True).start()

    # ---------- energia ----------
    def loop_energia(self):
        while True:
            try:
                m = energia.medir(self.cfg.get("economia", True))
            except Exception:
                m = "normal"
            if m != self.modo_energia:
                self.modo_energia = m
            time.sleep(30)

    def fator_frame(self):
        return energia.FATORES.get(self.modo_energia, (1, 1))[0]

    def fator_rede(self):
        return energia.FATORES.get(self.modo_energia, (1, 1))[1]

    def dormir_rede(self, segundos):
        """sleep das threads de rede, esticado na bateria/pausa. Recalcula a cada pedacinho:
        quando a tela destrava, a espera volta ao normal na hora (resume limpo)."""
        ini = time.monotonic()  # monotônico: relógio do sistema pulando não acelera a rede
        while time.monotonic() - ini < segundos * self.fator_rede():
            time.sleep(min(2.0, max(0.01, segundos)))

    # ---------- mouse / dicas ----------
    def _mouse_move(self, e):
        self.mouse = (e.x, e.y)
        self.ultimo_toque = time.time()
        z = efeitos.zona(e.x, e.y, self._zonas()) if not self.cena and not self.console_aberto else None
        if z is None:
            self.dica = None
        elif not self.dica or self.dica[0] != z:
            self.dica = [z, 0]

    def _mouse_sai(self, _e=None):
        self.mouse = None
        self.dica = None

    def _zonas(self):
        L, y = self.LARG, self.Y_PAINEL
        z = {
            "vida": (44, self.Y_VIDA - 2, 48 + 5 * 24, self.Y_VIDA + 18),
            "xp": (8, self.Y_XP - 2, L - 8, self.Y_XP + 10),
            "pro": (12, y + 6, 12 + 8 * 8, y + 20),
            "preco": (12 + 8 * 8, y + 6, L - 12, y + 38),
            "info": (12, y + 40, L - 12, y + 56),
            "botao": (6, self.Y_BOTAO, L - 6, self.Y_BOTAO + 36),
        }
        if not self.pro:
            z["preco"] = (12, y + 6, L - 12, y + 38)
            z["pro"] = (L - 16 - 8 * 8, y + 24, L - 12, y + 38)  # "PRO:graf"
        return z

    def _texto_dica(self, chave):
        if chave == "info":
            info = self._infos_nerd(self.cfg["moeda"])
            if not info:
                return None
            atual = info[(self.rodizio // 22) % len(info)][0]
            chave = next((k for k in efeitos.DICAS if atual.startswith(k)), None)
            if chave is None:
                return None
        return efeitos.DICAS.get(chave)

    def _desenhar_dica(self):
        if not self.dica or self.dica[1] < 2 or not self.mouse:  # ~0,4 s parado em cima
            return
        txt = self._texto_dica(self.dica[0])
        if not txt:
            return
        L = self.LARG
        cols = (L - 28) // 8
        linhas = self.fonte.quebrar(i18n.t(txt), cols)[:4]
        w = max(len(s) for s in linhas) * 8 + 12
        h = len(linhas) * 10 + 10
        mx, my = self.mouse
        x0 = max(4, min(L - w - 4, mx - w // 2))
        y0 = my - h - 10 if my - h - 10 > 4 else my + 16
        self._moldura(x0, y0, x0 + w, y0 + h, "#f4f4f4", luz="#ffffff", sombra="#94b0c2", tags=("fx",))
        for i, s in enumerate(linhas):
            self._txt(x0 + 6, y0 + 6 + i * 10, s, C_TINTA, anchor="nw", tags=("fx",))

    # ---------- transições ----------
    def transicao(self, tipo="dissolve", duracao=6):
        if self.cfg.get("juice", True):
            self.fx_trans = efeitos.Transicao(tipo, duracao)

    def _checar_cena(self):
        c = self.cena
        assin = (type(c).__name__, getattr(c, "passo", None), getattr(c, "aba", None)) if c else None
        if assin != self._assin_cena:
            if self._assin_cena is not None or c is not None:
                tipo = "wipe" if (c is None or self._assin_cena is None) else "dissolve"
                if c is not None and self._assin_cena and self._assin_cena[0] == assin[0]:
                    tipo = "mosaico"  # mesmo tipo de tela, passo/aba diferente
                self.transicao(tipo)
            self._assin_cena = assin

    # ---------- evolução ----------
    def iniciar_evolucao(self, velho, novo):
        if not self.cfg.get("juice", True):
            return
        try:
            atual = self.estagio
            self.estagio = velho
            p_velho = self._caminho_folha()
            self.estagio = atual
            p_novo = self._caminho_folha()
            E = self.escala
            self.fx_evo = efeitos.Evolucao(silhueta(p_velho, E), silhueta(p_novo, E),
                                           evolucao.NOMES.get(novo, str(novo)))
        except Exception:
            self.fx_evo = None

    def _sprite_vivo(self, img, frames, dormindo):
        """Troca/move o sprite: evolução > piscar/bocejo. Retorna (img, dx, dy)."""
        if self.fx_evo:
            return self.fx_evo.imagem(img), 0, 0
        dx = dy = 0
        if not dormindo and not self.reacao and not self.comendo and not self.panico_t:
            if self.idle.olhos_fechados():
                img = frames.get(("garimpando", 3), img)
            cx, cy = self.LARG // 2, self.Y_SPRITE + self.S // 2
            mx, my = self.mouse if self.mouse else (None, None)
            dx, dy = self.idle.deslocamento(cx, cy, mx, my, self.escala)
        return img, dx, dy

    def _overlay_fx(self):
        c, L, A = self.cv, self.LARG, self.ALT
        if self.fx_evo and not self.cena:
            cx, cy = L // 2, self.Y_SPRITE + self.S // 2
            self.fx_evo.desenhar(c, L, A, cx, cy, self.S // 2, self.escala, self._txt)
        if not self.cena:
            self._desenhar_dica()
        if self.fx_trans:
            self.fx_trans.desenhar(c, L, A)

    def _tick_efeitos(self):
        if self.fx_trans:
            self.fx_trans.tick()
            if not self.fx_trans.viva:
                self.fx_trans = None
        if self.fx_evo:
            self.fx_evo.tick()
            if not self.fx_evo.viva:
                self.fx_evo = None
        if self.dica:
            self.dica[1] += 1
        noite = time.localtime().tm_hour >= 23 or time.localtime().tm_hour < 6
        self.idle.tick(time.time() - self.ultimo_toque, noite)
