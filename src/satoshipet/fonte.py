"""fonte.py - fonte bitmap 8x8 (Press Start 2P rasterizada, OFL) desenhada pixel a pixel.

Nada de fonte do sistema: funciona igual no Windows, Mac e Linux, e fica nítida em
qualquer escala. Cada texto vira um PhotoImage em cache (só os "runs" de pixels acesos).
"""
import json
import tkinter as tk

from . import recursos


class FontePixel:
    def __init__(self):
        dados = json.loads((recursos.ASSETS / "fonts" / "pixel8.json").read_text(encoding="utf-8"))
        self.tam = dados["tam"]
        self.glifos = dados["glifos"]
        self.cache = {}

    def _glifo(self, ch):
        return self.glifos.get(ch) or self.glifos.get("?")

    def quebrar(self, texto, max_chars):
        """Quebra por palavras pra caber em max_chars colunas."""
        linhas = []
        for par in texto.split("\n"):
            atual = ""
            for palavra in par.split(" "):
                cand = (atual + " " + palavra).strip()
                if len(cand) <= max_chars or not atual:
                    atual = cand
                else:
                    linhas.append(atual)
                    atual = palavra
            linhas.append(atual)
        return linhas

    def medir(self, texto, escala=1, max_chars=None):
        linhas = self.quebrar(texto, max_chars) if max_chars else texto.split("\n")
        w = max(len(l) for l in linhas) * self.tam * escala
        return w, len(linhas) * (self.tam + 2) * escala

    def imagem(self, texto, cor, escala=1, max_chars=None, sombra=None):
        chave = (texto, cor, escala, max_chars, sombra)
        if chave in self.cache:
            return self.cache[chave]
        linhas = self.quebrar(texto, max_chars) if max_chars else texto.split("\n")
        larg = max(1, max(len(l) for l in linhas)) * self.tam
        w, h = larg * escala + escala, len(linhas) * (self.tam + 2) * escala + escala
        img = tk.PhotoImage(width=w, height=h)
        camadas = ([(sombra, escala)] if sombra else []) + [(cor, 0)]
        for cor_c, off in camadas:
            for li, linha in enumerate(linhas):
                x0 = (larg - len(linha) * self.tam) // 2  # centraliza cada linha
                y0 = li * (self.tam + 2)
                for ci, ch in enumerate(linha):
                    g = self._glifo(ch)
                    for gy, row in enumerate(g):
                        gx = 0
                        while gx < len(row):
                            if row[gx] == "1":
                                ini = gx
                                while gx < len(row) and row[gx] == "1":
                                    gx += 1
                                X = (x0 + ci * self.tam + ini) * escala + off
                                Y = (y0 + gy) * escala + off
                                img.put(cor_c, to=(X, Y, X + (gx - ini) * escala, Y + escala))
                            else:
                                gx += 1
        self.cache[chave] = img
        if len(self.cache) > 400:  # não deixa o cache virar baleia
            self.cache.pop(next(iter(self.cache)))
        return img
