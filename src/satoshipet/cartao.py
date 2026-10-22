"""cartao.py - card de perfil pro README do GitHub: SVG animado (sprite pulando) ou PNG estático.

Entrada: o JSON de stats exportado pelo app (`export` no console, ou GET /status da API local),
ou um código de pet TAMA1-... . Saída: SVG com 4 frames em PNG embutido + animação CSS (o GitHub
renderiza <img src="card.svg"> com animação). Nada de fonte externa, nada de JS, nada de rastreio.
"""
import base64
import io
import json
import time

from PIL import Image

from . import genetica, recursos
from .pixel import rgb
from .share import _Fonte
from .sprites import nome_folha

W, H, ESC = 240, 84, 2
LINHA = {"garimpando": 0, "moon": 1, "rekt": 2, "pulo": 3}
CAMPOS_SEGUROS = ("nome", "moeda", "nivel", "xp", "estagio", "humor", "variacao_pct", "conquistas", "genes",
                  "raridade", "batalhas", "crashes", "btc_comidos", "exportado_em", "versao")
EST = {"OVO": "ovo", "BEBE": "bebe", "ADULTO": "adulto", "WHALE": "whale", "DIAMOND HANDS": "diamond"}


def exportar_stats(status, versao=""):
    """Só o que é seguro tornar público. NUNCA carteira, saldo, e-mail, licença, device_id."""
    s = {k: status.get(k) for k in CAMPOS_SEGUROS if k in status}
    s["btc_comidos"] = (status.get("btc") or {}).get("comidos", 0)
    s["exportado_em"] = int(time.time())
    s["versao"] = versao
    return s


def de_petcode(codigo):
    pet, erro = genetica.importar(codigo)
    if erro:
        raise ValueError(erro)
    g = pet["genes"]
    return {"nome": pet["nome"], "moeda": g["moeda"], "nivel": pet["nivel"], "xp": pet["xp"],
            "estagio": pet["estagio"].upper(), "humor": "garimpando", "genes": {k: g[k] for k in genetica.GENES},
            "raridade": genetica.raridade(g)[0]}


def _estagio(s):
    e = str(s.get("estagio", "adulto"))
    return EST.get(e.upper(), e.lower() if e.lower() in ("ovo", "bebe", "adulto", "whale", "diamond") else "adulto")


def frames(s, escala=2):
    moeda = s.get("moeda", "BTC")
    arq = recursos.ASSETS / "sprites" / nome_folha(moeda, "padrao", _estagio(s))
    if not arq.exists():
        arq = recursos.ASSETS / "sprites" / nome_folha(moeda, "padrao", "adulto")
    folha = Image.open(arq).convert("RGBA")
    j = LINHA.get(s.get("humor", "garimpando"), 0)
    out = []
    for f in range(4):
        fr = folha.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48))
        fr = genetica.aplicar(fr, s.get("genes") or {})
        out.append(fr.resize((48 * escala, 48 * escala), Image.NEAREST))
    return out


def fundo(s):
    """Moldura + textos em pixel font (240x80 nativo)."""
    from PIL import ImageDraw
    img = Image.new("RGBA", (W, H), rgb("#1a1c2c") + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle((2, 2, W - 3, H - 3), fill=rgb("#29213f"))
    d.rectangle((2, 2, W - 3, 4), fill=rgb("#3e3466"))
    d.rectangle((4, 8, 60, H - 8), fill=rgb("#1d1730"))
    for x in range(4, 61, 8):  # chão quadriculado
        d.rectangle((x, H - 16, x + 3, H - 9), fill=rgb("#38b764"))
        d.rectangle((x + 4, H - 16, x + 7, H - 9), fill=rgb("#257179"))
    f = _Fonte()
    rar = s.get("raridade") or genetica.raridade(s.get("genes") or {})[0]
    humor = {"moon": ("TO THE MOON", "#a7f070"), "rekt": ("REKT", "#b13e53")}.get(s.get("humor"),
                                                                                     ("GARIMPANDO", "#ffcd75"))
    f.escrever(img, 68, 9, str(s.get("nome", "anon"))[:12], "#ffcd75", sombra="#1a1c2c")
    f.escrever(img, 68, 21, f"{s.get('moeda', 'BTC')} LV{s.get('nivel', 1)} {_estagio(s).upper()}"[:21], "#f4f4f4")
    f.escrever(img, 68, 33, humor[0], humor[1])
    b = s.get("batalhas") or {}
    f.escrever(img, 68, 45, f"BLOCOS {s.get('btc_comidos', 0)}  {b.get('vitorias', 0)}V/{b.get('derrotas', 0)}D"[:21],
               "#94b0c2")
    f.escrever(img, 68, 57, f"DNA {rar.upper()}"[:21], genetica.COR_RARIDADE.get(rar, "#94b0c2"))
    f.escrever(img, 68, 71, "SATOSHIPET", "#566c86")
    return img


def _b64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def svg(s, ms=180):
    bg = fundo(s).resize((W * ESC, H * ESC), Image.NEAREST)
    frs = frames(s, ESC)
    dur = ms * 4 / 1000
    css = "".join(
        f"@keyframes f{i}{{0%,{i * 25}%{{opacity:0}}{i * 25 + 0.01}%,{(i + 1) * 25}%{{opacity:1}}"
        f"{(i + 1) * 25 + 0.01}%,100%{{opacity:0}}}}.f{i}{{opacity:{1 if i == 0 else 0};animation:f{i} {dur}s step-end infinite}}"
        for i in range(4))
    css = css.replace("{0%,0%{opacity:0}0.01%", "{0%")  # frame 0 começa visível
    imgs = "".join(f'<image class="f{i}" x="{8 * ESC - 10}" y="{8 * ESC}" width="{48 * ESC}" height="{48 * ESC}" '
                   f'href="data:image/png;base64,{_b64(fr)}"/>' for i, fr in enumerate(frs))
    nome = str(s.get("nome", "anon")).replace("&", "&amp;").replace("<", "&lt;")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * ESC}" height="{H * ESC}" '
            f'viewBox="0 0 {W * ESC} {H * ESC}" role="img" aria-label="{nome} - SatoshiPet">'
            f'<title>{nome} - SatoshiPet</title><style>{css}</style>'
            f'<image x="0" y="0" width="{W * ESC}" height="{H * ESC}" href="data:image/png;base64,{_b64(bg)}"/>'
            f'{imgs}</svg>')


def png(s):
    img = fundo(s).resize((W * ESC, H * ESC), Image.NEAREST)
    img.alpha_composite(frames(s, ESC)[0], (8 * ESC - 10, 8 * ESC))
    return img


def carregar(caminho):
    return json.loads(open(caminho, encoding="utf-8").read())
