"""entrada.py - mouse, teclado e o console hacker (` abre).

Mixin do Tamagoshi (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import webbrowser

from . import (
    cenas,
    config,
)


class MixinEntrada:
    # ---------- mouse e teclado ----------
    def inicio_arraste(self, e):
        if self.cena:
            self.cena.clique(e.x, e.y)
            if getattr(self.cena, "acabou", False):
                self.cena = None
            self._desenhar()
            self._press = None
            return
        if self.toast and len(self.toast) > 2 and self.update and e.y < 50:
            self.abrir_update()
        elif e.y < 50 and self.link_balao:  # manchete / baleia: abre no navegador
            self.clique_balao()
        self._x, self._y = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()
        self._press = (e.x_root, e.y_root, e.x, e.y)
        self.root.focus_force()  # pra janela sem borda receber o código konami

    def arrastando(self, e):
        if self.cena or getattr(self, "_press", 1) is None:
            if isinstance(self.cena, cenas.PegaSats):
                self.cena.mouse(e.x)
            return
        self.root.geometry(f"+{e.x_root - self._x}+{e.y_root - self._y}")

    def fim_arraste(self, e):
        if self.cena or getattr(self, "_press", 1) is None:
            return
        px, py, cx, cy = getattr(self, "_press", (e.x_root, e.y_root, -99, -99))
        if abs(e.x_root - px) + abs(e.y_root - py) <= 4:  # clique, não arraste
            x0, y0, x1, y1 = self.SPRITE_BOX
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                self.carinho()
            elif self.Y_BOTAO <= cy <= self.Y_BOTAO + 36:
                webbrowser.open(config.LINK_AFILIADO)
            return
        self.cfg["posicao"] = [self.root.winfo_x(), self.root.winfo_y()]
        config.salvar(self.cfg)

    def _tecla(self, e):
        if self.cena:
            self.cena.tecla(e)
            if getattr(self.cena, "acabou", False):
                self.cena = None
            if not isinstance(self.cena, cenas.PegaSats):
                self._desenhar()
            return
        if e.keysym in ("p", "P"):
            return self.brincar()
        if self.console_aberto:
            return self._tecla_console(e)
        if e.char == "`" or e.keysym in ("grave", "dead_grave"):
            return self.alternar_console()
        if self.konami.alimentar(e.keysym):
            self.revelar_satoshi()
        passo = 50 if e.keysym in "HJKL" and len(e.keysym) == 1 else 10
        mov = {"h": (-1, 0), "j": (0, 1), "k": (0, -1), "l": (1, 0)}.get(e.keysym.lower() if len(e.keysym) == 1 else "")
        if mov:  # vim keys: hjkl move o widget (HJKL = turbo)
            x, y = self.root.winfo_x() + mov[0] * passo, self.root.winfo_y() + mov[1] * passo
            self.root.geometry(f"+{x}+{y}")
            self.cfg["posicao"] = [x, y]

    # ---------- console hacker ----------
    def alternar_console(self):
        self.console_aberto = not self.console_aberto
        self.root.focus_force()
        self._desenhar()

    def _tecla_console(self, e):
        if e.keysym in ("Escape",) or e.char == "`":
            self.console_aberto = False
        elif e.keysym == "Return":
            self.executar_console(self.console_input)
            self.console_input = ""
        elif e.keysym == "BackSpace":
            self.console_input = self.console_input[:-1]
        elif e.keysym == "Up" and self.console.historico:
            self.console_hist_i = max(0, (self.console_hist_i or len(self.console.historico)) - 1)
            self.console_input = self.console.historico[self.console_hist_i]
        elif e.char and e.char.isprintable() and len(self.console_input) < 60:
            self.console_input += e.char
        self._desenhar()

    def executar_console(self, linha):
        eco = linha
        if linha.strip().startswith("ai set "):  # não deixa a chave BYO aparecer na tela (nem em screenshot)
            p = linha.split()
            eco = " ".join(p[:3] + ["****"] * (len(p) > 3) + p[4:])
        self.console_linhas.append("> " + eco)
        self.console.historico = self.console.historico[-100:]
        if linha.strip() in ("clear", "cls"):
            self.console_linhas = []
        elif linha.strip() in ("exit", "quit", "q"):
            self.console_aberto = False
        else:
            self.console_linhas += self.console.executar(linha)
        self.console_hist_i = 0
        self.console_linhas = self.console_linhas[-60:]
