"""main.py - Tamagoshi Cripto: o bichinho que sente o mercado mais que você.

Free: BTC, pixel art animada, carinho, vida, conquistas, sons, lore (F&G, halving),
      skins da comunidade, terminal mode, bandeja, afiliado.
Pro:  5 moedas, skins premium, ajustes, alertas, sparkline e iniciar com o sistema.
"""
import threading
import time
import tkinter as tk

from . import (
    api,
    arts,
    cenas,
    config,
    conquistas,
    crashlog,
    engajamento,
    evolucao,
    i18n,
    juice,
    logic,
    lojinha,
    lore,
    mercado,
    onchain,
    plugins,
    recursos,
    sistema,
    sons,
)
from .console import Console
from .desenho import MixinDesenho
from .entrada import MixinEntrada
from .fonte import FontePixel
from .graficos import (  # noqa: F401  (re-export: cenas/testes usam main._png_para_tk etc.)
    C_PAINEL,
    C_PAINEL2,
    C_PAPEL,
    C_TINTA,
    COR_TRANSP,
    FRAME_MS,
    FRASE_MS,
    SKINS_PRO,
    _png_para_tk,
    carregar_frames,
)
from .menus import MixinMenus
from .rede import MixinRede
from .sprites import FRAMES
from .vida import MixinVida


