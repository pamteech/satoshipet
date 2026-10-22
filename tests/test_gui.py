"""test_gui.py - aperta TODOS os itens do menu e diálogos sem humano (Linux: xvfb-run).

    xvfb-run -a python tests/test_gui.py            # só testa
    SHOTS=1 xvfb-run -a python tests/test_gui.py    # + screenshots em docs/screenshots/
Também roda via pytest (pulado se não houver display).
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
os.environ["TAMAGOSHI_CONFIG"] = str(Path(tempfile.mkdtemp()) / "cfg.json")

import pytest  # noqa: E402

SHOTS = RAIZ / "docs" / "screenshots"


def _shot(app, nome):
    if not os.environ.get("SHOTS") or not shutil.which("import"):
        return
    for _ in range(3):
        app.root.update()
    tmp = Path(tempfile.gettempdir()) / f"{nome}.png"
    subprocess.run(["import", "-window", "root", str(tmp)], check=True)
    x, y = app.root.winfo_x(), app.root.winfo_y()
    SHOTS.mkdir(parents=True, exist_ok=True)
    subprocess.run(["convert", str(tmp), "-crop", f"{app.LARG + 16}x{app.ALT + 16}+{x - 8}+{y - 8}",
                    "+repage", "-background", "#1a1c2c", "-flatten", str(SHOTS / f"{nome}.png")], check=True)


def _bombear(app, ms):
    fim = [False]
    app.root.after(ms, lambda: fim.__setitem__(0, True))
    while not fim[0]:
        app.root.update()


def _invocar_tudo(app):
    erros = []
    for menu in (app.menu, app.menu_moedas, app.menu_skins):
        for i in range(menu.index("end") + 1):
            if menu.type(i) in ("command", "checkbutton") and menu.entrycget(i, "state") != "disabled":
                rotulo = menu.entrycget(i, "label")
                if rotulo == "Sair":
                    continue
                try:
                    menu.invoke(i)
                    _bombear(app, 40)
                except Exception as e:
                    erros.append((rotulo, repr(e)))
    return erros


def executar():
    from tkinter import messagebox, simpledialog

    from tamagoshi_cripto import config, license, logic, lore, main

    chamadas = []
    messagebox.askyesno = lambda *a, **k: (chamadas.append(("askyesno", a[0])), False)[1]
    messagebox.showinfo = lambda *a, **k: chamadas.append(("showinfo", a[0], a[1]))
    messagebox.showerror = lambda *a, **k: chamadas.append(("showerror", a[0], a[1]))
    floats = iter([3.0, -4.0, 0.0, 50.0, 0.0] * 5)
    simpledialog.askfloat = lambda *a, **k: (chamadas.append(("askfloat", a[1])), next(floats))[1]
    email = "teste@exemplo.com"
    strs = iter([email, "CHAVE-ERRADA", email, license.gerar_chave(email)])
    simpledialog.askstring = lambda *a, **k: (chamadas.append(("askstring", a[1])), next(strs))[1]
    precos = {"BTC": 100.0, "ETH": 50.0, "SOL": 10.0, "DOGE": 0.1, "PEPE": 0.00001}
    logic.buscar_precos = lambda simbolos, timeout=10: {s: precos[s] for s in simbolos}
    lore.fear_greed = lambda timeout=10: (72, "GANANCIA")
    lore.altura_bloco = lambda timeout=10: 921_337
    config.INTERVALO = 1

    falhas = []
    app = main.Tamagoshi({"sem_tray": True, "mudo": True})
    app.root.geometry("+24+24")
    _bombear(app, 2000)
    assert app.precos.get("BTC") == 100.0, app.precos
    _shot(app, "free")

    # FREE: itens Pro pedem licença e não mudam nada
    falhas += _invocar_tudo(app)
    assert app.cfg["moeda"] == "BTC" and app.cfg["skin"] in ("padrao", "plugin:slime"), app.cfg["skin"]
    assert any(c[0] == "askyesno" for c in chamadas), "Free não pediu licença"
    assert any(c[0] == "showinfo" and c[1] == "Conquistas" for c in chamadas)
    app.cfg["skin"] = "padrao"; app.var_crt.set(False); app.alternar_crt()

    # carinho (clique sem arrastar no bicho) -> pulo com squash & stretch
    x0, y0, x1, y1 = app.SPRITE_BOX
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    vida0 = app.conq.vida
    for _ in range(4):  # 5º clique no BTC revela o halving
        app.cv.event_generate("<ButtonPress-1>", x=cx, y=cy, rootx=cx + 24, rooty=cy + 24)
        app.cv.event_generate("<ButtonRelease-1>", x=cx, y=cy, rootx=cx + 24, rooty=cy + 24)
    app.cv.event_generate("<ButtonPress-1>", x=cx, y=cy, rootx=cx + 24, rooty=cy + 24)
    app.cv.event_generate("<ButtonRelease-1>", x=cx, y=cy, rootx=cx + 24, rooty=cy + 24)
    assert app.conq.vida > vida0 and app.reacao > 0
    assert "halving" in app.frase_atual, app.frase_atual
    app.toast = None
    _bombear(app, 400)
    _shot(app, "reacao")
    _bombear(app, 1500)

    # konami -> skin secreta Satoshi
    for k in ["Up", "Up", "Down", "Down", "Left", "Right", "Left", "Right", "b", "a"]:
        app.konami.alimentar(k) and app.revelar_satoshi()
    assert app.cfg["skin"] == "satoshi" and "konami" in app.conq.d["desbloqueadas"]
    _bombear(app, 300)
    _shot(app, "konami")
    app.toast = None
    app.trocar_skin("padrao")

    # conquista + toast
    for _ in range(10):
        app.carinho()
    _bombear(app, 200)
    assert "carinho_10" in app.conq.d["desbloqueadas"] and app.toast
    app.reacao = 0
    _shot(app, "conquista")
    app.toast = None

    # Pro: chave errada, depois certa
    app.ativar_pro(); app.ativar_pro()
    assert app.pro and any(c[0] == "showerror" for c in chamadas)
    chamadas.clear()
    falhas += _invocar_tudo(app)
    assert app.cfg["limite_alta"] == 3.0 and app.cfg["limite_queda"] == -4.0
    assert app.cfg["alertas"].get("BTC") == {"acima": 50.0}, app.cfg["alertas"]
    app._checar_alertas()
    assert "BTC" in app.alertados
    assert app.cfg["moeda"] == "PEPE", app.cfg["moeda"]

    # foto Pro: ETH cyberpunk em TO THE MOON com sparkline
    for w in app.root.winfo_children():
        if w.winfo_class() == "Toplevel":
            w.destroy()
    app.cfg["moeda"], app.cfg["skin"] = "ETH", "cyberpunk"
    for i in range(120):
        app.historico.adicionar("ETH", 50 + 3 * math.sin(i / 9) + i * 0.05, t=i)
    precos["ETH"] = 53.0
    app.precos["ETH"] = 53.0
    app._refs_sessao["ETH"] = 50.0
    _bombear(app, 800)
    _shot(app, "pro")
    # CRT liga/desliga
    app.var_crt.set(True); app.alternar_crt()
    app.cfg["moeda"], app.cfg["skin"] = "PEPE", "padrao"
    precos["PEPE"] = 0.0000095; app.precos["PEPE"] = 0.0000095; app._refs_sessao["PEPE"] = 0.00001
    _bombear(app, 800)
    _shot(app, "crt_rekt")
    if app.ultimo_erro:
        falhas.append(("callback", app.ultimo_erro))
    app.sair()
    return falhas, len(chamadas)


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="precisa de display (use xvfb-run)")
def test_gui_completo():
    falhas, _ = executar()
    assert not falhas, falhas


if __name__ == "__main__":
    falhas, n = executar()
    if falhas:
        print("FALHAS:", falhas)
        sys.exit(1)
    print("GUI OK - menus/diálogos exercitados;", n, "chamadas no modo Pro")
