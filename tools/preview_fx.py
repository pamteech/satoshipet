"""Gera prévias (GIF/PNG) das animações v1.6 em modo headless: xvfb-run -a python tools/preview_fx.py <pasta>"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
os.environ["HOME"] = tempfile.mkdtemp()
from PIL import Image

from tamagoshi_cripto import baleias, config, logic, lore, main, multichain, noticias, onchain

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "preview")
OUT.mkdir(parents=True, exist_ok=True)
logic.buscar_precos = lambda s, timeout=10: {m: {"BTC": 81320.0}.get(m, 1.0) for m in s}
lore.fear_greed = lambda timeout=10: (72, "GANANCIA")
lore.altura_bloco = lambda timeout=10: 921_337
baleias.recentes = lambda timeout=10: []
noticias.buscar = lambda timeout=10: []
multichain._rpc = lambda *a, **k: hex(0)
onchain.ultimo_bloco = lambda timeout=10: (921_337, int(time.time()))
onchain.fees = lambda timeout=10: {"halfHourFee": 12, "fastestFee": 20, "hourFee": 8, "economyFee": 2, "minimumFee": 1}
onchain.hashrate = lambda timeout=10: 1.035e21
onchain.gas_eth = lambda timeout=8: 0.4
config.INTERVALO = 1

app = main.Tamagoshi({"sem_tray": True, "mudo": True, "sem_updates": True, "sem_api": True,
                      "sem_onboarding": True, "idioma": "pt"})
app.cfg["chapeus"] = False
app.root.geometry("+40+40")


def bombear(ms):
    fim = time.time() + ms / 1000
    while time.time() < fim:
        app.root.update()
        time.sleep(0.005)


def quadro():
    app.root.update()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    tmp = Path(tempfile.mktemp(suffix=".png"))
    subprocess.run(["import", "-window", "root", "-crop", f"{app.LARG}x{app.ALT}+{x}+{y}", "+repage", str(tmp)], check=True)
    im = Image.open(tmp).convert("RGB")
    return im.resize((im.width * 2, im.height * 2), Image.NEAREST)


def gif(nome, n, preparo=None, passo=None):
    preparo and preparo()
    fr = []
    for i in range(n):
        passo and passo(i)
        bombear(180)
        fr.append(quadro())
    fr[0].save(OUT / f"{nome}.gif", save_all=True, append_images=fr[1:], duration=180, loop=0)
    for i in (0, n // 3, n // 2, (2 * n) // 3, n - 1):
        fr[i].save(OUT / f"{nome}_{i:02d}.png")


from tamagoshi_cripto import evolucao

xp = 0
while evolucao.estagio(xp, app.conq.d["crashes"]) != "adulto":
    xp += 50
app.evo.d["xp"] = xp
app.estagio = "adulto"
bombear(1500)
app.cache_sprites.clear()
gif("evolucao", 28, lambda: (setattr(app, "estagio", "adulto"), app.iniciar_evolucao("bebe", "adulto")))
gif("transicao_dissolve", 8, lambda: app.transicao("dissolve", 6))
gif("transicao_wipe", 8, lambda: app.transicao("wipe", 6))
gif("transicao_mosaico", 8, lambda: app.transicao("mosaico", 6))
gif("idle_olha_mouse", 24, passo=lambda i: setattr(app, "mouse", ((0, 200), (app.LARG, 200), (app.LARG // 2, 0))[i // 8]))
z = app._zonas()["info"]
gif("dica_hover", 8, lambda: (setattr(app, "rodizio", 22 * 1),
                               app._mouse_move(type("E", (), {"x": (z[0] + z[2]) // 2, "y": (z[1] + z[3]) // 2})())))
app._mouse_sai()
gif("ajustes_transicao", 10, lambda: app.abrir_ajustes())
print("ok", sorted(p.name for p in OUT.iterdir()))
