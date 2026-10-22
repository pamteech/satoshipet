"""graficos.py - constantes de cor/tempo e o carregador de sprites (PIL -> PhotoImage sem borrar)."""
import base64
import io
import sys
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
    if sys.platform == "darwin":
        return _rgba_para_tk_opaco(img)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def _rgba_para_tk_opaco(img):
    """macOS: numa janela -transparent (fundo systemTransparent) o Tk Aqua NÃO desenha PhotoImage
    vinda de PNG com canal alfa -> o bicho some (texto aparecia porque a fonte usa put()).
    Aqui pintamos só os pixels visíveis com put() (alfa 0/1, como a fonte). Pixel art não tem
    meio-alfa mesmo; o que for >=128 vira opaco, o resto fica "não pintado" = transparente."""
    img = img.convert("RGBA")
    w, h = img.size
    foto = tk.PhotoImage(width=w, height=h)
    px = img.load()
    for y in range(h):
        x = 0
        while x < w:
            r, g, b, a = px[x, y]
            if a < 128:
                x += 1
                continue
            ini = x
            while x < w and px[x, y][:3] == (r, g, b) and px[x, y][3] >= 128:
                x += 1
            foto.put(f"#{r:02x}{g:02x}{b:02x}", to=(ini, y, x, y + 1))
    return foto


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


def silhueta(caminho, escala, cor="#f4f4f4", linha="garimpando"):
    """Frame 0 da folha pintado de uma cor só (pra evolução estilo Pokémon). Alfa binário: ok no Mac."""
    folha = Image.open(caminho).convert("RGBA")
    j = LINHAS.index(linha) if linha in LINHAS else 0
    fr = folha.crop((0, j * 48, 48, (j + 1) * 48)).resize((48 * escala, 48 * escala), Image.NEAREST)
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    a = fr.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    sol = Image.new("RGBA", fr.size, (r, g, b, 255))
    sol.putalpha(a)
    return _png_para_tk(sol)
