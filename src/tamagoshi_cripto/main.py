"""main.py - Tamagoshi Cripto: o bichinho que sente o mercado mais que você.

Free: BTC, pixel art animada, carinho, vida, conquistas, sons, lore (F&G, halving),
      skins da comunidade, terminal mode, bandeja, afiliado.
Pro:  5 moedas, skins premium, ajustes, alertas, sparkline e iniciar com o sistema.
"""
import base64
import io
import math
import random
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog

from PIL import Image

from . import __version__, api, arts, cenas, config, conquistas, crashlog, juice, licencas, updates, evolucao, license, logic, lore, onchain, plugins, ranking, recursos, share, sistema, sons
from .console import SPRITE, Console
from .fonte import FontePixel
from .sprites import FRAMES, LINHAS, SKINS_SECRETAS, nome_folha

COR_TRANSP = "#010101"   # cor-chave que vira buraco no Windows
FRAME_MS = 180           # 4 frames por loop ~ 0,7s
FRASE_MS = 10000
SKINS_PRO = {"cyberpunk", "gato", "sapo"}

C_TINTA, C_PAPEL, C_PAINEL, C_PAINEL2 = "#1a1c2c", "#f4f4f4", "#29213f", "#3e3466"


def _png_para_tk(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def carregar_frames(caminho, escala, crt=False, chapeu=None):
    """Folha 192x192 -> {(linha, frame): PhotoImage} ampliado sem borrar (+ chapéu de época, + scanlines CRT)."""
    folha = Image.open(caminho).convert("RGBA")
    frames = {}
    for j, linha in enumerate(LINHAS):
        for f in range(FRAMES):
            fr = folha.crop((f * 48, j * 48, (f + 1) * 48, (j + 1) * 48))
            if chapeu:
                fr = juice.aplicar_chapeu(fr, chapeu)
            fr = fr.resize((48 * escala, 48 * escala), Image.NEAREST)
            if crt and escala >= 2:
                px = fr.load()
                for y in range(escala - 1, fr.height, escala):  # última linha de cada pixel escurece
                    for x in range(fr.width):
                        r, g, b, a = px[x, y]
                        if a:
                            px[x, y] = (r * 3 // 5, g * 3 // 5, b * 3 // 5, a)
            frames[(linha, f)] = _png_para_tk(fr)
    return frames


class Tamagoshi:
    def __init__(self, opcoes=None):
        op = opcoes or {}
        self.cfg = config.carregar()
        for k in ("moeda", "skin", "escala", "crt", "mudo"):  # flags da CLI vencem a config
            if op.get(k) is not None:
                self.cfg[k] = op[k]
        crashlog.instalar()
        self.pro = self._pro_inicial()
        self.plugins = plugins.descobrir(op.get("skins_dir"))
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
        self.api = api.iniciar(self.status) if (self.cfg.get("api", True) and not op.get("sem_api")) else None
        self.root.after(1000, self.atualizar_tela)
        self.root.after(FRAME_MS, self.animar)
        self.root.after(FRASE_MS, self.trocar_frase)
        self.root.after(10000, self.tick_vida)
        if not op.get("sem_tray"):
            self.root.after(1500, self._iniciar_tray)

    # ---------- layout (depende da escala) ----------
    def _medidas(self):
        S = 48 * self.escala
        self.S = S
        self.LARG = max(272, S + 48)
        self.Y_SPRITE = 58
        y = self.Y_SPRITE + S + 4
        self.Y_NOME, self.Y_VIDA = y, y + 14
        self.Y_XP = y + 36
        self.Y_PAINEL = y + 52
        self.Y_BOTAO = self.Y_PAINEL + 66
        self.ALT = self.Y_BOTAO + 40
        cx = self.LARG // 2
        self.SPRITE_BOX = (cx - S // 2, self.Y_SPRITE, cx + S // 2, self.Y_SPRITE + S)

    def _erro_tk(self, exc, val, tb):
        self.ultimo_erro = crashlog.registrar(exc, val, tb, "tk")
        print(self.ultimo_erro)

    # ---------- licença (provedores em licencas.py) ----------
    def _pro_inicial(self):
        """Na abertura não bate na rede: hmac valida local; online usa o cache + período de graça."""
        cfg = self.cfg
        if (cfg.get("licenca_provedor") or "hmac") == "hmac":
            return license.validar(cfg.get("email"), cfg.get("licenca"))
        cache = cfg.get("licenca_cache") or {}
        return bool(cfg.get("licenca") and cache.get("chave") == licencas._hash(cfg["licenca"])
                    and time.time() - cache.get("validado_em", 0) < licencas.GRACA_DIAS * 86400)

    def _revalidar_pro(self):
        res = licencas.verificar(self.cfg, self.cfg.get("email"), self.cfg.get("licenca"))
        with self.lock:
            self.eventos.append(("licenca", res.ok, res.msg))

    # ---------- atualizações (só avisa, nunca instala) ----------
    def loop_update(self):
        time.sleep(8)
        info = updates.checar()
        if info and info["versao"] != self.cfg.get("update_ignorado"):
            with self.lock:
                self.eventos.append(("update", info))

    def checar_update_agora(self):
        info = updates.checar()
        if info:
            self.update = info
            self.toast = [f"v{info['versao']} - clique aqui", 60, "NOVA VERSÃO!"]
            self.som.tocar("update")
        else:
            messagebox.showinfo("Atualizações", f"Você está na versão mais nova que achei (v{__version__}).\n"
                                "(ou estou offline / o repo ainda não é público)", parent=self.root)

    def abrir_update(self):
        if self.update:
            webbrowser.open(self.update["url"])  # só abre a página do Release. Instalar é com você.

    # ---------- relatório de erro ----------
    def enviar_relatorio(self):
        if messagebox.askyesno("Enviar relatório",
                               "Vou abrir uma issue PREENCHIDA no GitHub no seu navegador, com a versão, o sistema e o "
                               "último erro (sem seu nome de usuário). Você revisa e decide se envia. Abrir?",
                               parent=self.root):
            webbrowser.open(crashlog.url_issue())

    # ---------- acessibilidade e juice ----------
    def mudar_escala(self, e):
        self.escala = self.cfg["escala"] = max(1, min(6, int(e)))
        self._medidas()
        self.cv.config(width=self.LARG, height=self.ALT)
        self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def alternar_opcao(self, chave, var=None):
        self.cfg[chave] = bool(var.get()) if var is not None else not self.cfg.get(chave)
        if chave == "musica":
            self.som.musica(self.cfg["musica"])
        if chave == "chapeus":
            self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def rever_intro(self):
        self.cena = cenas.Onboarding(self)
        self._desenhar()

    # ---------- mini-game ----------
    def brincar(self):
        if isinstance(self.cena, cenas.PegaSats):
            return ["já tá jogando!"]
        self.console_aberto = False
        self.cena = cenas.PegaSats(self)
        self.root.focus_force()
        self.root.after(int(cenas.PegaSats.DT * 1000), self._loop_jogo)
        return ["Pega os Sats! ← → por 20s. boa sorte, anon"]

    def _loop_jogo(self):
        cena = self.cena
        if not isinstance(cena, cenas.PegaSats):
            return
        if not cena.tick():
            self.cena = None
            self._desenhar()
            return
        self.juice.tick()
        cena.desenhar()
        self.root.after(int(cenas.PegaSats.DT * 1000), self._loop_jogo)

    def fim_minigame(self, pontos, pegos):
        self.cfg["diversao"] = 100.0
        xp = min(90, pontos * 3)
        if xp:
            self._ganhar_xp("jogo", xp)
        if pegos >= 25:
            self._comemorar(self.conq.especial("stacker"))
        self.frase_atual = f"+{xp} XP! bora de novo? (P)" if xp else "nem um satzinho... HFSP"
        recorde = self.cfg.get("recorde_jogo", 0)
        if pegos > recorde:
            self.cfg["recorde_jogo"] = pegos
        self._salvar_progresso()

    def _sprites_mini(self):
        chave = ("mini", self.cfg["moeda"], self.cfg["skin"], self.estagio, self._chapeu())
        if chave not in self.cache_sprites:
            self.cache_sprites[chave] = carregar_frames(self._caminho_folha(), 2, chapeu=self._chapeu())
        return self.cache_sprites[chave]

    def _chapeu(self):
        return juice.chapeu_do_dia() if self.cfg.get("chapeus", True) else None

    # ---------- Free vs Pro ----------
    def _skin_permitida(self, sk):
        if sk == "padrao" or sk.startswith("plugin:"):
            return sk == "padrao" or sk in self.plugins
        if sk in SKINS_SECRETAS:
            return sk in self.cfg.get("segredos", [])
        return self.pro and sk in SKINS_PRO

    def _aplicar_limites_free(self):
        if self.cfg.get("moeda") not in config.MOEDAS:
            self.cfg["moeda"] = "BTC"
        if not self.pro:
            self.cfg["moeda"] = "BTC"
            self.cfg["limite_alta"], self.cfg["limite_queda"] = 2.0, -2.0
        if not self._skin_permitida(self.cfg.get("skin", "padrao")):
            self.cfg["skin"] = "padrao"

    def _exige_pro(self):
        if self.pro:
            return True
        if messagebox.askyesno("Recurso Pro", "Isso é coisa da versão Pro!\nQuer ativar sua licença agora?",
                               parent=self.root):
            self.ativar_pro()
        return self.pro

    # ---------- menu ----------
    def _montar_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        self.menu_moedas = tk.Menu(m, tearoff=0)
        for s in config.MOEDAS:
            self.menu_moedas.add_command(label=f"{s} - {arts.NOMES[s]}" + ("" if s == "BTC" else "  [Pro]"),
                                         command=lambda s=s: self.trocar_moeda(s))
        self.menu_skins = tk.Menu(m, tearoff=0)
        self._preencher_skins()
        m.add_cascade(label="Trocar moeda", menu=self.menu_moedas)
        m.add_cascade(label="Trocar skin", menu=self.menu_skins)
        m.add_command(label="Configurações", command=self.configuracoes)
        m.add_command(label="Alertas de preço", command=self.config_alertas)
        m.add_command(label="Conquistas", command=self.ver_conquistas)
        m.add_command(label="Carteira watch-only...", command=self.config_carteira)
        m.add_command(label="Console hacker (`)", command=self.alternar_console)
        m.add_command(label="Compartilhar card (X)", command=self._menu_share)
        m.add_command(label="Ranking (opt-in)...", command=self.config_ranking)
        m.add_command(label="Brincar: Pega os Sats (P)", command=self.brincar)
        ma = tk.Menu(m, tearoff=0)  # aparência e acessibilidade
        self.var_escala = tk.IntVar(value=self.escala)
        for e in range(1, 7):
            ma.add_radiobutton(label=f"Tamanho {e}x" + ("  (padrão)" if e == 3 else ""), variable=self.var_escala,
                               value=e, command=lambda e=e: self.mudar_escala(e))
        ma.add_separator()
        self.vars_op = {}
        for chave, rot in (("alto_contraste", "Alto contraste"), ("dia_noite", "Paleta dia/noite"),
                           ("chapeus", "Chapéus de época"), ("juice", "Tremidinha e partículas"),
                           ("musica", "Música de fundo (chiptune)"), ("checar_updates", "Avisar versão nova")):
            v = self.vars_op[chave] = tk.BooleanVar(value=bool(self.cfg.get(chave)))
            ma.add_checkbutton(label=rot, variable=v, command=lambda c=chave, v=v: self.alternar_opcao(c, v))
        m.add_cascade(label="Aparência e acessibilidade", menu=ma)
        mh = tk.Menu(m, tearoff=0)
        mh.add_command(label="Rever introdução", command=self.rever_intro)
        mh.add_command(label="Procurar atualização", command=self.checar_update_agora)
        mh.add_command(label="Enviar relatório de erro...", command=self.enviar_relatorio)
        mh.add_command(label=f"Tamagoshi Cripto v{__version__}", state="disabled")
        m.add_cascade(label="Ajuda", menu=mh)
        self.var_sats = tk.BooleanVar(value=self.cfg.get("unidade") == "sats")
        m.add_checkbutton(label="Mostrar em sats", variable=self.var_sats,
                          command=lambda: self.alternar_sats(self.var_sats.get()))
        self.var_mudo = tk.BooleanVar(value=self.cfg.get("mudo", False))
        m.add_checkbutton(label="Mudo", variable=self.var_mudo, command=self.alternar_mudo)
        self.var_crt = tk.BooleanVar(value=self.cfg.get("crt", False))
        m.add_checkbutton(label="Efeito CRT", variable=self.var_crt, command=self.alternar_crt)
        self.var_auto = tk.BooleanVar(value=sistema.autostart_ativo())
        m.add_checkbutton(label=sistema.nome_autostart(), variable=self.var_auto,
                          command=self.alternar_autostart,
                          state="normal" if sistema.autostart_suportado() else "disabled")
        m.add_command(label="Esconder (bandeja)", command=self.esconder,
                      state="normal" if sistema.tray_disponivel(self.cfg.get("menubar_mac")) else "disabled")
        m.add_separator()
        m.add_command(label="Ativar Pro", command=self.ativar_pro)
        m.add_command(label="Sair", command=self.sair)
        self.menu = m

    def _preencher_skins(self):
        ms = self.menu_skins
        ms.delete(0, "end")
        for sk in arts.SKINS_DISPONIVEIS:
            ms.add_command(label=sk + ("  [Pro]" if sk in SKINS_PRO else ""),
                           command=lambda sk=sk: self.trocar_skin(sk))
        for sk in sorted(self.cfg.get("segredos", [])):
            ms.add_command(label=f"{sk}  [secreta]", command=lambda sk=sk: self.trocar_skin(sk))
        if self.plugins:
            ms.add_separator()
            for pid, meta in self.plugins.items():
                ms.add_command(label=f"{meta['nome']} (por {meta['autor']})",
                               command=lambda pid=pid: self.trocar_skin(pid))

    def abrir_menu(self, e):
        self.menu.entryconfig(self.menu.index("end") - 1, label="Pro ativo" if self.pro else "Ativar Pro")
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def trocar_moeda(self, s):
        if s != "BTC" and not self._exige_pro():
            return
        self.cfg["moeda"] = s
        self.alertados.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def trocar_skin(self, sk):
        if not self._skin_permitida(sk):
            if sk in SKINS_PRO and self._exige_pro():
                return self.trocar_skin(sk)
            return
        self.cfg["skin"] = sk
        config.salvar(self.cfg)
        self._desenhar()

    def configuracoes(self):
        if not self._exige_pro():
            return
        ask = simpledialog.askfloat
        alta = ask("Configurações", "Limite TO THE MOON (%):", initialvalue=self.cfg["limite_alta"], parent=self.root)
        queda = ask("Configurações", "Limite REKT (%, negativo):", initialvalue=self.cfg["limite_queda"], parent=self.root)
        moeda = self.cfg["moeda"]
        atual = self.cfg["preco_referencia"].get(moeda) or self.precos.get(moeda) or 0
        ref = ask("Configurações", f"Preço de referência do {moeda} (USD, 0 = preço atual):",
                  initialvalue=atual, parent=self.root)
        if alta is not None:
            self.cfg["limite_alta"] = abs(alta)
        if queda is not None:
            self.cfg["limite_queda"] = -abs(queda)
        if ref is not None:
            if ref > 0:
                self.cfg["preco_referencia"][moeda] = ref
            else:
                self.cfg["preco_referencia"].pop(moeda, None)
        config.salvar(self.cfg)
        self._desenhar()

    def config_alertas(self):
        if not self._exige_pro():
            return
        moeda = self.cfg["moeda"]
        alvo = self.cfg["alertas"].get(moeda, {})
        acima = simpledialog.askfloat("Alertas", f"Avisar quando {moeda} passar de (USD, 0 = off):",
                                      initialvalue=alvo.get("acima", 0), parent=self.root)
        abaixo = simpledialog.askfloat("Alertas", f"Avisar quando {moeda} cair abaixo de (USD, 0 = off):",
                                       initialvalue=alvo.get("abaixo", 0), parent=self.root)
        self.cfg["alertas"][moeda] = {k: v for k, v in (("acima", acima), ("abaixo", abaixo)) if v}
        self.alertados.discard(moeda)
        config.salvar(self.cfg)

    def ver_conquistas(self):
        messagebox.showinfo("Conquistas", self.conq.resumo(), parent=self.root)

    def alternar_mudo(self):
        self.som.mudo = self.cfg["mudo"] = bool(self.var_mudo.get())
        config.salvar(self.cfg)

    def alternar_crt(self):
        self.cfg["crt"] = bool(self.var_crt.get())
        self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def alternar_autostart(self):
        if not self._exige_pro():
            self.var_auto.set(sistema.autostart_ativo())
            return
        if not sistema.definir_autostart(bool(self.var_auto.get())):
            messagebox.showerror("Ops", "Não consegui configurar a inicialização automática.", parent=self.root)
        self.var_auto.set(sistema.autostart_ativo())

    def ativar_pro(self):
        if self.pro:
            messagebox.showinfo("Pro", "Você já é Pro, sua baleia!", parent=self.root)
            return
        email = simpledialog.askstring("Ativar Pro", "E-mail da compra:", parent=self.root)
        if not email:
            return
        chave = simpledialog.askstring("Ativar Pro", "Chave de licença:", parent=self.root)
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            res = licencas.verificar(self.cfg, email, chave or "", forcar=True)
        finally:
            self.root.config(cursor="")
        if res.ok:
            self.pro = True
            hmac_ = (self.cfg.get("licenca_provedor") or "hmac") == "hmac"
            self.cfg["email"], self.cfg["licenca"] = email.strip().lower(), chave.strip().upper() if hmac_ else chave.strip()
            config.salvar(self.cfg)
            self.cache_sprites.clear()
            messagebox.showinfo("Pro ativado!", res.msg + "\nBem-vindo ao clube das mãos de diamante!", parent=self.root)
        else:
            messagebox.showerror("Ops", res.msg, parent=self.root)

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
        self.console_linhas.append("> " + linha)
        if linha.strip() in ("clear", "cls"):
            self.console_linhas = []
        elif linha.strip() in ("exit", "quit", "q"):
            self.console_aberto = False
        else:
            self.console_linhas += self.console.executar(linha)
        self.console_hist_i = 0
        self.console_linhas = self.console_linhas[-60:]

    # ações chamadas pelo console (também usadas pela API/TUI)
    def alimentar(self):
        self._comer(self.estomago.d.get("altura") or 0, manual=True)
        return "nhac! bloco extra (de mentirinha, não vale XP)"

    def panico(self):
        self.panico_t = 12
        self.som.tocar("panico")
        self.frase_atual = "AAAAA NÃO APAGA MINHA BLOCKCHAIN"
        self._comemorar(self.conq.especial("rm_rf"))

    def sudo_moon(self):
        self.estado_forcado = ("moon", time.time() + 15)
        self.frase_atual = "sudo: TO THE MOON (por 15 segundos)"
        self.som.tocar("moon")
        self._comemorar(self.conq.especial("sudo"))

    def skins(self):
        return [sk for sk in arts.SKINS_DISPONIVEIS + list(self.cfg.get("segredos", [])) + list(self.plugins)
                if self._skin_permitida(sk)]

    def alternar_sats(self, ligar=None):
        atual = self.cfg.get("unidade") == "sats"
        ligar = (not atual) if ligar is None else bool(ligar)
        self.cfg["unidade"] = "sats" if ligar else "usd"
        if ligar:
            self._comemorar(self.conq.especial("moscow"))
        config.salvar(self.cfg)
        return "unidade: " + ("sats (moscow time)" if ligar else "USD")

    def carteira(self, endereco):
        if endereco is None:
            if not self.cfg.get("carteira"):
                return ["nenhuma carteira. uso: wallet bc1q...  (SÓ endereço público!)"]
            s = self.saldo
            return [f"watch-only: {self.cfg['carteira'][:12]}...", f"saldo: {s['total']:,} sats ({s['txs']} txs)".replace(",", ".")
                    if s else "saldo: consultando..."]
        ok, msg = onchain.validar_endereco(endereco)
        if not ok:
            return [msg]
        self.cfg["carteira"] = endereco.strip()
        self.vigia = onchain.Vigia()
        self.saldo = None
        config.salvar(self.cfg)
        self._comemorar(self.conq.especial("not_your_keys"))
        return ["carteira watch-only salva. o bicho só OLHA, nunca mexe.", "(atualiza a cada 2 min via mempool.space)"]

    # ---------- share card & ranking ----------
    def compartilhar(self, abrir=True):
        try:
            caminho = share.salvar(self.status(), self.conq.d["desbloqueadas"], self.cfg.get("site") or share.SITE)
        except Exception as e:
            return [f"share: falhou ({e})"]
        url = share.url_x(self.status(), self.cfg.get("site") or share.SITE)
        if abrir:
            webbrowser.open(url)
        self.ultimo_card = caminho
        return [f"card salvo: {caminho}", "abri o X com o texto pronto. anexe o PNG e poste você mesmo.",
                "(nada foi postado automaticamente)"]

    def _menu_share(self):
        linhas = self.compartilhar()
        messagebox.showinfo("Compartilhar", "\n".join(linhas), parent=self.root)

    def ranking(self, args):
        """Roda em thread (rede); a resposta cai no console quando chegar."""
        def tarefa():
            linhas = ranking.comando(self.cfg, self.status(), list(args), config.salvar)
            with self.lock:
                self.eventos.append(("console", linhas))
        threading.Thread(target=tarefa, daemon=True).start()
        return ["consultando ranking..."]

    def config_ranking(self):
        if self.cfg.get("ranking"):
            if messagebox.askyesno("Ranking", f"Ranking ligado como {self.cfg.get('nick')}. Desligar?", parent=self.root):
                ranking.comando(self.cfg, self.status(), ["off"], config.salvar)
            return
        url = simpledialog.askstring("Ranking (opt-in)", "URL do servidor de ranking:", parent=self.root,
                                     initialvalue=self.cfg.get("ranking_url") or "http://127.0.0.1:8740")
        if not url:
            return
        nick = simpledialog.askstring("Ranking (opt-in)",
                                      "Apelido público (3-16 letras/números/_/-).\n"
                                      "Enviado: apelido, XP, nível, estágio, blocos, nº de conquistas.\n"
                                      "NUNCA carteira, e-mail ou nome real.", parent=self.root)
        if not nick:
            return
        self.cfg["ranking_url"] = url.strip()
        linhas = ranking.comando(self.cfg, self.status(), ["on", nick.strip()], config.salvar)
        messagebox.showinfo("Ranking", "\n".join(linhas[:6]), parent=self.root)

    def config_carteira(self):
        end = simpledialog.askstring(
            "Carteira watch-only",
            "Cole um endereço BTC PÚBLICO (bc1..., 1..., 3...).\n"
            "NUNCA cole seed, chave privada ou xprv. O app só lê o saldo.\n(vazio = remover)",
            initialvalue=self.cfg.get("carteira", ""), parent=self.root)
        if end is None:
            return
        if not end.strip():
            self.cfg["carteira"] = ""
            self.saldo = None
            config.salvar(self.cfg)
            return
        res = self.carteira(end)
        (messagebox.showinfo if res[0].startswith("carteira") else messagebox.showerror)(
            "Carteira", "\n".join(res), parent=self.root)

    def status(self):
        """Estado completo (API /status, console, sketchybar). Barato e só leitura."""
        moeda = self.cfg["moeda"]
        preco = self.precos.get(moeda)
        var = self._variacao(moeda, preco) if preco else 0.0
        btc = self.precos.get("BTC")
        nome = self.nome_pet()
        return {
            "nome": nome, "moeda": moeda, "preco": preco, "preco_fmt": self._fmt_preco(moeda, preco),
            "variacao_pct": round(var, 4), "humor": self.estado,
            "emoji": {"moon": "🚀", "rekt": "💀", "garimpando": "⛏"}[self.estado],
            "nivel": evolucao.nivel(self.evo.xp), "xp": self.evo.xp,
            "xp_pct": evolucao.progresso_nivel(self.evo.xp), "estagio": evolucao.NOMES[self.estagio],
            "vida": round(self.conq.vida, 2), "crashes": self.conq.d["crashes"],
            "conquistas": f"{len(self.conq.d['desbloqueadas'])}/{len(conquistas.LISTA)}",
            "uptime_min": int((time.time() - self.inicio) / 60), "skin": self.cfg["skin"], "pro": self.pro,
            "btc": {"bloco": self.estomago.d.get("altura"), "comidos": self.estomago.comidos,
                    "fee_sat_vb": self.fee, "fome": onchain.fome_por_fee(self.fee)[1],
                    "dormindo": self.estomago.dormindo(),
                    "hashrate": onchain.formatar_hashrate(self.hash) if self.hash else None,
                    "sats_por_dolar": onchain.sats_por_dolar(btc)},
            "eth": {"gas_gwei": round(self.gas, 2) if self.gas else None},
            "fng": {"valor": self.fng[0], "rotulo": self.fng[1]} if self.fng else None,
            "carteira": {"endereco": self.cfg.get("carteira") or None,
                         "saldo_sats": self.saldo["total"] if self.saldo else None},
        }

    def nome_pet(self):
        if self.cfg.get("nome_pet"):
            return self.cfg["nome_pet"][:12]
        return (self.plugins[self.cfg["skin"]]["nome"] if self.cfg["skin"].startswith("plugin:")
                else arts.NOMES[self.cfg["moeda"]])

    def _fmt_preco(self, moeda, preco):
        if not preco:
            return "carregando"
        if self.cfg.get("unidade") == "sats":
            btc = self.precos.get("BTC")
            if moeda == "BTC":
                return f"1$={onchain.sats_por_dolar(preco):,}sat".replace(",", ".")
            if btc:
                sats = preco / btc * 1e8
                return f"{sats:,.2f} sats".replace(",", "X").replace(".", ",").replace("X", ".") if sats < 100 \
                    else f"{sats:,.0f} sats".replace(",", ".")
        return logic.formatar_preco(preco)

    # ---------- on-chain ----------
    def loop_onchain(self):
        n = 0
        while True:
            try:
                altura, ts = onchain.ultimo_bloco()
                with self.lock:
                    self.eventos.append(("tip", altura, ts))
            except Exception:
                pass
            try:
                self.fee = onchain.fees()["halfHourFee"]
            except Exception:
                pass
            if n % 10 == 0:
                try:
                    self.hash = onchain.hashrate()
                except Exception:
                    pass
            if n % 2 == 0:
                try:
                    self.gas = onchain.gas_eth()
                except Exception:
                    pass
                end = self.cfg.get("carteira")
                if end:
                    try:
                        s = onchain.saldo_endereco(end)
                        with self.lock:
                            self.eventos.append(("saldo", s))
                    except Exception:
                        pass
            if n % 10 == 5 and ranking.ligado(self.cfg):  # a cada ~10 min, só se você ligou
                try:
                    ranking.enviar(self.cfg, self.status())
                except Exception:
                    pass
            n += 1
            time.sleep(60)

    def _processar_eventos(self):
        with self.lock:
            evs, self.eventos = self.eventos, []
        for ev in evs:
            if ev[0] == "update":
                self.update = ev[1]
                self.toast = [f"v{ev[1]['versao']} - clique aqui", 60, "NOVA VERSÃO!"]
                self.som.tocar("update")
                continue
            if ev[0] == "licenca":
                if not ev[1] and self.pro:
                    self.pro = False
                    self.cache_sprites.clear()
                    self.toast = [ev[2][:60], 40, "LICENÇA"]
                continue
            if ev[0] == "console":
                self.console_linhas = (self.console_linhas + ev[1])[-60:]
                continue
            if ev[0] == "tip":
                for h in self.estomago.novo_tip(ev[1], ev[2]):
                    self._comer(h)
                self.cfg["onchain"] = self.estomago.d
            elif ev[0] == "saldo":
                self.saldo = ev[1]
                delta = self.vigia.atualizar(ev[1]["total"])
                if delta > 0:
                    self.reacao = FRAMES * 3
                    self.frase_atual = f"+{delta:,} sats chegando! obrigado, fren".replace(",", ".")
                    self.som.tocar("moon")
                    self.toast = ["RECEBEU +%s sats" % f"{delta:,}".replace(",", "."), 22]
                elif delta < 0:
                    self.frase_atual = f"{delta:,} sats saíram... era pra HODL".replace(",", ".")
                    self.som.tocar("rekt")

    def _comer(self, altura, manual=False):
        self.comendo = 10
        self.bloco_comido = altura
        self.som.tocar("comer")
        if manual:
            return
        self.toast = [f"BLOCO #{altura:,} COMIDO".replace(",", "."), 18]
        self.frase_atual = random.choice(["nhac! bloco fresquinho", "hmm, gosto de transação",
                                          "esse bloco veio com bastante fee", "mais um tijolo da timechain"])
        self._ganhar_xp("bloco")
        if self.estomago.comidos >= 1:
            self._comemorar(self.conq.especial("genesis"))
        if self.estomago.comidos >= 100:
            self._comemorar(self.conq.especial("pow_100"))

    def _ganhar_xp(self, motivo, qtd=1):
        subiu = self.evo.ganhar(motivo, qtd) if motivo != "minuto" else self.evo.tick_minutos(qtd)
        self.cfg["evolucao"] = self.evo.d
        novo = evolucao.estagio(self.evo.xp, self.conq.d["crashes"])
        if novo != self.estagio:
            self.estagio = novo
            self.toast = [f"EVOLUIU: {evolucao.NOMES[novo]}!", 26]
            self.reacao = FRAMES * 3
            self.som.tocar("evoluir")
            if novo == "whale":
                self._comemorar(self.conq.especial("whale_alert"))
            if novo == "diamond":
                self._comemorar(self.conq.especial("diamond_hands"))
        elif subiu:
            self.frase_atual = f"LEVEL UP! nível {evolucao.nivel(self.evo.xp)}"
        if evolucao.nivel(self.evo.xp) >= 21:
            self._comemorar(self.conq.especial("lv21"))

    def revelar_satoshi(self):
        segredos = self.cfg.setdefault("segredos", [])
        if "satoshi" not in segredos:
            segredos.append("satoshi")
        self._preencher_skins()
        self.cfg["skin"] = "satoshi"
        config.salvar(self.cfg)
        self.frase_atual = "eu sou Satoshi... ou não?"
        self._comemorar(self.conq.especial("konami"))
        self._desenhar()

    # ---------- carinho, vida, conquistas ----------
    def carinho(self):
        self.reacao = FRAMES * 2
        self.frase_atual = arts.reacao(self.estado)
        if self.cfg["moeda"] == "BTC":
            self.cliques_btc += 1
            if self.cliques_btc % 5 == 0 and self.bloco:  # easter egg do halving
                faltam, dias, n = lore.halving(self.bloco)
                self.frase_atual = f"bloco {self.bloco:,}: halving #{n} em {faltam:,} blocos (~{dias:.0f} dias)".replace(",", ".")
                self._comemorar(self.conq.especial("halving_nerd"))
        self.som.tocar("clique")
        self._comemorar(self.conq.carinho())
        frase = self.frase_atual
        self._ganhar_xp("carinho")
        self.frase_atual = frase if "halving" in frase else self.frase_atual
        return self.frase_atual
        self._desenhar()

    def tick_vida(self):
        bonus = lore.ajuste_vida_fng(self.fng[0] if self.fng else None)
        crashes = self.conq.d["crashes"]
        self._comemorar(self.conq.tick(self.estado, 10, bonus))
        if self.conq.d["crashes"] > crashes:
            self._ganhar_xp("crash")
        self._ganhar_xp("minuto", 10)
        d = max(0.0, float(self.cfg.get("diversao", 100.0)) - 100 / (3 * 360))  # zera em ~3 h sem brincar
        self.cfg["diversao"] = d
        if d < 25 and random.random() < 0.15 and not self.toast:
            self.frase_atual = random.choice(["tô entediado... bora jogar? (P)", "quero brincar! aperta P",
                                              "pega uns sats comigo? (P)"])
        self._salvar_progresso()
        self.root.after(10000, self.tick_vida)

    def _salvar_progresso(self):
        self.cfg["progresso"] = self.conq.d
        self.cfg["onchain"] = self.estomago.d
        self.cfg["evolucao"] = self.evo.d
        config.salvar(self.cfg)

    def _comemorar(self, novas):
        for cid in novas:
            self.toast = [conquistas.LISTA[cid][0], 22]  # ~4s em frames de 180ms
            self.som.tocar("conquista")
            self._salvar_progresso()

    # ---------- threads de rede (nunca tocam na GUI) ----------
    def loop_api(self):
        espera = config.INTERVALO
        while True:
            simbolos = list(config.MOEDAS) if self.pro else ["BTC"]
            try:
                novos = logic.buscar_precos(simbolos)
                with self.lock:
                    self.precos.update(novos)
                    for m, p in novos.items():
                        self.historico.adicionar(m, p)
                    self.erro = None
                espera = config.INTERVALO
            except logic.RateLimit:
                self.erro = "API pediu calma..."
                espera = min(espera * 2, 300)
            except Exception as erro:
                self.erro = "Sem sinal da API"
                print("API deu ruim (igual sua carteira):", erro)
            time.sleep(espera)

    def loop_lore(self):
        while True:
            try:
                self.fng = lore.fear_greed()
            except Exception:
                pass
            try:
                self.bloco = lore.altura_bloco()
            except Exception:
                pass
            time.sleep(600)  # a cada 10 min: as duas APIs são grátis, não abuse

    # ---------- desenho ----------
    def _variacao(self, moeda, preco):
        refs = self.cfg["preco_referencia"]
        if not self.pro or moeda not in refs:
            refs = self.__dict__.setdefault("_refs_sessao", {})
            refs.setdefault(moeda, preco)
        return logic.variacao_pct(preco, refs[moeda])

    def _caminho_folha(self):
        moeda, skin = self.cfg["moeda"], self.cfg["skin"]
        if skin.startswith("plugin:"):
            return self.plugins[skin]["_folha"]
        caminho = recursos.ASSETS / "sprites" / nome_folha(moeda, skin, self.estagio)
        if not caminho.exists():  # estágio sem folha? volta pro adulto, ninguém fica invisível
            caminho = recursos.ASSETS / "sprites" / nome_folha(moeda, skin, "adulto")
        return caminho

    def _sprites(self):
        chave = (self.cfg["moeda"], self.cfg["skin"], self.cfg.get("crt"), self.estagio, self._chapeu())
        if chave not in self.cache_sprites:
            self.cache_sprites[chave] = carregar_frames(self._caminho_folha(), self.escala, self.cfg.get("crt"),
                                                        self._chapeu())
        return self.cache_sprites[chave]

    def _txt(self, x, y, texto, cor, anchor="center", escala=1, max_chars=None, sombra=None, tags=()):
        img = self.fonte.imagem(texto, cor, escala, max_chars, sombra)
        self.cv.create_image(x, y, image=img, anchor=anchor, tags=tags)

    def _moldura(self, x0, y0, x1, y1, fundo, borda=C_TINTA, luz=None, sombra=None, tags=()):
        """Caixa 16-bit: borda com cantos mordidos, brilho em cima e sombra embaixo."""
        P, c = 3, self.cv
        c.create_rectangle(x0 + P, y0, x1 - P, y1, fill=borda, width=0, tags=tags)
        c.create_rectangle(x0, y0 + P, x1, y1 - P, fill=borda, width=0, tags=tags)
        c.create_rectangle(x0 + P, y0 + P, x1 - P, y1 - P, fill=fundo, width=0, tags=tags)
        if luz:
            c.create_rectangle(x0 + P, y0 + P, x1 - P, y0 + 2 * P - 1, fill=luz, width=0, tags=tags)
        if sombra:
            c.create_rectangle(x0 + P, y1 - 2 * P + 1, x1 - P, y1 - P, fill=sombra, width=0, tags=tags)
        if self.cfg.get("crt"):  # scanlines sólidas (stipple não funciona no Mac)
            h = fundo.lstrip("#")
            escuro = "#%02x%02x%02x" % tuple(int(h[i:i + 2], 16) * 17 // 20 for i in (0, 2, 4))
            for y in range(y0 + P + 2, y1 - P, 3):
                c.create_line(x0 + P, y, x1 - P, y, fill=escuro, tags=tags)

    def _coracao(self, x, y, esq, dir_, P=3):
        forma = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
        for j, row in enumerate(forma):
            for i, b in enumerate(row):
                if b == "1":
                    self.cv.create_rectangle(x + i * P, y + j * P, x + i * P + P - 1, y + j * P + P - 1,
                                             fill=esq if i < 4 else dir_, width=0)
        self.cv.create_rectangle(x + P, y + P, x + 2 * P - 1, y + 2 * P - 1, fill="#ffffff", width=0)

    def _sparkline(self, moeda, x0, y0, x1, y1, cor):
        serie = self.historico.serie(moeda, (x1 - x0) // 3)
        c = self.cv
        c.create_rectangle(x0, y0, x1, y1, fill="#1a1428", width=0)
        if len(serie) < 2:
            self._txt((x0 + x1) // 2, (y0 + y1) // 2, "...", "#6a5a8a")
            return
        lo, hi = min(serie), max(serie)
        h = (y1 - y0 - 3) // 3
        ant = None
        for i, v in enumerate(serie):
            n = 0 if hi == lo else round((v - lo) / (hi - lo) * h)
            x, y = x0 + 1 + i * 3, y1 - 2 - n * 3
            topo, base = (y, y) if ant is None else (min(y, ant), max(y, ant))
            c.create_rectangle(x, topo - 1, x + 2, base + 1, fill=cor, width=0)
            ant = y

    def _paleta(self):
        """(painel, painel2, sombra, destaque, ícone) conforme hora local / alto contraste."""
        if self.cfg.get("alto_contraste"):
            return juice.ALTO_CONTRASTE
        if not self.cfg.get("dia_noite", True):
            return juice.PERIODOS["noite"]
        return juice.PERIODOS[juice.periodo()]

    def _desenhar(self):
        if self.cena:
            self.cena.desenhar()
            return
        moeda = self.cfg["moeda"]
        ac = bool(self.cfg.get("alto_contraste"))
        pal = self._paleta()
        dormindo = self.estomago.dormindo() and moeda == "BTC" and not self.reacao
        with self.lock:
            preco = self.precos.get(moeda)
        if preco is not None:
            var = self._variacao(moeda, preco)
            novo = logic.estado_do_bicho(var, self.cfg["limite_alta"], self.cfg["limite_queda"])
            if self.estado_forcado and time.time() < self.estado_forcado[1]:
                novo = self.estado_forcado[0]  # sudo moon
            if novo != self.estado:
                self.estado = novo
                self.som.tocar(novo)
                self._nova_frase()
                if novo in ("moon", "rekt") and self.cfg.get("juice", True):
                    self.juice.emitir(novo, self.LARG // 2, self.Y_SPRITE + self.S // 2, self.escala)
            linha_preco, linha_var = self._fmt_preco(moeda, preco), f"{'+' if var >= 0 else ''}{var:.2f}%"
        else:
            linha_preco, linha_var = "carregando", "..."
        cor = arts.CORES[self.estado]
        c, L = self.cv, self.LARG
        c.delete("all")
        mc = (L - 30) // 8  # colunas que cabem no balão
        # ----- balão / toast -----
        if dormindo and not self.toast and not self.console_aberto:
            self.frase_atual = "esperando bloco... zzz"
        if self.toast:
            fundo = "#ffff00" if ac else ("#73eff7" if len(self.toast) > 2 and self.update else "#ffcd75")
            self._moldura(6, 2, L - 6, 48, fundo, luz=None if ac else "#fff4c0", sombra=None if ac else "#ef7d57")
            self._txt(L // 2, 16, self.toast[2] if len(self.toast) > 2 else "CONQUISTA!", C_TINTA if ac else "#b13e53")
            self._txt(L // 2, 32, self.toast[0], C_TINTA, max_chars=mc)
        else:
            fundo = "#ffffff" if ac else C_PAPEL
            self._moldura(6, 2, L - 6, 48, fundo, luz="#ffffff", sombra=None if ac else "#94b0c2")
            self._txt(L // 2, 25, self.frase_atual, C_TINTA, max_chars=mc)
        m = L // 2
        for i, w in enumerate((8, 5, 2)):
            c.create_rectangle(m - w - 3, 45 + i * 3, m + w + 3, 48 + i * 3, fill=C_TINTA, width=0)
            c.create_rectangle(m - w, 45 + i * 3, m + w, 48 + i * 3, fill=fundo, width=0)
        # ----- bicho -----
        frames = self._sprites()
        if self.reacao or (self.comendo and self.comendo <= 4):
            img = frames[("pulo", (FRAMES * 2 - max(self.reacao, self.comendo)) % FRAMES)]
        elif dormindo:
            img = frames[("garimpando", 3)]  # olhinho fechado
        else:
            img = frames[(self.estado, self.frame)]
        tremor = random.randint(-3, 3) if self.panico_t else 0
        sx, sy = self.juice.deslocamento() if self.cfg.get("juice", True) else (0, 0)
        cy = self.Y_SPRITE + self.S // 2
        c.create_image(L // 2 + tremor + sx, cy + sy, image=img)
        if self.cfg.get("juice", True):
            self.juice.desenhar(c)
        E = self.escala
        if dormindo:  # Zzz subindo
            for i in range(3):
                k = (self.frame + i * 2) % 6
                self._txt(L // 2 + self.S // 3 + i * 8, cy - self.S // 3 - k * 4 - i * 6, "z" if i < 2 else "Z",
                          "#94b0c2", sombra=C_TINTA)
        if onchain.fome_por_fee(self.fee)[0] >= 2 and not dormindo:  # suando de fome (fee alta)
            for i, dx in enumerate((-self.S // 4, self.S // 4)):
                yy = cy - self.S // 4 + ((self.frame + i * 2) % 4) * E * 2
                c.create_rectangle(L // 2 + dx, yy, L // 2 + dx + E, yy + E * 2, fill="#73eff7", width=0)
        if self.comendo > 4:  # bloquinho laranja voando até a boca
            t = (10 - self.comendo) / 6
            bx = int(L - 24 - (L - 24 - L // 2) * t)
            by = int(self.Y_SPRITE + 8 + (self.S // 2 - 8) * t * t)
            tam = 4 * E
            c.create_rectangle(bx - tam, by - tam, bx + tam, by + tam, fill="#1a1c2c", width=0)
            c.create_rectangle(bx - tam + E, by - tam + E, bx + tam - E, by + tam - E, fill="#ef7d57", width=0)
            c.create_rectangle(bx - tam + E, by - tam + E, bx + tam - E, by - tam + 2 * E, fill="#ffcd75", width=0)
            self._txt(bx, by, "B", "#f4f4f4")
        elif self.comendo:  # migalhas
            for i in range(5):
                ang = i * 1.3 + self.comendo
                r = (5 - self.comendo) * E * 3
                c.create_rectangle(L // 2 + int(math.cos(ang) * r), cy + int(math.sin(ang) * r) - E * 4,
                                   L // 2 + int(math.cos(ang) * r) + E, cy + int(math.sin(ang) * r) - E * 3,
                                   fill="#ef7d57", width=0)
        if self.reacao:
            k = FRAMES * 2 - self.reacao
            for dx, ph in ((-self.S // 2 - 6, 0), (self.S // 2 - 8, 2), (-self.S // 2 + 10, 4)):
                self._coracao(L // 2 + dx, self.Y_SPRITE + self.S // 2 - (k + ph) * 6, "#b13e53", "#b13e53")
        # ----- nome e vida -----
        nome = self.nome_pet()
        if ac:
            cor = {"moon": "#00ff00", "rekt": "#ff5555", "garimpando": "#ffff00"}[self.estado]
        self._txt(L // 2, self.Y_NOME, f"{nome} - {arts.TITULOS[self.estado]}", cor,
                  max_chars=(L - 12) // 8, sombra=C_TINTA)
        self._txt(10, self.Y_VIDA + 2, "VIDA", "#f4f4f4", anchor="nw", sombra=C_TINTA)
        vida = self.conq.vida
        for i in range(5):
            r = vida - i * 2
            self._coracao(48 + i * 24, self.Y_VIDA, "#b13e53" if r >= 1 else "#4a3a5a",
                          "#b13e53" if r >= 2 else "#4a3a5a")
        # ----- nível + barra de XP -----
        y = self.Y_XP
        nv = evolucao.nivel(self.evo.xp)
        self._txt(10, y, f"LV{nv:<2}", "#ffcd75", anchor="nw", sombra=C_TINTA)
        bx0, bx1 = 48, L - 10 - 8 * min(13, len(evolucao.NOMES[self.estagio])) - 6
        c.create_rectangle(bx0, y, bx1, y + 8, fill=C_TINTA, width=0)
        c.create_rectangle(bx0 + 2, y + 2, bx1 - 2, y + 6, fill="#333c57", width=0)
        cheio = int((bx1 - bx0 - 4) * evolucao.progresso_nivel(self.evo.xp))
        if cheio > 0:
            c.create_rectangle(bx0 + 2, y + 2, bx0 + 2 + cheio, y + 6, fill="#41a6f6", width=0)
            c.create_rectangle(bx0 + 2, y + 2, bx0 + 2 + cheio, y + 3, fill="#73eff7", width=0)
        self._txt(L - 10, y, evolucao.NOMES[self.estagio][:13], "#73eff7", anchor="ne", sombra=C_TINTA)
        # ----- painel -----
        y = self.Y_PAINEL
        self._moldura(6, y, L - 6, y + 60, pal[0], borda="#ffffff" if ac else C_TINTA, luz=pal[1], sombra=pal[2])
        if not ac:
            juice.desenhar_icone_ceu(c, L // 2 - 7, y + 8, pal[4], self.frame)
        self._txt(16, y + 10, ("PRO " if self.pro else "") + moeda, "#ffcd75" if self.pro else "#f4f4f4", anchor="nw")
        self._txt(L - 16, y + 10, linha_var, cor, anchor="ne")
        if self.update and not self.toast:
            self._txt(L // 2 + 12, y + 10, "UPD", "#73eff7", anchor="nw")
        self._txt(16, y + 26, self.erro or linha_preco, "#ef7d57" if self.erro else "#f4f4f4", anchor="nw")
        if self.pro:
            self._sparkline(moeda, L - 92, y + 22, L - 16, y + 38, cor)
        else:
            self._txt(L - 16, y + 26, "PRO:graf", "#566c86", anchor="ne")
        info = self._infos_nerd(moeda)
        if info:
            txt, cor_i = info[(self.rodizio // 22) % len(info)]
            self._txt(16, y + 42, txt[:(L - 32) // 8], cor_i, anchor="nw")
        # ----- botão de afiliado -----
        y = self.Y_BOTAO
        self._moldura(6, y, L - 6, y + 36, "#ef7d57", luz="#ffcd75", sombra="#b13e53", tags=("botao",))
        self._txt(L // 2, y + 18, "COMPRAR A QUEDA ANTES\nQUE ELE MORRA!", C_TINTA, tags=("botao",))
        if self.console_aberto:
            self._desenhar_console()

    def _infos_nerd(self, moeda):
        """Linhas que se revezam no painel: F&G, fee, bloco, hashrate, gas, carteira."""
        out = []
        if self.fng:
            v, rot = self.fng
            out.append((f"F&G {v} {rot}", "#38b764" if v >= 55 else "#b13e53" if v <= 45 else "#ffcd75"))
        if self.fee is not None:
            out.append((f"FEE {self.fee} sat/vB {onchain.fome_por_fee(self.fee)[1]}", "#ef7d57"))
        if self.estomago.d.get("altura"):
            out.append((f"BLOCO {self.estomago.d['altura']} NHAC:{self.estomago.comidos}", "#94b0c2"))
        if self.hash:
            out.append((f"HASH {onchain.formatar_hashrate(self.hash)}", "#a7f070"))
        if moeda == "ETH" and self.gas:
            out.append((f"GAS {self.gas:.1f} gwei", "#73eff7"))
        if self.saldo:
            out.append((f"WALLET {self.saldo['total']:,} sats".replace(",", "."), "#ffcd75"))
        return out

    def _desenhar_console(self):
        """Terminal verde-fósforo por cima do bicho. Fonte pixel, cursor piscando."""
        c, L = self.cv, self.LARG
        y0, y1 = 2, self.Y_PAINEL - 4
        self._moldura(4, y0, L - 4, y1, "#0b0f14", borda="#38b764", luz="#122018")
        cols = (L - 20) // 8
        linhas_vis = (y1 - y0 - 30) // 10
        render = []
        for ln in self.console_linhas:
            if ln == SPRITE:
                render.append(SPRITE)
            else:
                render += self.fonte.quebrar(ln, cols) or [""]
        render = render[-linhas_vis:]
        y = y0 + 8
        for ln in render:
            if ln == SPRITE:  # neofetch: o próprio bicho no terminal
                img = self.__dict__.setdefault("_mini", {}).get((self.cfg["moeda"], self.cfg["skin"], self.estagio))
                if img is None:
                    caminho = (self.plugins[self.cfg["skin"]]["_folha"] if self.cfg["skin"].startswith("plugin:")
                               else recursos.ASSETS / "sprites" / nome_folha(self.cfg["moeda"], self.cfg["skin"], self.estagio))
                    img = carregar_frames(caminho, 1)[("garimpando", 0)]
                    self._mini[(self.cfg["moeda"], self.cfg["skin"], self.estagio)] = img
                c.create_image(L - 12, y, image=img, anchor="ne")
                continue
            cor = "#a7f070" if ln.startswith(">") else "#38b764"
            self._txt(12, y, ln, cor, anchor="nw")
            y += 10
        cursor = "_" if self.frame % 2 == 0 else " "
        self._txt(12, y1 - 18, ("$ " + self.console_input + cursor)[-cols:], "#f4f4f4", anchor="nw")

    def _nova_frase(self):
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
        self._desenhar()

    def trocar_frase(self):
        self._nova_frase()
        self.root.after(FRASE_MS, self.trocar_frase)

    def _checar_alertas(self):
        for moeda, alvo in self.cfg["alertas"].items():
            preco = self.precos.get(moeda)
            if preco is None:
                continue
            msg = logic.checar_alerta(preco, alvo)
            if msg and moeda not in self.alertados:
                self.alertados.add(moeda)
                self._popup(f"{moeda} {msg}")
            elif not msg:
                self.alertados.discard(moeda)

    def _popup(self, texto):
        if not self.som.tocar("alerta"):
            self.root.bell()
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        p.configure(bg=C_TINTA)
        img = self.fonte.imagem("ALERTA! " + texto.replace("🚀", "").replace("💀", ""), C_TINTA, 1, 28)
        tk.Label(p, image=img, bg="#ffcd75", padx=10, pady=8).pack(padx=3, pady=3)
        p._img = img
        p.geometry(f"+{self.root.winfo_x()}+{max(0, self.root.winfo_y() - 60)}")
        p.bind("<Button-1>", lambda e: p.destroy())
        p.after(6000, p.destroy)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Tamagoshi().run()