class Tamagoshi(MixinVida, MixinDesenho, MixinEntrada, MixinMenus, MixinRede,
                engajamento.MixinEngajamento, mercado.MixinMercado, lojinha.MixinLoja):
    def __init__(self, opcoes=None):
        op = opcoes or {}
        self.cfg = config.carregar()
        for k in ("moeda", "skin", "escala", "crt", "mudo"):  # flags da CLI vencem a config
            if op.get(k) is not None:
                self.cfg[k] = op[k]
        crashlog.instalar()
        self.pro = self._pro_inicial()
        self.plugins = plugins.descobrir(op.get("skins_dir"))
        self._init_loja(op.get("loja_dir"))
        self._aplicar_limites_free()

        self.precos, self.erro = {}, None
        self.lock = threading.Lock()
        self.frame, self.estado = 0, "garimpando"
        self.alertados = set()
        self.historico = logic.Historico()
        self.conq = conquistas.Conquistas(self.cfg.get("progresso"))
        self.som = sons.Som(mudo=self.cfg.get("mudo", False), volume=float(self.cfg.get("volume", 0.35)))
        self.juice = juice.Particulas()
        self.cena = None           # onboarding / mini-game tomam o widget
        self.update = None         # {"versao", "url"} se saiu versão nova
        self.op = op
        self.reacao = 0            # frames restantes do pulo
        self.toast = None
        self.fng = None            # (valor, rótulo)
        self.bloco = None
        self.konami = lore.Konami()
        self.cliques_btc = 0
        self.cache_sprites = {}
        self.frase_atual = "gm, fren!"
        # on-chain + evolução + nerdices
        self.estomago = onchain.Estomago(self.cfg.get("onchain"))
        self.evo = evolucao.Evolucao(self.cfg.get("evolucao"))
        self.estagio = evolucao.estagio(self.evo.xp, self.conq.d["crashes"])
        self.fee = self.gas = self.hash = None
        self.eventos = []          # fila thread -> GUI: ("bloco", n) / ("carteira", delta)
        self.comendo = 0           # frames restantes da animação de comer
        self.bloco_comido = None
        self.panico_t = 0
        self.estado_forcado = None
        self.vigia = onchain.Vigia()
        self.saldo = None
        self.inicio = time.time()
        self.console = Console(self)
        self.console_aberto = False
        self.console_linhas = ["Tamagoshi OS - digite 'help'"]
        self.console_input = ""
        self.console_hist_i = 0
        self.rodizio = 0           # qual info nerd aparece no painel
        self.tray = None
        self.ultimo_erro = None
        self.escala = max(1, min(6, int(self.cfg.get("escala", 3))))
        self._init_mercado()
        self._medidas()

        self.root = tk.Tk()
        self.root.title("Tamagoshi Cripto")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COR_TRANSP)
        self.root.report_callback_exception = self._erro_tk
        self.cv = tk.Canvas(self.root, width=self.LARG, height=self.ALT, bg=COR_TRANSP,
                            highlightthickness=0, bd=0)
        self.cv.pack()
        sistema.aplicar_transparencia(self.root, self.cv, COR_TRANSP)
        self.fonte = FontePixel()
        try:
            self.root.iconphoto(True, tk.PhotoImage(file=str(recursos.ASSETS / "icone.png")))
        except tk.TclError:
            pass

        self.cv.tag_bind("botao", "<Enter>", lambda e: self.cv.config(cursor="hand2"))
        self.cv.tag_bind("botao", "<Leave>", lambda e: self.cv.config(cursor=""))
        i18n.definir(self.op.get("idioma") or self.cfg.get("idioma", "auto"))
        self._montar_menu()
        self.cv.bind("<ButtonPress-1>", self.inicio_arraste)
        self.cv.bind("<B1-Motion>", self.arrastando)
        self.cv.bind("<ButtonRelease-1>", self.fim_arraste)
        for b in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):  # Mac: botão direito = Button-2/ctrl-clique
            self.cv.bind(b, self.abrir_menu)
        self.root.bind("<Key>", self._tecla)

        x, y = self.cfg.get("posicao", [100, 100])
        self.root.geometry(f"+{x}+{y}")
        if not self.cfg.get("onboarding_ok") and not op.get("sem_onboarding"):
            self.cena = cenas.Onboarding(self)
        self._desenhar()
        if self.cfg.get("musica"):
            self.som.musica(True)
        threading.Thread(target=self.loop_api, daemon=True).start()
        if self.cfg.get("checar_updates", True) and not op.get("sem_updates"):
            threading.Thread(target=self.loop_update, daemon=True).start()
        if self.pro and self.cfg.get("licenca_provedor", "hmac") != "hmac":
            threading.Thread(target=self._revalidar_pro, daemon=True).start()
        threading.Thread(target=self.loop_lore, daemon=True).start()
        threading.Thread(target=self.loop_onchain, daemon=True).start()
        threading.Thread(target=self.loop_mercado, daemon=True).start()
        self.iniciar_twitch()
        api_ligada = self.cfg.get("api", True) and not op.get("sem_api")
        self.api = api.iniciar(self.status, folha=self.folha_png) if api_ligada else None
        self.root.after(1000, self.atualizar_tela)
        self.root.after(FRAME_MS, self.animar)
        self.root.after(FRASE_MS, self.trocar_frase)
        self.root.after(10000, self.tick_vida)
        if not op.get("sem_tray"):
            self.root.after(1500, self._iniciar_tray)


    def _erro_tk(self, exc, val, tb):
        self.ultimo_erro = crashlog.registrar(exc, val, tb, "tk")
        print(self.ultimo_erro)


    # ---------- bandeja ----------
    def _iniciar_tray(self):
        depois = lambda f: (lambda: self.root.after(0, f))  # noqa: E731 - volta pra thread do Tk
        self.tray = sistema.iniciar_tray(recursos.ASSETS / "icone.png", depois(self.mostrar),
                                         depois(self.esconder), depois(self.sair),
                                         mac_menubar=self.cfg.get("menubar_mac"))

    def esconder(self):
        self.root.withdraw()

    def mostrar(self):
        self.root.deiconify()
        self.root.attributes("-topmost", True)

    def sair(self):
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        self._salvar_progresso()
        self.cfg["posicao"] = [self.root.winfo_x(), self.root.winfo_y()]
        config.salvar(self.cfg)
        self.root.destroy()


    def _nova_frase(self):
        if self.frase_noticia() or self.frase_papel():
            return
        extras = self.plugins.get(self.cfg["skin"], {}).get("frases")
        self.frase_atual = arts.frase(self.estado, self.cfg["moeda"], extras)

    # ---------- loops da GUI ----------
    def atualizar_tela(self):
        if self.pro:
            self._checar_alertas()
        self.root.after(1000, self.atualizar_tela)

    def animar(self):
        self.root.after(FRAME_MS, self.animar)
        if isinstance(self.cena, cenas.PegaSats):
            return  # o jogo tem o próprio loop de 50 ms
        if self.cena:
            if not self.cena.tick():
                self.cena = None
            self.juice.tick()
            self._desenhar()
            return
        self.frame = (self.frame + 1) % FRAMES
        self.juice.tick()
        self.rodizio += 1
        self._processar_eventos()
        if self.comendo:
            self.comendo -= 1
        if self.panico_t:
            self.panico_t -= 1
        if self.reacao:
            self.reacao -= 1
        if self.toast:
            self.toast[1] -= 1
            if self.toast[1] <= 0:
                self.toast = None
                if getattr(self, "link_do_toast", False):  # link da baleia morre junto com o toast
                    self.link_balao = self.link_do_toast = None
        self._desenhar()

    def trocar_frase(self):
        self._nova_frase()
        self.root.after(FRASE_MS, self.trocar_frase)


    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Tamagoshi().run()
