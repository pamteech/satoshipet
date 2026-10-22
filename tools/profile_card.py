#!/usr/bin/env python3
"""profile_card.py - gera o card de perfil (SVG animado / PNG) pro README do GitHub.

Uso:
  python tools/profile_card.py --stats tamagoshi-stats.json -o card.svg
  python tools/profile_card.py --url http://127.0.0.1:8737/status -o card.svg   # app rodando
  python tools/profile_card.py --petcode TAMA1-... -o card.png
O stats.json sai do console do app: `export` (só campos públicos: nada de carteira/e-mail/licença).
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tamagoshi_cripto import cartao


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--stats", help="JSON exportado pelo app (console: export)")
    g.add_argument("--url", help="URL do /status da API local")
    g.add_argument("--petcode", help="código TAMA1-...")
    ap.add_argument("-o", "--saida", default="tamagoshi-card.svg", help=".svg (animado) ou .png")
    a = ap.parse_args(argv)
    if a.stats:
        s = cartao.carregar(a.stats)
    elif a.url:
        s = cartao.exportar_stats(json.loads(urllib.request.urlopen(a.url, timeout=5).read()))
    else:
        s = cartao.de_petcode(a.petcode)
    out = Path(a.saida)
    if out.suffix.lower() == ".png":
        cartao.png(s).save(out)
    else:
        out.write_text(cartao.svg(s), encoding="utf-8")
    print(f"card salvo: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
