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
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RANK_URL = ""
sys.path.insert(0, str(RAIZ / "src"))
os.environ["TAMAGOSHI_CONFIG"] = str(Path(tempfile.mkdtemp()) / "cfg.json")
os.environ.setdefault("TAMAGOSHI_API_PORT", "18737")

import pytest

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


def _gif(app, nome, n=16, ms=180, passo=None):
    """Grava n frames da janela e monta docs/demo/<nome>.gif (só com SHOTS=1)."""
    if not os.environ.get("SHOTS") or not shutil.which("import"):
        for i in range(n):
            passo and passo(i)
            _bombear(app, ms)
        return
    from PIL import Image
    pasta = Path(tempfile.mkdtemp())
    x, y = app.root.winfo_x(), app.root.winfo_y()
    for i in range(n):
        passo and passo(i)
        _bombear(app, ms)
        subprocess.run(["import", "-window", "root", "-crop", f"{app.LARG + 16}x{app.ALT + 16}+{x - 8}+{y - 8}",
                        str(pasta / f"{i:03d}.png")], check=True)
    frames = [Image.open(p).convert("RGB").convert("P", palette=Image.ADAPTIVE) for p in sorted(pasta.glob("*.png"))]
    (RAIZ / "docs" / "demo").mkdir(parents=True, exist_ok=True)
    frames[0].save(RAIZ / "docs" / "demo" / f"{nome}.gif", save_all=True, append_images=frames[1:],
                   duration=ms, loop=0)


