"""tui.py - o bicho no terminal. Cada caractere ▀ mostra 2 pixels (cor de cima no texto,
cor de baixo no fundo), em truecolor. Sai com q ou Ctrl+C.

No modo terminal todas as moedas e skins embutidas ficam liberadas: é o presente pros devs.
"""
import os
import shutil
import sys
import threading
import time

from PIL import Image

from . import arts, config, conquistas, evolucao, logic, onchain, plugins, ranking, recursos, share
from .console import SPRITE, Console
from .sprites import FRAMES, LINHAS

RESET = "\x1b[0m"


def _bloco(cima, baixo):
    """Converte 2 pixels RGBA em 1 célula ANSI (com transparência)."""
    if cima[3] < 128 and baixo[3] < 128:
        return RESET + " "
    if cima[3] < 128:
        return f"{RESET}\x1b[38;2;{baixo[0]};{baixo[1]};{baixo[2]}m▄"
    if baixo[3] < 128:
        return f"{RESET}\x1b[38;2;{cima[0]};{cima[1]};{cima[2]}m▀"
    return f"\x1b[38;2;{cima[0]};{cima[1]};{cima[2]};48;2;{baixo[0]};{baixo[1]};{baixo[2]}m▀"


def frame_ansi(img):
    px = img.load()
    linhas = []
    for y in range(0, img.height - 1, 2):
        linhas.append("".join(_bloco(px[x, y], px[x, y + 1]) for x in range(img.width)) + RESET)
    return linhas


def carregar(moeda, skin, extra_dir=None, estagio="adulto"):
    from .sprites import nome_folha
    if skin and skin.startswith("plugin:"):
        caminho = plugins.descobrir(extra_dir)[skin]["_folha"]
    else:
        caminho = recursos.ASSETS / "sprites" / nome_folha(moeda, skin or "padrao", estagio)
    folha = Image.open(caminho).convert("RGBA")
    return {(l, f): folha.crop((f * 48, j * 48, (f + 1) * 48, (j + 1) * 48))
            for j, l in enumerate(LINHAS) for f in range(FRAMES)}


class _Teclado:
    """Leitura de tecla sem bloquear (POSIX: termios; Windows: msvcrt)."""

    def __enter__(self):
        self.velho = None
        if os.name != "nt" and sys.stdin.isatty():
            import termios
            import tty
            self.velho = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def tecla(self):
        if os.name == "nt":
            import msvcrt
            return msvcrt.getwch() if msvcrt.kbhit() else None
        import select
        if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

    def __exit__(self, *a):
        if self.velho:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.velho)


def painel(moeda, preco, var, estado, vida, frase):
    cor = arts.CORES[estado].lstrip("#")
    r, g, b = (int(cor[i:i + 2], 16) for i in (0, 2, 4))
    c = f"\x1b[1;38;2;{r};{g};{b}m"
    cor_vida = "\x1b[38;2;177;62;83m"
    coracoes = "".join("♥" if vida - i * 2 >= 1 else "♡" for i in range(5))
    preco_s = logic.formatar_preco(preco) if preco else "carregando..."
    var_s = f"{var:+.2f}%" if preco else ""
    return [f"{c}{arts.NOMES[moeda]} - {arts.TITULOS[estado]}{RESET}",
            f"{moeda} {preco_s} {c}{var_s}{RESET}   {cor_vida}{coracoes}{RESET}",
            f"\x1b[3m\"{frase}\"{RESET}",
            "\x1b[2m[c] trocar moeda  [espaço] carinho  [q] sair\x1b[0m"]


