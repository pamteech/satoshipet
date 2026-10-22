"""Screenshots do site (desktop + mobile) via Chrome headless -> docs/screenshots/site_*.png.

    cd site && python -m http.server 8765 &      # (e opcional: python server/ranking.py)
    python tools/site_screenshots.py [URL]
"""
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/?lang=pt&ranking=http://127.0.0.1:8740"
CHROME = next(c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c))


def shot(nome, w, h, escala=1, aparar=True):
    destino = RAIZ / "docs" / "screenshots" / f"{nome}.png"
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={w},{h}", f"--force-device-scale-factor={escala}", "--virtual-time-budget=8000",
                    f"--screenshot={destino}", URL], check=True, capture_output=True, timeout=90)
    if aparar:  # corta o céu vazio depois do rodapé
        img = Image.open(destino).convert("RGB")
        px = img.load()
        fim = img.height - 1
        def vazia(y):  # só céu + estrelinhas esparsas
            return sum(1 for x in range(img.width) if not (px[x, y][0] < 70 and px[x, y][2] < 90)) < img.width * 0.01
        while fim > 0 and vazia(fim):
            fim -= 1
        img.crop((0, 0, img.width, min(img.height, fim + 40))).save(destino)
    print(destino)


shot("site_desktop", 1280, 4200)
shot("site_desktop_hero", 1280, 800, aparar=False)
shot("site_mobile", 390, 6400)
shot("site_mobile_hero", 390, 844, escala=2, aparar=False)
