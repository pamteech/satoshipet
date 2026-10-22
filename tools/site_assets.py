"""Gera os assets do site: og.png (1200x630), card de exemplo em docs/ e copia sprites/GIFs.

    PYTHONPATH=src python tools/site_assets.py
"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from tamagoshi_cripto import recursos, share  # noqa: E402
from tamagoshi_cripto.pixel import rgb  # noqa: E402

SITE = RAIZ / "site" / "assets"


def og():
    W, H = 400, 210
    img = Image.new("RGBA", (W, H), rgb("preto") + (255,))
    d = ImageDraw.Draw(img)
    f = share._Fonte()
    for y in range(H):
        for x in range(W):
            t = y / H + ((x * 7 + y * 13) % 4) / 24
            img.putpixel((x, y), rgb("preto" if t < 0.4 else "roxo" if t < 0.85 else "vinho") + (255,))
    for i in range(60):
        img.putpixel(((i * 97) % W, (i * 53) % 120), rgb("branco" if i % 5 == 0 else "cinza") + (255,))
    for bx in range(0, W, 20):
        share._moldura(d, bx + 1, 178, bx + 18, 192, "laranja", luz="amarelo")
    d.rectangle([0, 195, W, H], fill=rgb("preto") + (255,))
    t1, t2 = "TAMAGOSHI", "CRIPTO"
    f.escrever(img, (W - f.larg(t1 + " " + t2, 3)) // 2, 16, t1, "branco", 3, sombra="roxo")
    f.escrever(img, (W - f.larg(t1 + " " + t2, 3)) // 2 + f.larg(t1 + " ", 3), 16, t2, "laranja", 3, sombra="vinho")
    sub = "o pet pixel art que come blocos de bitcoin"
    f.escrever(img, (W - f.larg(sub)) // 2, 48, sub, "amarelo")
    linhas = {"BTC": 1, "ETH": 0, "SOL": 1, "DOGE": 0, "PEPE": 2}
    for i, (m, ln) in enumerate(linhas.items()):
        sh = Image.open(recursos.ASSETS / "sprites" / f"{m}_padrao.png").convert("RGBA")
        pet = sh.crop((48, ln * 48, 96, ln * 48 + 48)).resize((96, 96), Image.NEAREST) if m == "BTC" else \
            sh.crop((48, ln * 48, 96, ln * 48 + 48)).resize((72, 72), Image.NEAREST)
        x = [8, 84, 152, 240, 318][i] + (0 if m == "BTC" else 0)
        y = 178 - pet.height + 4
        img.alpha_composite(pet, (x if m != "BTC" else 160, y) if False else (x, y))
    rod = "gratis - macos - windows - linux - terminal"
    f.escrever(img, (W - f.larg(rod)) // 2, 198, rod, "lima")
    img.resize((1200, 630), Image.NEAREST).convert("RGB").save(SITE / "og.png")


def card_exemplo():
    st = {"nome": "Satoshinho", "moeda": "BTC", "estagio": "WHALE", "nivel": 15, "xp": 2015, "xp_pct": 0.62,
          "preco_fmt": "$108,421.00", "variacao_pct": 3.41, "humor": "moon", "skin": "padrao", "btc": {"comidos": 42}}
    share.gerar(st, ["genesis", "pow_100", "whale_alert", "sudo"]).convert("RGB").save(RAIZ / "docs" / "share_card.png")


def copiar():
    s = recursos.ASSETS / "sprites"
    (SITE / "sprites").mkdir(parents=True, exist_ok=True)
    (SITE / "gif").mkdir(parents=True, exist_ok=True)
    nomes = [f"{m}_padrao" for m in ("BTC", "ETH", "SOL", "DOGE", "PEPE")]
    nomes += [f"BTC_padrao_{e}" for e in ("ovo", "bebe", "whale", "diamond")] + ["BTC_cyberpunk", "BTC_gato", "BTC_sapo"]
    for n in nomes:
        shutil.copy(s / f"{n}.png", SITE / "sprites" / f"{n}.png")
    for g in ("btc", "eth", "sol", "doge", "pepe", "comendo", "console", "evoluindo", "onboarding_ovo", "minigame", "juice_moon"):
        shutil.copy(RAIZ / "docs" / "demo" / f"{g}.gif", SITE / "gif" / f"{g}.gif")


if __name__ == "__main__":
    copiar()
    og()
    card_exemplo()
    print("ok: site/assets/og.png, docs/share_card.png")