def _resetar_extras(app):
    """O _invocar_tudo clica em TUDO: abre jogo/intro, muda escala e opções. Volta pro normal."""
    app.cena = None
    from tamagoshi_cripto import config as _c
    for k in ("alto_contraste", "dia_noite", "chapeus", "juice", "musica", "checar_updates"):
        app.cfg[k] = _c.PADRAO[k]
    app.som.musica(False)
    if app.escala != 3:
        app.mudar_escala(3)


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
    import json
    import time
    import urllib.request
    from tkinter import messagebox, simpledialog

    os.environ["HOME"] = tempfile.mkdtemp()  # card de share cai aqui, não no ~ de verdade
    (Path(os.environ["HOME"]) / "Pictures").mkdir()
    sys.path.insert(0, str(RAIZ / "server"))
    import ranking as servidor_ranking
    srv_rank = servidor_ranking.criar_servidor("127.0.0.1", 0)
    threading.Thread(target=srv_rank.serve_forever, daemon=True).start()
    global RANK_URL
    RANK_URL = f"http://127.0.0.1:{srv_rank.server_address[1]}"
    from tamagoshi_cripto import config, license, logic, lore, main, onchain

    chamadas = []
    messagebox.askyesno = lambda *a, **k: (chamadas.append(("askyesno", a[0])), False)[1]
    messagebox.showinfo = lambda *a, **k: chamadas.append(("showinfo", a[0], a[1]))
    messagebox.showerror = lambda *a, **k: chamadas.append(("showerror", a[0], a[1]))
    floats = iter([3.0, -4.0, 0.0, 50.0, 0.0] * 5)
    simpledialog.askfloat = lambda *a, **k: (chamadas.append(("askfloat", a[1])), next(floats))[1]
    email = "teste@exemplo.com"
    strs = iter([email, "CHAVE-ERRADA", email, license.gerar_chave(email)])
    import webbrowser
    abertos = []
    webbrowser.open = lambda url, *a, **k: abertos.append(url) or True

    def _ask(*a, **k):
        chamadas.append(("askstring", a[1]))
        if a[0].startswith("Ranking"):
            return RANK_URL if "URL" in a[1] else "gui_tester"
        if a[0] != "Ativar Pro":  # carteira watch-only: endereço público, nunca chave
            return "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        return next(strs)
    simpledialog.askstring = _ask
    precos = {"BTC": 100.0, "ETH": 50.0, "SOL": 10.0, "DOGE": 0.1, "PEPE": 0.00001}
    logic.buscar_precos = lambda simbolos, timeout=10: {s: precos[s] for s in simbolos}
    lore.fear_greed = lambda timeout=10: (72, "GANANCIA")
    lore.altura_bloco = lambda timeout=10: 921_337
    from tamagoshi_cripto import baleias as _bal
    from tamagoshi_cripto import multichain as _mc
    from tamagoshi_cripto import noticias as _news
    _bal.recentes = lambda timeout=10: []
    _news.buscar = lambda timeout=10: [{"titulo": "Bitcoin volta aos US$ 100 mil e o bicho comemora", "link":
                                        "https://example.com/noticia", "fonte": "Teste"}]
    _mc._rpc = lambda urls, metodo, params, timeout=10: ({"value": 4_200_000_000} if metodo == "getBalance"
                                                         else hex(15 * 10 ** 17))
    onchain.ultimo_bloco = lambda timeout=10: (921_337, int(time.time()))
    onchain.fees = lambda timeout=10: {"fastestFee": 80, "halfHourFee": 72, "hourFee": 40, "economyFee": 9, "minimumFee": 1}
    onchain.mempool = lambda timeout=10: {"count": 53908, "vsize": 25_160_871}
    onchain.hashrate = lambda timeout=10: 1.03e21
    onchain.gas_eth = lambda timeout=8: 0.42
    onchain.saldo_endereco = lambda e, timeout=10: {"confirmado": 5000, "pendente": 0, "total": 5000, "txs": 3}
    config.INTERVALO = 1

    falhas = []
    app = main.Tamagoshi({"sem_tray": True, "mudo": True, "sem_updates": True})

    # ---------- onboarding (1ª vez): ovo choca, escolhe moeda, batiza, dicas, opt-ins ----------
    from tamagoshi_cripto import cenas
    assert isinstance(app.cena, cenas.Onboarding)
    app.root.geometry("+24+24")
    for _ in range(5):
        app.root.update()
    K = lambda k, ch="": type("E", (), {"keysym": k, "char": ch})()
    _gif(app, "onboarding_ovo", n=40, ms=180)
    _shot(app, "onboarding_ovo")
    app._tecla(K("Return"))
    assert app.cena.passo == "moeda"
    app._tecla(K("Right")); app._tecla(K("Left"))
    _bombear(app, 400)
    _shot(app, "onboarding_moeda")
    app._tecla(K("Return"))
    for ch in "Satoshi Jr":
        app._tecla(K("space" if ch == " " else ch, ch))
    _bombear(app, 300)
    _shot(app, "onboarding_nome")
    app._tecla(K("Return"))
    _shot(app, "onboarding_dicas")
    app._tecla(K("Return"))
    app._tecla(K("s"))  # liga o som (a CLI abriu mudo)
    _shot(app, "onboarding_optins")
    app._tecla(K("Return"))
    assert app.cena is None and app.cfg["onboarding_ok"] and app.cfg["nome_pet"] == "Satoshi Jr"
    assert app.cfg["mudo"] is False and app.nome_pet() == "Satoshi Jr"
    app.cfg["mudo"] = False; app.som.mudo = True  # (os testes seguem mudos)
    # pular também funciona
    app.rever_intro(); app._tecla(K("Escape"))
    assert app.cena is None and app.cfg["nome_pet"] == "Satoshi Jr"
    app.root.geometry("+24+24")
    _bombear(app, 2000)
    assert app.precos.get("BTC") == 100.0, app.precos
    _shot(app, "free")

    # FREE: itens Pro pedem licença e não mudam nada
    falhas += _invocar_tudo(app)
    _resetar_extras(app)
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

    # ---------- on-chain: come bloco novo ----------
    app.console_aberto = False  # o menu "Console" ficou ligado no _invocar_tudo
    app.alternar_sats(False)
    app.eventos.append(("tip", 921_337, int(time.time())))
    app._processar_eventos()
    assert app.estomago.comidos == 0  # 1º tip só calibra
    xp0 = app.evo.xp
    app.eventos.append(("tip", 921_338, int(time.time())))
    app.toast = None
    _gif(app, "comendo", n=14)
    assert app.estomago.comidos == 1 and app.evo.xp > xp0
    assert "genesis" in app.conq.d["desbloqueadas"]
    app.eventos.append(("tip", 921_339, int(time.time())))
    _bombear(app, 600)
    _shot(app, "comendo")
    _bombear(app, 1500)
    app.toast = None
    # fee alta = suando; sem bloco há 31 min = dormindo
    app.fee = 72
    app.estomago.d["ts_bloco"] = time.time() - 31 * 60
    _bombear(app, 400)
    assert app.estomago.dormindo()
    _shot(app, "dormindo")
    app.estomago.d["ts_bloco"] = time.time()

    # ---------- carteira watch-only ----------
    assert "PRIVADA" in app.carteira("xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")[0]
    assert app.carteira("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")[0].startswith("carteira")
    assert "not_your_keys" in app.conq.d["desbloqueadas"]
    app.eventos.append(("saldo", {"total": 5000, "confirmado": 5000, "pendente": 0, "txs": 3}))
    app.eventos.append(("saldo", {"total": 7100, "confirmado": 5000, "pendente": 2100, "txs": 4}))
    app._processar_eventos()
    assert "2.100 sats" in app.frase_atual, app.frase_atual

    # ---------- console hacker ----------
    app.alternar_console()
    app._exige_pro = lambda *a, **k: False  # sem diálogo de licença no meio do console
    esperado = {"help": "comandos", "price": "BTC", "stats": "nível", "mempool": "fees", "halving": "halving",
                "fng": "fear", "hashrate": "EH/s", "gas": "gwei", "wallet": "watch-only", "sats": "unidade",
                "git blame": "Satoshi", "sudo moon": "sudo", "rm -rf /": "blockchain", "skin gato": "skin",
                "coin ETH": "Pro", "neofetch": "Tamagoshi OS", "comando_que_nao_existe": "não encontrado"}
    for cmd, trecho in esperado.items():
        app.console_linhas = []
        antes = 0
        app.executar_console(cmd)
        saida = " ".join(l for l in app.console_linhas[antes:] if isinstance(l, str))
        assert trecho.lower() in saida.lower(), (cmd, saida)
    assert {"sudo", "rm_rf", "moscow"} <= set(app.conq.d["desbloqueadas"])
    del app._exige_pro
    app.alternar_sats(False)
    app.console_linhas = ["Tamagoshi OS - digite 'help'"]
    app.panico_t = 0; app.toast = None
    app.console_aberto = True
    app.executar_console("neofetch")
    _bombear(app, 300)
    _shot(app, "console")
    roteiro = list("price\r") + list("git blame\r") + list("sudo moon\r") + [None] * 8
    def _digita(i):
        ch = roteiro[i]
        if ch == "\r":
            app._tecla_console(type("E", (), {"keysym": "Return", "char": "\r"})())
        elif ch:
            app._tecla_console(type("E", (), {"keysym": "space" if ch == " " else ch, "char": ch})())
    app.console_linhas = ["Tamagoshi OS - digite 'help'"]
    app.console_input = ""
    _gif(app, "console", n=len(roteiro), ms=140, passo=_digita)
    app.console_aberto = True
    # digitação via teclado de verdade (event_generate) + backtick fecha
    app.console_aberto = True
    app.console_input = ""
    for ch in "ping":
        app._tecla_console(type("E", (), {"keysym": ch, "char": ch})())
    app._tecla_console(type("E", (), {"keysym": "Return", "char": "\r"})())
    assert any("pong" in l.lower() for l in app.console_linhas if isinstance(l, str)), app.console_linhas[-3:]
    app._tecla_console(type("E", (), {"keysym": "grave", "char": "`"})())
    assert not app.console_aberto

    # ---------- share card ----------
    linhas = app.compartilhar()
    assert app.ultimo_card.exists() and app.ultimo_card.parent.name == "Pictures"
    from PIL import Image
    assert Image.open(app.ultimo_card).size == (1200, 675)
    assert abertos and abertos[-1].startswith("https://x.com/intent/post?")
    assert any("nada foi postado" in l for l in linhas)

    # ---------- ranking (servidor local de verdade, ponta a ponta) ----------
    assert config.PADRAO["ranking"] is False  # opt-in: desligado por padrão
    app.cfg["ranking"] = False
    app.config_ranking()
    assert app.cfg["ranking"] and app.cfg["nick"] == "gui_tester" and len(app.cfg["device_id"]) == 32
    app.console_linhas = []
    app.ranking([])
    for _ in range(50):
        _bombear(app, 100)
        if any("gui_tester" in l for l in app.console_linhas if isinstance(l, str)):
            break
    assert any("gui_tester" in l for l in app.console_linhas if isinstance(l, str)), app.console_linhas
    top = srv_rank.ranking.top()
    assert top[0]["nick"] == "gui_tester" and "device_id" not in top[0]

    # ---------- mini-game: pega os sats ----------
    xp0 = app.evo.xp
    app._tecla(K("p"))
    jogo = app.cena
    assert isinstance(jogo, cenas.PegaSats)
    jogo.rnd.seed(7)
    def _piloto(i):  # um "jogador" que corre pro sat mais baixo
        sats = [it for it in jogo.itens if it[3] == "sat"]
        if sats:
            alvo = max(sats, key=lambda it: it[1])[0]
            if abs(alvo - jogo.x) > 10:
                jogo.tecla(K("Right" if alvo > jogo.x else "Left"))
    _gif(app, "minigame", n=60, ms=100, passo=_piloto)
    for _ in range(400):
        if jogo.fim is not None:
            break
        _piloto(0)
        jogo.tempo -= 0.3
        _bombear(app, 60)
    assert jogo.fim is not None
    _bombear(app, 200)
    _shot(app, "minigame_fim")
    jogo.tecla(K("Return"))
    _bombear(app, 300)
    assert app.cena is None and app.evo.xp >= xp0 and app.cfg["diversao"] == 100.0

    # ---------- juice + aparência ----------
    app.juice.emitir("moon", app.LARG // 2, app.Y_SPRITE + app.S // 2, app.escala)
    _gif(app, "juice_moon", n=12, ms=120)
    app.juice.emitir("rekt", app.LARG // 2, app.Y_SPRITE + app.S // 2, app.escala)
    _gif(app, "juice_rekt", n=12, ms=120)
    for chave in ("alto_contraste", "dia_noite", "chapeus", "juice", "musica"):
        app.alternar_opcao(chave); _bombear(app, 60); app.alternar_opcao(chave)
    app.cfg["alto_contraste"] = True
    _bombear(app, 200)
    _shot(app, "alto_contraste")
    app.cfg["alto_contraste"] = False
    app.mudar_escala(2); assert app.LARG >= 272 and app.cv.winfo_reqheight() == app.ALT
    app.mudar_escala(3)
    # update: toast clicável abre o Release (nunca instala)
    app.eventos.append(("update", {"versao": "9.9.9", "url": "https://github.com/OWNER/tamagoshi-cripto/releases/tag/v9.9.9"}))
    _bombear(app, 400)
    assert app.toast and app.toast[2] == "NOVA VERSÃO!"
    _shot(app, "update")
    app.inicio_arraste(type("E", (), {"x": 50, "y": 20, "x_root": 0, "y_root": 0})())
    assert abertos[-1].endswith("v9.9.9")
    app.toast = None
    # relatório de erro: só abre a issue preenchida
    messagebox.askyesno = lambda *a, **k: True
    app.enviar_relatorio()
    assert abertos[-1].startswith("https://github.com/OWNER/tamagoshi-cripto/issues/new?")
    messagebox.askyesno = lambda *a, **k: (chamadas.append(("askyesno", a[0])), False)[1]

    # ---------- vim keys ----------
    x_antes = app.root.winfo_x()
    app._tecla(type("E", (), {"keysym": "l", "char": "l"})())
    app.root.update()
    assert app.cfg["posicao"][0] == x_antes + 10
    app.root.geometry("+24+24"); app.root.update()

    # ---------- API local ----------
    st = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{os.environ['TAMAGOSHI_API_PORT']}/status", timeout=3).read())
    assert st["btc"]["comidos"] >= 1 and "nivel" in st and st["btc"]["fome"] == "MORRENDO DE FOME"
    txt = urllib.request.urlopen(f"http://127.0.0.1:{os.environ['TAMAGOSHI_API_PORT']}/status.txt", timeout=3).read().decode()
    assert "LV" in txt
    html = urllib.request.urlopen(f"http://127.0.0.1:{os.environ['TAMAGOSHI_API_PORT']}/overlay", timeout=3).read().decode()
    assert "fetch('/status')" in html

    # ---------- evolução ----------
    app.fee = 3
    app.toast = None
    app.evo.d["xp"] = 1990
    app._ganhar_xp("bloco")
    assert app.estagio == "whale" and "whale_alert" in app.conq.d["desbloqueadas"]
    _gif(app, "evoluindo", n=16)
    _shot(app, "whale")
    app.toast = None

    # Pro: chave errada, depois certa
    app.ativar_pro(); app.ativar_pro()
    assert app.pro and any(c[0] == "showerror" for c in chamadas)
    chamadas.clear()
    falhas += _invocar_tudo(app)
    _resetar_extras(app)
    assert app.cfg["limite_alta"] == 3.0 and app.cfg["limite_queda"] == -4.0
    assert app.cfg["alertas"].get("BTC") == {"acima": 50.0}, app.cfg["alertas"]
    app._checar_alertas()
    assert "BTC" in app.alertados
    assert app.cfg["moeda"] == "PEPE", app.cfg["moeda"]

    # ---------- v1.4 fase 1: genes, cruzamento, batalha, hardcore ----------
    from tamagoshi_cripto import cenas as _cenas
    from tamagoshi_cripto import genetica as _gen
    for w in app.root.winfo_children():
        if w.winfo_class() == "Toplevel":
            w.destroy()
    app.cfg["moeda"], app.cfg["skin"] = "BTC", "padrao"
    app.cfg["chapeus"] = False
    app.cfg["crt"] = False
    app.cfg["genes"] = {"paleta": "gelo", "olhos": "laser", "acessorio": "coroinha", "padrao": "pintas",
                        "moeda": "BTC", "geracao": 1, "id": "cafe0001"}
    app.cache_sprites.clear()
    app.evo.d["xp"] = 900
    app.estagio = "adulto"
    _bombear(app, 400)
    _shot(app, "genes_bicho")
    amigo = {"nome": "Bia", "genes": _gen.aleatorio(9, "BTC"), "nivel": 12, "xp": 1500, "estagio": "adulto"}
    cod = _gen.exportar(amigo)
    out = app.console.executar("breed " + cod)
    assert "estábulo" in out[0] and isinstance(app.cena, _cenas.Cruzamento), out
    _gif(app, "cruzamento", n=26)
    _shot(app, "cruzamento")
    app._tecla(type("E", (), {"keysym": "Return", "char": "\r"})())
    assert app.cena is None and len(app.cfg["estabulo"]) == 1
    assert "Filhote1" in "".join(app.console.executar("stable"))
    assert app.console.executar("petcode")[0].startswith("TAMA1-")
    assert _gen.importar(app.root.clipboard_get())[1] is None  # foi pra área de transferência
    out = app.console.executar("battle " + cod)
    assert isinstance(app.cena, _cenas.Batalha)
    app.cena.auto = True
    v0 = dict(app.cfg["batalhas"])
    _gif(app, "batalha", n=60, passo=lambda i: None)
    for _ in range(3000):  # acelera: tick direto em vez de esperar 180 ms
        if app.cena is None or app.cena.fim:
            break
        app.cena.tick()
    _bombear(app, 200)
    _shot(app, "batalha_fim")
    assert app.cena.fim and sum(app.cfg["batalhas"].values()) == sum(v0.values()) + 1
    app._tecla(type("E", (), {"keysym": "Return", "char": "\r"})())
    assert app.cena is None
    app.console.executar("battle")  # vs IA: começa e sai com ESC
    assert isinstance(app.cena, _cenas.Batalha)
    app._tecla(type("E", (), {"keysym": "Escape", "char": ""})())
    assert app.cena is None
    # hardcore: morre de abandono, vira fantasma, cemitério, renasce do ovo
    app.op["sem_confirmar"] = True
    app.alternar_hardcore()
    assert app.cfg["hardcore"]
    app.conq.d["vida"] = 0
    app.cfg["ultima_interacao"] = time.time() - 5 * 3600
    app.cfg["zero_desde"] = time.time() - 31 * 60
    assert app.checar_hardcore() and app.cfg["fantasma"]
    _bombear(app, 400)
    _shot(app, "fantasma")
    frase = app.carinho()
    assert any(k in frase for k in ("atravessou", "fantasma", "renasce")), frase
    app.ver_cemiterio()
    _gif(app, "cemiterio", n=12)
    _shot(app, "cemiterio")
    app.cena.acao("renascer")
    assert not app.cfg["fantasma"] and app.estagio == "ovo" and app.cfg["cemiterio"]
    app.cena = None
    app.cfg["hardcore"] = False
    app.cfg["chapeus"] = True
    app.cache_sprites.clear()

    # ---------- v1.4 fase 2: paper trading, ETH/SOL, baleia, manchete ----------
    app.cfg["moeda"], app.cfg["crt"] = "BTC", False
    app.cache_sprites.clear()
    for i in range(80):
        app.historico.adicionar("BTC", 100 + 4 * math.sin(i / 7) + i * .1, t=i)
    assert "FICTÍCIO" in app.console.executar("paper")[0]
    app.abrir_corretora()
    assert isinstance(app.cena, _cenas.Corretora)
    app.cena.acao("buy:1000")
    precos["BTC"] = 112.0; app.precos["BTC"] = 112.0
    app.cena.acao("buy:100")
    _bombear(app, 300)
    _shot(app, "paper_trading")
    app.cena.acao("sell:all")
    assert app.cfg["papel"]["usd"] > 10_000 and "lucro" in app.cfg["papel"]["hist"][-1]
    app.cena.acao("sair"); app.cena = None
    assert app.status()["papel"]["aviso"] == "DINHEIRO FICTÍCIO"
    assert "CHAVE PRIVADA" in app.console.executar("wallet eth 0x" + "ab" * 32)[0]
    assert "salva" in app.console.executar("wallet eth 0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe")[0]
    assert "salva" in app.console.executar("wallet sol vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg")[0]
    app.eventos += [("saldo_multi", "eth", 1.5), ("saldo_multi", "sol", 4.2), ("saldo_multi", "sol", 5.0)]
    app._processar_eventos()
    assert app.saldos_multi == {"eth": 1.5, "sol": 5.0} and "SOL" in app.toast[2]
    app.toast = None
    app.manchetes = _news.buscar()
    app._desenhar()  # estabiliza o humor (troca de humor sorteia frase nova)
    import random as _rnd
    _r0 = _rnd.random
    _rnd.random = lambda: 0.0
    app._nova_frase()
    _rnd.random = _r0
    assert app.frase_atual.startswith("NEWS:") and app.link_balao
    app._desenhar()
    _shot(app, "noticia")
    n_ab = len(abertos)
    app.inicio_arraste(type("E", (), {"x": 100, "y": 20, "x_root": 0, "y_root": 0})())
    assert abertos[n_ab:] == ["https://example.com/noticia"]
    app.fim_arraste(type("E", (), {"x": 100, "y": 20, "x_root": 0, "y_root": 0})())
    app._press = None
    app.eventos.append(("baleia", {"txid": "f" * 64, "btc": 1234.5, "url": "https://mempool.space/tx/" + "f" * 64}))
    app._processar_eventos()
    assert app.toast[2] == "ALERTA DE BALEIA" and app.panico_t
    _gif(app, "baleia", n=12)
    _shot(app, "baleia")
    app.toast = None; app.link_balao = None
    app.cfg["carteira_eth"] = app.cfg["carteira_sol"] = ""
    app.saldos_multi.clear()

    # ---------- v1.4 fase 3: export, card, ask (IA off), máscara da chave ----------
    out = app.console.executar("export")
    arq = Path(out[0].split(": ", 1)[1])
    assert "carteira" not in json.loads(arq.read_text())
    assert app.console.executar("card")[0].startswith("card:")
    svg = urllib.request.urlopen(f"http://127.0.0.1:{os.environ['TAMAGOSHI_API_PORT']}/card.svg", timeout=3).read()
    assert svg.startswith(b"<svg")
    from tamagoshi_cripto import ai as _ai
    assert app.console.executar("ask vai subir?")[0]
    app.executar_console("ai set https://api.exemplo.com/v1 sk-SEGREDO modelo-x")
    assert not any("sk-SEGREDO" in l for l in app.console_linhas) and app.cfg["ai_key"] == "sk-SEGREDO"
    _ai_orig = _ai.perguntar
    _ai.perguntar = lambda p, cfg, ctx=None, timeout=25: "HODL, fren (IA de mentira)"
    app.executar_console("ask e agora?")
    for _ in range(50):
        _bombear(app, 20)
        app._processar_eventos()
        if any("IA de mentira" in l for l in app.console_linhas):
            break
    _ai.perguntar = _ai_orig
    assert any("IA de mentira" in l for l in app.console_linhas)
    app.executar_console("ai off")
    assert not app.cfg["ai_url"] and not app.cfg["ai_key"]
    app.console_aberto = False

    # ---------- v1.4 fase 4: loja, pacote de marca, overlay de streamer ----------
    from tamagoshi_cripto import loja as _loja
    app.abrir_loja()
    assert isinstance(app.cena, _cenas.Loja) and app.cena.ids
    app.cena.i = app.cena.ids.index("neon_nights")
    _bombear(app, 300)
    _shot(app, "loja_trancada")
    assert "inválido" in app.console.executar("redeem SKIN-NEON_NIGHTS-000000000000")[0]
    assert "destravado" in app.console.executar("redeem " + _loja.gerar_codigo("neon_nights", "*"))[0]
    app.cena.acao("usar")
    assert app.cfg["skin"] == "loja:neon_nights"
    _gif(app, "loja", n=10, passo=lambda i: app.cena and app.cena.acao("prox" if i < 5 else "ant"))
    app.cena.i = app.cena.ids.index("neon_nights")
    _bombear(app, 200)
    _shot(app, "loja")
    app.cena.acao("sair"); app.cena = None
    assert "loja:cafe_satoshi" in app.console.executar("skin loja:cafe_satoshi")[0]
    app.toast = None
    _bombear(app, 400)
    _shot(app, "skin_patrocinada")
    assert app.status()["patrocinado"] is True
    porta = os.environ["TAMAGOSHI_API_PORT"]
    html_s = urllib.request.urlopen(f"http://127.0.0.1:{porta}/stream", timeout=3).read().decode()
    assert "PATROCINADO" in html_s and "/sprite.png" in html_s
    png_s = urllib.request.urlopen(f"http://127.0.0.1:{porta}/sprite.png", timeout=3).read()
    assert png_s[:8] == b"\x89PNG\r\n\x1a\n"
    app.cfg["skin"] = "padrao"; app.cache_sprites.clear()
    app.eventos.append(("twitch", "viewer42", "!moon"))
    app._processar_eventos()
    assert app.stream["ultimo"] == "viewer42: !moon" and app.estado_forcado[0] == "moon"
    assert not app.evento_twitch("spammer", "!rekt")  # cooldown
    assert "spammer: !rekt" in app.status()["stream"]["chat"]
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if os.environ.get("SHOTS") and chrome:
        app.frase_atual = "valeu pelo !moon, viewer42!"
        subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=29366fff", "--window-size=600,400", "--virtual-time-budget=4000",
                        f"--screenshot={SHOTS / 'stream_overlay.png'}", f"http://127.0.0.1:{porta}/stream"],
                       capture_output=True, timeout=60)

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
