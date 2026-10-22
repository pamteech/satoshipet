"""share.py - card 1200x675 em pixel art pra postar no X (quem posta é você, a gente só prepara).

Desenha tudo numa grade nativa de 400x225 e amplia 3x com NEAREST: pixel de verdade, sem blur.
Nada é enviado pra lugar nenhum: o PNG fica no seu computador e o X abre com o texto pronto.
"""
import json
import time
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw

from . import conquistas, recursos
from .pixel import rgb
from .sprites import nome_folha

SITE = "https://pamteech.github.io/satoshipet"   # troque quando o site estiver no ar
W, H, ESC = 400, 225, 3
COR_HUMOR = {"moon": "lima", "rekt": "vermelho", "garimpando": "amarelo"}
TXT_HUMOR = {"moon": "TO THE MOON", "rekt": "REKT", "garimpando": "GARIMPANDO"}
LINHA = {"garimpando": 0, "moon": 1, "rekt": 2}


class _Fonte:
    def __init__(self):
        d = json.loads((recursos.ASSETS / "fonts" / "pixel8.json").read_text(encoding="utf-8"))
        self.tam, self.g = d["tam"], d["glifos"]

    def larg(self, s, e=1):
        return len(s) * self.tam * e

    def escrever(self, img, x, y, s, cor, e=1, sombra=None):
        px = img.load()
        for cor_c, off in ([(sombra, e)] if sombra else []) + [(cor, 0)]:
            c = rgb(cor_c) + (255,)
            for i, ch in enumerate(s):
                for gy, row in enumerate(self.g.get(ch) or self.g.get("?")):
                    for gx, b in enumerate(row):
                        if b == "1":
                            for dy in range(e):
                                for dx in range(e):
                                    X, Y = x + (i * self.tam + gx) * e + dx + off, y + gy * e + dy + off
                                    if 0 <= X < img.width and 0 <= Y < img.height:
                                        px[X, Y] = c


def _cor(n):
    return rgb(n) + (255,)


def _moldura(d, x0, y0, x1, y1, fundo, borda="preto", luz=None):
    d.rectangle([x0 + 1, y0, x1 - 1, y1], fill=_cor(borda))
    d.rectangle([x0, y0 + 1, x1, y1 - 1], fill=_cor(borda))
    d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=_cor(fundo))
    if luz:
        d.line([x0 + 2, y0 + 1, x1 - 2, y0 + 1], fill=_cor(luz))