class CtxTUI:
    """Contexto do console no modo terminal (mesmos comandos da janela)."""

    def __init__(self, est):
        self.e = est

    def status(self):
        e = self.e
        p = e["precos"].get(e["moeda"])
        var = logic.variacao_pct(p, e["ref"].get(e["moeda"], p)) if p else 0.0
        xp = e["evo"].xp
        return {"nome": (config.carregar().get("nome_pet") or arts.NOMES[e["moeda"]])[:12], "moeda": e["moeda"], "preco": p,
                "preco_fmt": logic.formatar_preco(p) if p else "carregando", "variacao_pct": var,
                "humor": e["estado"], "nivel": evolucao.nivel(xp), "xp": xp,
                "xp_pct": evolucao.progresso_nivel(xp), "estagio": evolucao.NOMES[e["estagio"]],
                "vida": e["vida"].vida, "crashes": e["vida"].d["crashes"],
                "conquistas": f"{len(e['vida'].d['desbloqueadas'])}/{len(conquistas.LISTA)}",
                "uptime_min": int((time.time() - e["inicio"]) / 60),
                "btc": {"bloco": e["estomago"].d.get("altura"), "comidos": e["estomago"].comidos,
                        "fee_sat_vb": e.get("fee"), "fome": onchain.fome_por_fee(e.get("fee"))[1],
                        "sats_por_dolar": onchain.sats_por_dolar(e["precos"].get("BTC"))}}

    def alimentar(self):
        self.e["pulo"] = FRAMES * 2
        return "nhac!"

    def carinho(self):
        self.e["pulo"] = FRAMES * 2
        self.e["vida"].carinho()
        return arts.reacao(self.e["estado"])

    def panico(self):
        self.e["frase"] = "AAAAA NÃO APAGA MINHA BLOCKCHAIN"

    def sudo_moon(self):
        self.e["forcado"] = time.time() + 15

    def skins(self):
        return ["padrao", "cyberpunk", "gato", "sapo"] + list(plugins.descobrir())

    def trocar_skin(self, sk):
        try:
            self.e["sprites"] = carregar(self.e["moeda"], sk, estagio=self.e["estagio"])
            self.e["skin"] = sk
            return f"skin: {sk}"
        except (OSError, KeyError):
            return f"skin desconhecida: {sk}"

    def trocar_moeda(self, m):
        if m not in config.MOEDAS:
            return "moeda desconhecida"
        self.e["moeda"] = m
        self.e["sprites"] = carregar(m, self.e["skin"], estagio=self.e["estagio"])
        return f"moeda: {m}"

    def alternar_sats(self):
        return "sats: só na janela, por enquanto"

    def carteira(self, end):
        if not end:
            return ["uso: wallet bc1q...  (só endereço público)"]
        ok, msg = onchain.validar_endereco(end)
        if not ok:
            return [msg]
        s = onchain.saldo_endereco(end)
        return [f"saldo watch-only: {s['total']:,} sats em {s['txs']} txs".replace(",", ".")]


    def _st(self):
        st = self.status()
        st["skin"] = self.e.get("skin", "padrao")
        return st

    def compartilhar(self):
        import webbrowser
        cfg = config.carregar()
        site = cfg.get("site") or share.SITE
        caminho = share.salvar(self._st(), self.e["vida"].d["desbloqueadas"], site)
        url = share.url_x(self._st(), site)
        aberto = webbrowser.open(url)
        return [f"card salvo: {caminho}", "post pronto (você que posta):" if aberto else "abra e poste você mesmo:", url]

    def ranking(self, args):
        cfg = config.carregar()
        return ranking.comando(cfg, self._st(), list(args), config.salvar)


