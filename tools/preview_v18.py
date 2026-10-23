"""Prévias da v1.8: roupinhas de época (PNG por roupa + contact sheet) e festas (GIF no app).

Headless: xvfb-run -a python3 tools/preview_v18.py <pasta>
"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
os.environ["HOME"] = tempfile.mkdtemp()
from PIL import Image, ImageDraw

from satoshipet import baleias, config, juice, logic, lore, main, multichain, noticias, onchain, roupas, sprites

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "preview")
OUT.mkdir(parents=True, exist_ok=True)
FOLHAS = RAIZ / "src" / "satoshipet" / "assets" / "sprites"
FUNDO = (34, 32, 52, 255)
DATAS = {"halloween": "2026-10-28", "whitepaper": "2026-10-31", "natal": "2026-12-24", "ano_novo": "2026-12-31",
         "genesis": "2027-01-03", "carnaval": "2027-02-09", "pizza": "2027-05-22", "halving": "bloco 1.050.000"}


def frame(moeda, estagio, rid, escala=6):
    folha = Image.open(FOLHAS / sprites.nome_folha(moeda, "padrao", estagio)).convert("RGBA")
    fr = folha.crop((0, 0, 48, 48))
    fr = juice.aplicar_chapeu(fr, rid) if rid else fr
    base = Image.new("RGBA", (48, 48), FUNDO)
    base.alpha_composite(fr)
    return base.resize((48 * escala, 48 * escala), Image.NEAREST)


# 1) uma PNG por roupa: BTC em todos os estágios + as outras moedas no adulto
for rid in roupas.NOMES:
    linha = [frame("BTC", e, rid, 5) for e in sprites.ESTAGIOS] + [frame(m, "adulto", rid, 5) for m in
                                                                   ("ETH", "SOL", "DOGE", "PEPE")]
    im = Image.new("RGB", (240 * len(linha), 240 + 34), FUNDO[:3])
    for i, f in enumerate(linha):
        im.paste(f, (i * 240, 34))
    ImageDraw.Draw(im).text((10, 8), f"{roupas.NOMES[rid]}  -  {DATAS[rid]}", fill=(255, 205, 117))
    im.save(OUT / f"roupa_{rid}.png")

# 2) contact sheet: linhas = roupas, colunas = estágios BTC + 4 moedas
cols = list(sprites.ESTAGIOS) + ["ETH", "SOL", "DOGE", "PEPE"]
E, C, TOPO, ESQ = 3, 144, 26, 230
sheet = Image.new("RGB", (ESQ + C * len(cols), TOPO + C * (len(roupas.NOMES) + 1)), FUNDO[:3])
d = ImageDraw.Draw(sheet)
for j, c in enumerate(cols):
    d.text((ESQ + j * C + 8, 8), c if c in ("ETH", "SOL", "DOGE", "PEPE") else f"BTC {c}", fill=(148, 176, 194))
for i, rid in enumerate([None] + list(roupas.NOMES)):
    d.text((8, TOPO + i * C + 60), (roupas.NOMES[rid] if rid else "sem roupinha")[:34], fill=(255, 205, 117))
    if rid:
        d.text((8, TOPO + i * C + 76), DATAS[rid], fill=(148, 176, 194))
    for j, c in enumerate(cols):
        moeda, est = (c, "adulto") if c in ("ETH", "SOL", "DOGE", "PEPE") else ("BTC", c)
        sheet.paste(frame(moeda, est, rid, E), (ESQ + j * C, TOPO + i * C))
sheet.save(OUT / "roupas_contact_sheet.png")
print("roupas ok")

# 3) no app de verdade: roupinha na janela + festas
logic.buscar_precos = lambda s, timeout=10: {m: {"BTC": 126500.0}.get(m, 1.0) for m in s}
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
config.salvar = lambda cfg: None
main.SatoshiPet._atualizar_ath = lambda self: None  # sem CoinGecko de verdade na prévia

app = main.SatoshiPet({"sem_tray": True, "mudo": True, "sem_updates": True, "sem_api": True,
                       "sem_onboarding": True, "idioma": "pt"})
app.root.geometry("+40+40")
import random as _r

from satoshipet import genetica

_r.seed(1)
app.cfg["genes"] = genetica.aleatorio(moeda="BTC")  # mesmo DNA das prévias da v1.7
app.cache_sprites.clear()
app._ultimo_calendario = time.time() + 1e9
from satoshipet import evolucao

xp = 0
while evolucao.estagio(xp, app.conq.d["crashes"]) != "adulto":
    xp += 50
app.evo.d["xp"] = xp
app.estagio = "adulto"


def bombear(ms):
    fim = time.time() + ms / 1000
    while time.time() < fim:
        app.root.update()
        time.sleep(0.005)


def quadro():
    app.root.update()
    x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
    tmp = Path(tempfile.mktemp(suffix=".png"))
    subprocess.run(["import", "-window", "root", "-crop", f"{app.LARG}x{app.ALT}+{x}+{y}", "+repage", str(tmp)],
                   check=True)
    im = Image.open(tmp).convert("RGB")
    return im.resize((im.width * 2, im.height * 2), Image.NEAREST)


def gif(nome, n, preparo=None):
    preparo and preparo()
    fr = []
    for _ in range(n):
        bombear(180)
        fr.append(quadro())
    fr[0].save(OUT / f"{nome}.gif", save_all=True, append_images=fr[1:], duration=180, loop=0)
    fr[n // 2].save(OUT / f"{nome}.png")


bombear(1500)
for rid, data in DATAS.items():
    if rid == "halving":
        continue
    os.environ["SATOSHIPET_DATE"] = data
    app.cache_sprites.clear()
    app.toast = None
    gif(f"app_roupa_{rid}", 6)
os.environ.pop("SATOSHIPET_DATE")
app.cache_sprites.clear()

agora = time.time()
for dias, nome in ((7, "festa_1semana"), (30, "festa_1mes"), (100, "festa_100dias"), (365, "festa_1ano")):
    def prep(d=dias):
        app.cfg["nasceu_em"] = agora - d * 86400 - 60
        app.cfg["marcos"] = []
        app.conq.d["desbloqueadas"].clear()
        app.conq.d["desbloqueadas"]["hodl_30d"] = 1  # só a festa no quadro
        app.fx_festa = None
        app._checar_marcos()
    gif(nome, 22, prep)
app.toast = None


def prep_ath():
    app.cfg.update({"ath_btc": 126080.0, "ath_btc_festa": 0})
    app.checar_ath_btc(126080.0, 126500.0)


gif("festa_ath", 22, prep_ath)
app.toast = None
app.cfg["reduzir_movimento"] = True
gif("festa_1ano_reduzir_movimento", 8, lambda: (app.cfg.update({"marcos": [], "nasceu_em": agora - 366 * 86400}),
                                               app.conq.d["desbloqueadas"].clear(), app._checar_marcos()))
print("ok", len(list(OUT.iterdir())), dt.datetime.now())
