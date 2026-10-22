"""graficos.py - constantes de cor/tempo e o carregador de sprites (PIL -> PhotoImage sem borrar)."""
import base64
import io
import tkinter as tk

from PIL import Image

from . import (
    genetica,
    juice,
)
from .sprites import FRAMES, LINHAS

COR_TRANSP = "#010101"   # cor-chave que vira buraco no Windows
FRAME_MS = 180           # 4 frames por loop ~ 0,7s
FRASE_MS = 10000
SKINS_PRO = {"cyberpunk", "gato", "sapo"}

C_TINTA, C_PAPEL, C_PAINEL, C_PAINEL2 = "#1a1c2c", "#f4f4f4", "#29213f", "#3e3466"


def _png_para_tk(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def carregar_frames(caminho, escala, crt=False, chapeu=None, genes=None, fantasma=False):
    """Folha 192x192 -> {(linha, frame): PhotoImage} ampliado sem borrar (+ chapéu de época, + scanlines CRT)."""
    folha = Image.open(caminho).convert("RGBA")
    frames = {}
    for j, linha in enumerate(LINHAS):
        for f in range(FRAMES):
            fr = folha.crop((f * 48, j * 48, (f + 1) * 48, (j + 1) * 48))
            if fantasma:  # hardcore: virou assombração
                fr = genetica.fantasma(fr)
            else:
                fr = genetica.aplicar(fr, genes)  # DNA do bicho (v1.4)
                if chapeu:
                    fr = juice.aplicar_chapeu(fr, chapeu)
            fr = fr.resize((48 * escala, 48 * escala), Image.NEAREST)
            if crt and escala >= 2:
                px = fr.load()
                for y in range(escala - 1, fr.height, escala):  # última linha de cada pixel escurece
                    for x in range(fr.width):
                        r, g, b, a = px[x, y]
                        if a:
                            px[x, y] = (r * 3 // 5, g * 3 // 5, b * 3 // 5, a)
            frames[(linha, f)] = _png_para_tk(fr)
    return frames