def _modo_comando(console, tec, est):
    """Sai do cbreak, lê uma linha, mostra a saída e volta pro bicho."""
    tec.__exit__()
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25h\x1b[32mSatoshiPet OS - 'help', 'exit' volta pro bicho\x1b[0m\n")
    while True:
        try:
            linha = input("\x1b[92m$ \x1b[0m")
        except EOFError:
            break
        if linha.strip() in ("exit", "quit", "q", ""):
            break
        for out in console.executar(linha):
            if out == SPRITE:
                print("\n".join(frame_ansi(est["sprites"][(est["estado"], 0)])))
            else:
                print("\x1b[32m" + out + "\x1b[0m")
    tec.__enter__()
    sys.stdout.write("\x1b[?25l\x1b[2J")


def rodar(opcoes, frames=0):
    cfg = config.carregar()  # a TUI compartilha XP/evolução com a janela
    evo = evolucao.Evolucao(cfg.get("evolucao"))
    vida = conquistas.Conquistas(cfg.get("progresso"))
    estagio = evolucao.estagio(evo.xp, vida.d["crashes"])
    est = {"moeda": opcoes.get("moeda") or "BTC", "skin": opcoes.get("skin") or "padrao",
           "precos": {}, "ref": {}, "estado": "garimpando", "pulo": 0, "frase": "gm, fren! (` ou : abre o console)",
           "evo": evo, "vida": vida, "estagio": estagio, "inicio": time.time(), "forcado": 0,
           "estomago": onchain.Estomago(cfg.get("onchain")), "fee": None}
    est["sprites"] = carregar(est["moeda"], est["skin"], opcoes.get("skins_dir"), estagio)
    escala = 2 if (opcoes.get("escala") or 1) >= 2 and shutil.get_terminal_size().columns >= 100 else 1
    console = Console(CtxTUI(est))

    def buscar():
        while True:
            try:
                est["precos"].update(logic.buscar_precos(list(config.MOEDAS)))
            except Exception:
                pass
            try:
                h, ts = onchain.ultimo_bloco()
                if est["estomago"].novo_tip(h, ts):
                    est["pulo"], est["frase"] = FRAMES * 2, f"bloco #{h} comido! nhac"
                est["fee"] = onchain.fees()["halfHourFee"]
            except Exception:
                pass
            time.sleep(config.INTERVALO)

    threading.Thread(target=buscar, daemon=True).start()
    t_frase, f, n = time.time(), 0, 0
    sys.stdout.write("\x1b[?25l\x1b[2J")  # esconde cursor, limpa tela
    try:
        with _Teclado() as tec:
            while True:
                k = tec.tecla()
                if k in ("q", "Q", "\x03"):
                    break
                if k in ("`", ":"):
                    _modo_comando(console, tec, est)
                if k == "c":
                    moedas = list(config.MOEDAS)
                    CtxTUI(est).trocar_moeda(moedas[(moedas.index(est["moeda"]) + 1) % len(moedas)])
                if k == " ":
                    est["frase"] = CtxTUI(est).carinho()
                moeda = est["moeda"]
                p = est["precos"].get(moeda)
                var = 0.0
                if p:
                    est["ref"].setdefault(moeda, p)
                    var = logic.variacao_pct(p, est["ref"][moeda])
                    novo = "moon" if time.time() < est["forcado"] else logic.estado_do_bicho(var)
                    if novo != est["estado"]:
                        est["estado"], est["frase"] = novo, arts.frase(novo, moeda)
                if time.time() - t_frase > 10:
                    est["frase"], t_frase = arts.frase(est["estado"], moeda), time.time()
                pulo = est["pulo"]
                img = est["sprites"][("pulo", (FRAMES * 2 - pulo) % FRAMES) if pulo else (est["estado"], f)]
                if escala > 1:
                    img = img.resize((96, 96), Image.NEAREST)
                extra = f"bloco {est['estomago'].d.get('altura') or '?'}  fee {est['fee'] or '?'} sat/vB  " \
                        f"LV{evolucao.nivel(evo.xp)} {evolucao.NOMES[est['estagio']]}"
                saida = frame_ansi(img) + [""] + painel(moeda, p, var, est["estado"], vida.vida, est["frase"]) + \
                    ["\x1b[2m" + extra + "  [`] console\x1b[0m"]
                sys.stdout.write("\x1b[H" + "\n".join(l + "\x1b[K" for l in saida) + "\n")
                sys.stdout.flush()
                f = (f + 1) % FRAMES
                est["pulo"] = max(0, pulo - 1)
                n += 1
                if frames and n >= frames:
                    break
                time.sleep(0.18)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + "\x1b[?25h\n")
    return 0
