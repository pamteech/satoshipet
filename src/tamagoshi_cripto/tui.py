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

from . import arts, config, conquistas, logic, plugins, recursos
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


def carregar(moeda, skin, extra_dir=None):
    if skin and skin.startswith("plugin:"):
        caminho = plugins.descobrir(extra_dir)[skin]["_folha"]
    else:
        caminho = recursos.sheet_path(moeda, skin or "padrao")
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


def rodar(opcoes, frames=0):
    moeda = opcoes.get("moeda") or "BTC"
    skin = opcoes.get("skin") or "padrao"
    escala = 2 if (opcoes.get("escala") or 1) >= 2 and shutil.get_terminal_size().columns >= 100 else 1
    sprites = carregar(moeda, skin, opcoes.get("skins_dir"))
    precos, ref = {}, {}
    vida = conquistas.Conquistas()

    def buscar():
        while True:
            try:
                precos.update(logic.buscar_precos(list(config.MOEDAS)))
            except Exception:
                pass
            time.sleep(config.INTERVALO)

    threading.Thread(target=buscar, daemon=True).start()
    estado, frase, t_frase, f, n, pulo = "garimpando", "gm, fren!", time.time(), 0, 0, 0
    sys.stdout.write("\x1b[?25l\x1b[2J")  # esconde cursor, limpa tela
    try:
        with _Teclado() as tec:
            while True:
                k = tec.tecla()
                if k in ("q", "Q", "\x03"):
                    break
                if k == "c":
                    moedas = list(config.MOEDAS)
                    moeda = moedas[(moedas.index(moeda) + 1) % len(moedas)]
                    sprites = carregar(moeda, skin if not skin.startswith("plugin:") else skin,
                                       opcoes.get("skins_dir"))
                if k == " ":
                    pulo, frase = FRAMES * 2, arts.reacao(estado)
                    vida.carinho()
                p = precos.get(moeda)
                var = 0.0
                if p:
                    ref.setdefault(moeda, p)
                    var = logic.variacao_pct(p, ref[moeda])
                    novo = logic.estado_do_bicho(var)
                    if novo != estado:
                        estado, frase = novo, arts.frase(novo, moeda)
                if time.time() - t_frase > 10:
                    frase, t_frase = arts.frase(estado, moeda), time.time()
                img = sprites[("pulo", (FRAMES * 2 - pulo) % FRAMES) if pulo else (estado, f)]
                if escala > 1:
                    img = img.resize((96, 96), Image.NEAREST)
                saida = frame_ansi(img) + [""] + painel(moeda, p, var, estado, vida.vida, frase)
                sys.stdout.write("\x1b[H" + "\n".join(l + "\x1b[K" for l in saida) + "\n")
                sys.stdout.flush()
                f = (f + 1) % FRAMES
                pulo = max(0, pulo - 1)
                n += 1
                if frames and n >= frames:
                    break
                time.sleep(0.18)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + "\x1b[?25h\n")
    return 0
