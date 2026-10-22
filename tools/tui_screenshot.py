"""Gera docs/screenshots/tui.png simulando o terminal (pro README). python tools/tui_screenshot.py"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tamagoshi_cripto import tui  # noqa: E402

CEL_W, CEL_H = 8, 16
sprites = tui.carregar("PEPE", "padrao")
spr = sprites[("moon", 1)]
linhas_txt = ["Sapo Degen - TO THE MOON!", "PEPE $0.0000049 +8.12%   ♥♥♥♥♡",
              '"rug ou moon, sem meio-termo"', "[c] trocar moeda  [espaço] carinho  [q] sair"]
cols = 60
img = Image.new("RGB", (cols * CEL_W + 32, (24 + len(linhas_txt) + 3) * CEL_H + 40), (24, 24, 32))
d = ImageDraw.Draw(img)
d.rectangle((0, 0, img.width, 22), fill=(52, 52, 64))
for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
    d.ellipse((10 + i * 18, 6, 20 + i * 18, 16), fill=c)
d.text((img.width // 2 - 70, 5), "~ tamagoshi --tui", fill=(200, 200, 210))
ox, oy = 16, 34
px = spr.load()
for y in range(0, 48, 2):  # cada célula ▀: metade de cima/baixo
    for x in range(48):
        for k in (0, 1):
            r, g, b, a = px[x, y + k]
            if a:
                X, Y = ox + x * CEL_W, oy + (y // 2) * CEL_H + k * (CEL_H // 2)
                d.rectangle((X, Y, X + CEL_W - 1, Y + CEL_H // 2 - 1), fill=(r, g, b))
try:
    fonte = ImageFont.truetype("DejaVuSansMono.ttf", 14)
except OSError:
    fonte = ImageFont.load_default()
cores = [(56, 183, 100), (230, 230, 230), (200, 200, 200), (120, 120, 140)]
for i, (t, c) in enumerate(zip(linhas_txt, cores)):
    d.text((ox, oy + (25 + i) * CEL_H), t, font=fonte, fill=c)
img.save(RAIZ / "docs" / "screenshots" / "tui.png")
print("ok")
