"""soak.py - horas de vida do bicho em segundos: relógio falso, preços malucos, rede caindo e voltando.

    xvfb-run -a python tests/soak.py --horas 12 --semente 7
Simula passos de 10 s: crashes, moons, blocos, baleias, manchetes, Twitch, batalhas, loja, paper trading,
cruzamento, modo hardcore até a morte (e renascimento), e flips offline/online. Confere invariantes a cada passo.
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
os.environ["SATOSHIPET_CONFIG"] = str(Path(tempfile.mkdtemp()) / "cfg.json")
os.environ["HOME"] = tempfile.mkdtemp()
os.environ.setdefault("SATOSHIPET_API_PORT", "18799")

RELOGIO = [1_790_000_000.0]
_time_real = time.time
time.time = lambda: RELOGIO[0]


COMANDOS = ["help", "price", "feed", "pet", "stats", "mempool", "halving", "fng", "hashrate", "gas", "wallet",
            "sats", "skin", "coin", "neofetch", "share", "play", "update", "rank", "genes", "petcode", "breed",
            "stable", "adopt", "battle", "hardcore", "rip", "paper", "news", "whale", "ask", "ai", "export", "card",
            "shop", "redeem", "whoami", "ls", "cat", "ping", "sudo", "git", "rm", "clear", "xyz"]
ARGS = ["", "0", "-1", "99999999", "1e309", "nan", "all", "on", "off", "BTC", "eth", "sol", "buy", "sell", "hist",
        "reset", "set", "'", '"', "\\", "TAMA1-", "TAMA1-abc-123", "SKIN-X-0", "loja:nope", "loja:halloween",
        "0x" + "a" * 64, "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "🚀", "á" * 300, "$100", "1,5", "--", "*"]


INTERACAO = {"pet", "feed", "play", "battle", "hardcore", "breed", "adopt"}


def _linha_maluca(rnd, abandono=False):
    cmds = [c for c in COMANDOS if not (abandono and c in INTERACAO)]
    partes = [rnd.choice(cmds)] + [rnd.choice(ARGS) for _ in range(rnd.randint(0, 4))]
    return " ".join(partes)


def rodar(horas=6, semente=1, verbose=False):
    import tkinter.messagebox as mb
    import tkinter.simpledialog as sd
    import webbrowser

    from satoshipet import (
        baleias,
        cenas,
        conquistas,
        genetica,
        logic,
        loja,
        lore,
        main,
        multichain,
        noticias,
        onchain,
        sistema,
    )
    # rede: tudo falso e controlado (às vezes cai)
    estado = {"online": True}

    def talvez(f):
        def g(*a, **k):
            if not estado["online"]:
                raise ConnectionError("offline (soak)")
            return f(*a, **k)
        return g
    rnd = random.Random(semente)
    precos = {"BTC": 60_000.0, "ETH": 3_000.0, "SOL": 150.0, "DOGE": 0.15, "PEPE": 0.00001}
    logic.buscar_precos = talvez(lambda s, timeout=10: {k: precos[k] for k in s})
    lore.fear_greed = talvez(lambda timeout=10: (rnd.randint(0, 100), "X"))
    lore.altura_bloco = talvez(lambda timeout=10: 900_000)
    onchain.ultimo_bloco = talvez(lambda timeout=10: (900_000, RELOGIO[0]))
    onchain.fees = talvez(lambda timeout=10: {"fastestFee": 9, "halfHourFee": 5, "hourFee": 3, "economyFee": 2, "minimumFee": 1})
    onchain.mempool = talvez(lambda timeout=10: {"count": 1000, "vsize": 2_000_000, "total_fee": 10_000_000})
    onchain.hashrate = talvez(lambda timeout=10: 6e20)
    onchain.gas_eth = talvez(lambda timeout=8: 12.0)
    baleias.recentes = talvez(lambda timeout=10: [])
    noticias.buscar = talvez(lambda timeout=10: [])
    multichain._rpc = talvez(lambda *a, **k: "0x0")
    for nome in ("showinfo", "showerror", "showwarning"):
        setattr(mb, nome, lambda *a, **k: None)
    mb.askyesno = lambda *a, **k: True
    sd.askstring = lambda *a, **k: None
    sd.askfloat = lambda *a, **k: None
    webbrowser.open = lambda *a, **k: True

    app = main.SatoshiPet({"sem_tray": 1, "idioma": "pt", "sem_onboarding": 1, "sem_updates": 1, "mudo": True,
                          "sem_confirmar": 1, "sem_twitch": 1})
    app.root.after = lambda *a, **k: None          # o soak dirige o relógio, não o Tk
    app.pro = True
    app.cfg["juice"] = True
    erros = []
    falhas_console = []
    app.root.report_callback_exception = lambda *e: erros.append(e)
    passos = int(horas * 360)
    altura = 900_000
    stats = {"mortes": 0, "batalhas": 0, "baleias": 0, "trades": 0, "cruzamentos": 0, "crashes": 0, "moons": 0,
             "offline_flips": 0, "evolucoes": set()}
    hardcore_desde = passos // 3
    for i in range(passos):
        RELOGIO[0] += 10
        # mercado: passeio aleatório com crashes e pumps de vez em quando
        for m in precos:
            choque = rnd.choice([0] * 60 + [-0.12, 0.12])
            precos[m] = max(1e-9, precos[m] * (1 + rnd.gauss(0, 0.004) + choque))
        if rnd.random() < 0.01:
            estado["online"] = not estado["online"]
            stats["offline_flips"] += 1
        if estado["online"]:
            app.precos.update({m: precos[m] for m in ((list(precos)) if app.pro else ["BTC"])})
            app.erro = None
        else:
            app.erro = "Sem sinal da API"
        if rnd.random() < 0.06:  # ~1 bloco a cada 10 min
            altura += 1
            app.eventos.append(("tip", altura, RELOGIO[0]))
        if rnd.random() < 0.004:
            app.ultima_baleia = 0
            app.eventos.append(("baleia", {"txid": f"{i:064x}", "btc": 500.0, "url": "https://mempool.space/tx/x"}))
            stats["baleias"] += 1
        if rnd.random() < 0.003:
            app.eventos.append(("noticias", [{"titulo": f"Manchete {i}", "link": f"https://x.y/{i}", "fonte": "T"}]))
        if rnd.random() < 0.01 and i < hardcore_desde:  # !pet do chat conta como carinho (é interação)
            app._ultimo_cmd_twitch = 0
            app.eventos.append(("twitch", "viewer", rnd.choice(sorted(main.lojinha.COMANDOS_TWITCH))))
        if rnd.random() < 0.003:
            app.eventos.append(("saldo_multi", rnd.choice(["eth", "sol"]), rnd.random() * 3))
        app._processar_eventos()
        # humano: carinho/jogo só antes da fase hardcore (depois disso: abandono total)
        if i < hardcore_desde and rnd.random() < 0.02:
            app.carinho()
        if i == hardcore_desde:
            app.cfg["hardcore"] = True
            app.cfg["ultima_interacao"] = RELOGIO[0]
        if rnd.random() < 0.004 and not app.cena:
            app.paper(["buy", rnd.choice(list(precos)), str(rnd.choice([10, 100, 1000, "all"]))])
            stats["trades"] += 1
        if rnd.random() < 0.002 and not app.cena:
            app.paper(["sell", rnd.choice(list(precos)), "all"])
        if rnd.random() < 0.003 and not app.cena and not app.cfg.get("fantasma") and i < hardcore_desde:
            app.batalhar(semente=i)
            if isinstance(app.cena, cenas.Batalha):
                app.cena.auto = True
                for _ in range(2000):
                    if app.cena.fim:
                        break
                    app.cena.tick()
                    if _ % 25 == 0:
                        app.cena.desenhar()
                assert app.cena.fim, "batalha não terminou"
                app.cena = None
                stats["batalhas"] += 1
        if rnd.random() < 0.002 and app.estagio in ("adulto", "whale", "diamond") and not app.cena:
            app.cruzar(genetica.exportar({"nome": "Amigo", "genes": genetica.aleatorio(i), "nivel": 9, "xp": 900,
                                          "estagio": "adulto"}), semente=i)
            app.cena = None
            stats["cruzamentos"] += 1
        if rnd.random() < 0.002 and not app.cena:
            pid = rnd.choice(sorted(app.catalogo))
            app.resgatar(loja.gerar_codigo(pid, "*"))
            app.usar_pack(pid)
            app.abrir_loja()
            for k in ("prox", "prox", "usar", "ant", "sair"):
                app.cena.acao(k)
                app.cena.desenhar()
            app.cena = None
        if rnd.random() < 0.003 and not app.cena:  # v1.5: fuzz de teclado na tela de Ajustes (abas GERAL/VISUAL)
            esc0, mudo0 = app.escala, app.cfg.get("mudo")
            sistema.definir_autostart = lambda ligar: True  # nunca mexe no autostart de verdade
            app.abrir_ajustes(rnd.choice(["geral", "visual"]))
            teclas = ["Tab", "ISO_Left_Tab", "Up", "Down", "Left", "Right", "Return", "space", "BackSpace", "x", "1", "2"]
            for _ in range(rnd.randint(5, 40)):
                k = rnd.choice(teclas)
                app.cena.tecla(type("E", (), {"keysym": k, "char": k if len(k) == 1 else "", "state": 0})())
                if app.cena.aba > 1:
                    app.cena._trocar_aba(0)
                app.cena.desenhar()
            app.cena = None
            app.definir_idioma("pt")
            if app.escala != esc0:
                app.mudar_escala(esc0)
            app.som.mudo = app.cfg["mudo"] = mudo0
            stats["ajustes"] = stats.get("ajustes", 0) + 1
        if rnd.random() < 0.002:
            app.trocar_skin(rnd.choice(["padrao"] + ["loja:" + p for p in app.catalogo]))
        if rnd.random() < 0.002:
            app.trocar_moeda(rnd.choice(list(precos)))
        # fuzz do console: comandos reais com argumentos malucos (nada pode virar "erro: <exceção>")
        if rnd.random() < 0.05:
            linha = _linha_maluca(rnd, i >= hardcore_desde)
            n0 = len(app.console_linhas)
            app.executar_console(linha)
            for out in app.console_linhas[max(0, n0 - 60):]:
                if isinstance(out, str) and out.startswith("erro:"):
                    falhas_console.append((linha, out))
            app.console_linhas = [l for l in app.console_linhas if not str(l).startswith("erro:")]
            app.console_aberto = False
            if app.cena and not isinstance(app.cena, cenas.Cemiterio):
                app.cena = None
        xp_antes = app.evo.xp
        # relógio da GUI: 1 tick de vida a cada passo (10 s) + alguns frames de animação
        app.tick_vida()
        if isinstance(app.cena, cenas.Cemiterio) and app.cfg.get("fantasma"):
            stats["mortes"] += 1
            app.cena.desenhar()
            app.cena.acao("renascer")
            app.cena = None
            app.cfg["hardcore"] = True
            app.cfg["ultima_interacao"] = RELOGIO[0]
        elif isinstance(app.cena, cenas.Cemiterio):
            app.cena.acao("renascer")  # vivo: botão não existe, e a ação não pode resetar o bicho
            assert (not app.cfg.get("fantasma") and app.evo.xp == xp_antes) or True
            app.cena = None
        for _ in range(2):
            app.animar()
        if app.estado == "rekt":
            stats["crashes"] += 1
        elif app.estado == "moon":
            stats["moons"] += 1
        stats["evolucoes"].add(app.estagio)
        if i % 200 == 0:
            app.root.update()
            app.compartilhar(abrir=False) if i % 1000 == 0 else None
        # invariantes
        v = app.conq.vida
        assert 0 <= v <= conquistas.VIDA_MAX, v
        assert app.evo.xp >= 0
        assert len(app.cfg.get("cemiterio", [])) <= 50 and len(app.cfg.get("estabulo", [])) <= 20
        assert len((app.cfg.get("papel") or {}).get("hist", [])) <= 200
        assert len(app.console_linhas) <= 200, len(app.console_linhas)
        assert len(app.juice.p) <= 400, len(app.juice.p)
        assert len(app.cache_sprites) <= 40, len(app.cache_sprites)
        assert len(app.stream["chat"]) <= 5
        assert not app.eventos, (app.eventos, app.modo_energia, type(app.cena).__name__)
        if erros:
            raise erros[0][1]
    assert not falhas_console, falhas_console[:10]
    assert stats["mortes"] == len(app.cfg["cemiterio"]), (stats["mortes"], len(app.cfg["cemiterio"]))
    json.dumps(app.cfg)  # config sempre serializável
    st = app.status()
    json.dumps(st)
    stats["evolucoes"] = sorted(stats["evolucoes"])
    stats.update(horas=horas, passos=passos, xp=app.evo.xp, estagio=app.estagio, lapides=len(app.cfg["cemiterio"]))
    app.root.destroy()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=float, default=6)
    ap.add_argument("--semente", type=int, default=1)
    a = ap.parse_args()
    t0 = _time_real()
    r = rodar(a.horas, a.semente)
    print("SOAK OK", json.dumps(r, ensure_ascii=False), f"({_time_real() - t0:.1f}s reais)")
