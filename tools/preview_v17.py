"""Gera prévias (GIF/PNG) da v1.7 (clima, eventos, conquistas, amigos, fonte grande) em modo headless: xvfb-run -a python tools/preview_fx.py <pasta>"""
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
import random as _r

from tamagoshi_cripto import genetica

_r.seed(1)
app.cfg["genes"] = genetica.aleatorio(moeda="BTC")
print("genes", app.cfg["genes"])
app.cfg["chapeus"] = True
app.cache_sprites.clear()
import datetime as _dt

from tamagoshi_cripto import evolucao

xp = 0
while evolucao.estagio(xp, app.conq.d["crashes"]) != "adulto":
    xp += 50
app.evo.d["xp"] = xp
app.estagio = "adulto"
app._ultimo_calendario = time.time() + 1e9  # o calendário real não interfere
bombear(1500)
for tipo, dia, nome in (("chuva", True, "clima_chuva"), ("sol", True, "clima_sol"), ("neve", True, "clima_neve"),
                        ("neblina", True, "clima_neblina"), ("tempestade", True, "clima_tempestade"),
                        (None, False, "clima_noite")):
    gif(nome, 12, lambda t=tipo, d=dia: setattr(app, "clima_dado", {"tipo": t, "dia": d, "temp": 21.0}))
app.clima_dado = None
for dia, nome in ((_dt.date(2027, 5, 22), "evento_pizza"), (_dt.date(2026, 10, 31), "evento_whitepaper"),
                  (_dt.date(2027, 2, 7), "evento_carnaval")):
    gif(nome, 10, lambda d=dia: app._checar_calendario(d))
app.evento = None
app.cache_sprites.clear()
app.toast = None
gif("conquista_medo_extremo", 10, lambda: app._comemorar(app.conq.especial("medo_extremo")))
app.toast = None
gif("conquista_ath", 8, lambda: app._comemorar(app.conq.especial("ath_vivo")))
app.toast = None
gif("amigo_visita", 40, lambda: app.iniciar_visita({"id": "00000001", "nome": "Vitalik", "moeda": "ETH",
                                                    "skin": "padrao", "humor": "moon", "emote": "wagmi"}, lado=1))
app.visita = None
app.cfg["fonte_grande"] = True
app.mudar_escala(app.escala)
app.root.geometry("+40+40")
gif("fonte_grande", 6)
z = app._zonas()["vida"]
gif("fonte_grande_dica", 6, lambda: app._mouse_move(type("E", (), {"x": (z[0] + z[2]) // 2, "y": (z[1] + z[3]) // 2})()))
app.cfg["fonte_grande"] = False
print("ok", len(list(OUT.iterdir())))