def gerar(st, desbloqueadas=(), site=SITE, frame=1):
    """Retorna PIL.Image 1200x675. st = dict do status() do app (ou do TUI)."""
    img = Image.new("RGBA", (W, H), _cor("preto"))
    d = ImageDraw.Draw(img)
    f = _Fonte()
    humor = st.get("humor", "garimpando")
    # céu com degradê dithered + estrelas determinísticas
    for y in range(H):
        for x in range(W):
            t = y / H + ((x * 7 + y * 13) % 4) / 24
            img.putpixel((x, y), _cor("preto" if t < 0.35 else "roxo" if t < 0.8 else "vinho"))
    for i in range(70):
        x, y = (i * 97) % W, (i * 53) % 150
        img.putpixel((x, y), _cor("branco" if i % 5 == 0 else "cinza"))
    # chão: blocos laranja (a timechain, claro)
    for bx in range(0, W, 20):
        _moldura(d, bx + 1, 190, bx + 18, 204, "laranja", luz="amarelo")
        d.line([bx + 1, 205, bx + 18, 205], fill=_cor("vinho"))
    d.rectangle([0, 207, W, H], fill=_cor("preto"))
    # o bicho (estágio certo), 3x nativo
    est = {"OVO": "ovo", "BEBE": "bebe", "ADULTO": "adulto", "WHALE": "whale",
           "DIAMOND HANDS": "diamond"}.get(str(st.get("estagio", "ADULTO")).upper(), "adulto")
    folha = recursos.ASSETS / "sprites" / nome_folha(st.get("moeda", "BTC"), st.get("skin", "padrao")
                                                     if not str(st.get("skin", "")).startswith("plugin:") else "padrao", est)
    if not folha.exists():
        folha = recursos.ASSETS / "sprites" / nome_folha(st.get("moeda", "BTC"), "padrao", est)
    sh = Image.open(folha).convert("RGBA")
    pet = sh.crop((frame * 48, LINHA.get(humor, 0) * 48, frame * 48 + 48, LINHA.get(humor, 0) * 48 + 48))
    pet = pet.resize((144, 144), Image.NEAREST)
    # sombra elíptica no chão
    d.ellipse([30, 184, 154, 192], fill=_cor("preto"))
    img.alpha_composite(pet, (20, 44))
    # painel direito
    _moldura(d, 180, 14, 388, 182, "marinho", luz="azul")
    nome = str(st.get("nome", "Satoshinho"))[:12]
    f.escrever(img, 192, 24, nome.upper(), "amarelo", 2, sombra="preto")
    f.escrever(img, 192, 46, f"{st.get('moeda', 'BTC')} · {st.get('estagio', 'ADULTO')}".replace("·", "-"),
               "ciano")
    # nível + XP
    lv = f"LV{st.get('nivel', 1)}"
    f.escrever(img, 192, 62, lv, "branco", 2)
    bx0, bx1 = 192 + f.larg(lv, 2) + 8, 376
    _moldura(d, bx0, 64, bx1, 76, "preto", "cinza")
    pct = max(0.0, min(1.0, float(st.get("xp_pct") or 0)))
    if pct > 0:
        d.rectangle([bx0 + 2, 66, bx0 + 2 + int((bx1 - bx0 - 4) * pct), 74], fill=_cor("lima"))
        d.line([bx0 + 2, 66, bx0 + 2 + int((bx1 - bx0 - 4) * pct), 66], fill=_cor("branco"))
    f.escrever(img, 192, 84, f"XP {st.get('xp', 0)}", "cinza_claro")
    # preço + humor
    var = float(st.get("variacao_pct") or 0)
    f.escrever(img, 192, 100, str(st.get("preco_fmt", "?")), "branco", 2, sombra="preto")
    f.escrever(img, 192, 120, f"{var:+.2f}%  {TXT_HUMOR.get(humor, humor.upper())}", COR_HUMOR.get(humor, "branco"))
    # conquistas
    total = len(conquistas.LISTA)
    f.escrever(img, 192, 138, f"CONQUISTAS {len(desbloqueadas)}/{total}", "amarelo")
    nomes = [conquistas.LISTA[c][0] for c in list(desbloqueadas)[-3:] if c in conquistas.LISTA]
    for i, n in enumerate(nomes):
        d.rectangle([192, 152 + i * 10, 196, 156 + i * 10], fill=_cor("amarelo"))
        f.escrever(img, 200, 150 + i * 10, n[:22], "cinza_claro")
    # balão + rodapé
    blocos = (st.get("btc") or {}).get("comidos")
    if blocos:
        _moldura(d, 20, 18, 168, 40, "branco", luz=None)
        f.escrever(img, 26, 26, f"{blocos} BLOCOS COMIDOS"[:17], "preto")
    dominio = site.replace("https://", "").replace("http://", "").rstrip("/")
    rod = f"baixe em {dominio}"
    f.escrever(img, (W - f.larg(rod)) // 2, 212, rod[:49], "lima")
    return img.resize((W * ESC, H * ESC), Image.NEAREST)


def texto_post(st, site=SITE):
    h = {"moon": "TO THE MOON 🚀", "rekt": "REKT 💀", "garimpando": "garimpando ⛏️"}.get(st.get("humor"), "")
    blocos = (st.get("btc") or {}).get("comidos") or 0
    comeu = f"Já comeu {blocos} blocos. " if blocos else ""
    return (f"Meu {st.get('nome', 'bichinho')} tá LV{st.get('nivel', 1)} ({st.get('estagio', '?')}) e "
            f"{h} com {st.get('moeda', 'BTC')} a {st.get('preco_fmt', '?')}. {comeu}#Bitcoin #SatoshiPet")


def url_x(st, site=SITE):
    """Intent do X: abre a caixa de post preenchida. A imagem você anexa na mão (o X não aceita via URL)."""
    return "https://x.com/intent/post?" + urllib.parse.urlencode({"text": texto_post(st, site), "url": site})


def pasta_destino():
    for p in (Path.home() / "Pictures", Path.home() / "Imagens"):
        if p.is_dir():
            return p
    return Path.home()


def salvar(st, desbloqueadas=(), site=SITE, pasta=None):
    pasta = Path(pasta) if pasta else pasta_destino()
    caminho = pasta / f"satoshipet_card_{time.strftime('%Y%m%d_%H%M%S')}.png"
    gerar(st, desbloqueadas, site).convert("RGB").save(caminho)
    return caminho
