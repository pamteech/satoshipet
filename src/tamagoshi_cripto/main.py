"""main.py - Tamagoshi Cripto: o bichinho que sente o mercado mais que você.

Free: BTC, pixel art animada, carinho, vida, conquistas, sons, lore (F&G, halving),
      skins da comunidade, terminal mode, bandeja, afiliado.
Pro:  5 moedas, skins premium, ajustes, alertas, sparkline e iniciar com o sistema.
"""
import base64
import io
import math
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog

from PIL import Image

from . import arts, config, conquistas, license, logic, lore, plugins, recursos, sistema, sons
from .fonte import FontePixel
from .sprites import FRAMES, LINHAS, SKINS_SECRETAS

COR_TRANSP = "#010101"   # cor-chave que vira buraco no Windows
FRAME_MS = 180           # 4 frames por loop ~ 0,7s
FRASE_MS = 10000
SKINS_PRO = {"cyberpunk", "gato", "sapo"}

C_TINTA, C_PAPEL, C_PAINEL, C_PAINEL2 = "#1a1c2c", "#f4f4f4", "#29213f", "#3e3466"


def _png_para_tk(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def carregar_frames(caminho, escala, crt=False):
    """Folha 192x192 -> {(linha, frame): PhotoImage} ampliado sem borrar (+ scanlines CRT)."""
    folha = Image.open(caminho).convert("RGBA")
    frames = {}
    for j, linha in enumerate(LINHAS):
        for f in range(FRAMES):
            fr = folha.crop((f * 48, j * 48, (f + 1) * 48, (j + 1) * 48))
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
        self.pro = license.validar(self.cfg.get("email"), self.cfg.get("licenca"))
        self.plugins = plugins.descobrir(op.get("skins_dir"))
        self._aplicar_limites_free()

        self.precos, self.erro = {}, None
        self.lock = threading.Lock()
        self.frame, self.estado = 0, "garimpando"
        self.alertados = set()
        self.historico = logic.Historico()
        self.conq = conquistas.Conquistas(self.cfg.get("progresso"))
        self.som = sons.Som(mudo=self.cfg.get("mudo", False))
        self.reacao = 0            # frames restantes do pulo
        self.toast = None
        self.fng = None            # (valor, rótulo)
        self.bloco = None
        self.konami = lore.Konami()
        self.cliques_btc = 0
        self.cache_sprites = {}
        self.frase_atual = "gm, fren!"
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
        self._desenhar()
        threading.Thread(target=self.loop_api, daemon=True).start()
        threading.Thread(target=self.loop_lore, daemon=True).start()
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
        self.Y_PAINEL = y + 34
        self.Y_BOTAO = self.Y_PAINEL + 66
        self.ALT = self.Y_BOTAO + 40
        cx = self.LARG // 2
        self.SPRITE_BOX = (cx - S // 2, self.Y_SPRITE, cx + S // 2, self.Y_SPRITE + S)

    def _erro_tk(self, exc, val, tb):
        import traceback
        self.ultimo_erro = "".join(traceback.format_exception(exc, val, tb))
        print(self.ultimo_erro)

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
        if license.validar(email, chave or ""):
            self.pro = True
            self.cfg["email"], self.cfg["licenca"] = email.strip().lower(), chave.strip().upper()
            config.salvar(self.cfg)
            messagebox.showinfo("Pro ativado!", "Bem-vindo ao clube das mãos de diamante!", parent=self.root)
        else:
            messagebox.showerror("Ops", "Chave inválida. Confere o e-mail e a chave, hein?", parent=self.root)

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
        self._x, self._y = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()
        self._press = (e.x_root, e.y_root, e.x, e.y)
        self.root.focus_force()  # pra janela sem borda receber o código konami

    def arrastando(self, e):
        self.root.geometry(f"+{e.x_root - self._x}+{e.y_root - self._y}")

    def fim_arraste(self, e):
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
        if self.konami.alimentar(e.keysym):
            self.revelar_satoshi()

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
        self._desenhar()

    def tick_vida(self):
        bonus = lore.ajuste_vida_fng(self.fng[0] if self.fng else None)
        self._comemorar(self.conq.tick(self.estado, 10, bonus))
        self._salvar_progresso()
        self.root.after(10000, self.tick_vida)

    def _salvar_progresso(self):
        self.cfg["progresso"] = self.conq.d
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

    def _sprites(self):
        moeda, skin = self.cfg["moeda"], self.cfg["skin"]
        chave = (moeda, skin, self.cfg.get("crt"))
        if chave not in self.cache_sprites:
            if skin.startswith("plugin:"):
                caminho = self.plugins[skin]["_folha"]
            else:
                caminho = recursos.sheet_path(moeda, skin)
            self.cache_sprites[chave] = carregar_frames(caminho, self.escala, self.cfg.get("crt"))
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

    def _desenhar(self):
        moeda = self.cfg["moeda"]
        with self.lock:
            preco = self.precos.get(moeda)
        if preco is not None:
            var = self._variacao(moeda, preco)
            novo = logic.estado_do_bicho(var, self.cfg["limite_alta"], self.cfg["limite_queda"])
            if novo != self.estado:
                self.estado = novo
                self.som.tocar(novo)
                self._nova_frase()
            linha_preco, linha_var = logic.formatar_preco(preco), f"{'+' if var >= 0 else ''}{var:.2f}%"
        else:
            linha_preco, linha_var = "carregando", "..."
        cor = arts.CORES[self.estado]
        c, L = self.cv, self.LARG
        c.delete("all")
        mc = (L - 30) // 8  # colunas que cabem no balão
        # ----- balão / toast -----
        if self.toast:
            fundo = "#ffcd75"
            self._moldura(6, 2, L - 6, 48, fundo, luz="#fff4c0", sombra="#ef7d57")
            self._txt(L // 2, 16, "CONQUISTA!", "#b13e53")
            self._txt(L // 2, 32, self.toast[0], C_TINTA, max_chars=mc)
        else:
            fundo = C_PAPEL
            self._moldura(6, 2, L - 6, 48, fundo, luz="#ffffff", sombra="#94b0c2")
            self._txt(L // 2, 25, self.frase_atual, C_TINTA, max_chars=mc)
        m = L // 2
        for i, w in enumerate((8, 5, 2)):
            c.create_rectangle(m - w - 3, 45 + i * 3, m + w + 3, 48 + i * 3, fill=C_TINTA, width=0)
            c.create_rectangle(m - w, 45 + i * 3, m + w, 48 + i * 3, fill=fundo, width=0)
        # ----- bicho -----
        frames = self._sprites()
        if self.reacao:
            img = frames[("pulo", (FRAMES * 2 - self.reacao) % FRAMES)]
        else:
            img = frames[(self.estado, self.frame)]
        c.create_image(L // 2, self.Y_SPRITE + self.S // 2, image=img)
        if self.reacao:
            k = FRAMES * 2 - self.reacao
            for dx, ph in ((-self.S // 2 - 6, 0), (self.S // 2 - 8, 2), (-self.S // 2 + 10, 4)):
                self._coracao(L // 2 + dx, self.Y_SPRITE + self.S // 2 - (k + ph) * 6, "#b13e53", "#b13e53")
        # ----- nome e vida -----
        nome = (self.plugins[self.cfg["skin"]]["nome"] if self.cfg["skin"].startswith("plugin:")
                else arts.NOMES[moeda])
        self._txt(L // 2, self.Y_NOME, f"{nome} - {arts.TITULOS[self.estado]}", cor,
                  max_chars=(L - 12) // 8, sombra=C_TINTA)
        self._txt(10, self.Y_VIDA + 2, "VIDA", "#f4f4f4", anchor="nw", sombra=C_TINTA)
        vida = self.conq.vida
        for i in range(5):
            r = vida - i * 2
            self._coracao(48 + i * 24, self.Y_VIDA, "#b13e53" if r >= 1 else "#4a3a5a",
                          "#b13e53" if r >= 2 else "#4a3a5a")
        # ----- painel -----
        y = self.Y_PAINEL
        self._moldura(6, y, L - 6, y + 60, C_PAINEL, luz=C_PAINEL2, sombra="#1d1730")
        self._txt(16, y + 10, ("PRO " if self.pro else "") + moeda, "#ffcd75" if self.pro else "#f4f4f4", anchor="nw")
        self._txt(L - 16, y + 10, linha_var, cor, anchor="ne")
        self._txt(16, y + 26, self.erro or linha_preco, "#ef7d57" if self.erro else "#f4f4f4", anchor="nw")
        if self.pro:
            self._sparkline(moeda, L - 92, y + 22, L - 16, y + 38, cor)
        else:
            self._txt(L - 16, y + 26, "PRO:graf", "#566c86", anchor="ne")
        if self.fng:
            v, rot = self.fng
            cor_f = "#38b764" if v >= 55 else "#b13e53" if v <= 45 else "#ffcd75"
            self._txt(16, y + 42, f"F&G {v} {rot}"[:(L - 32) // 8], cor_f, anchor="nw")
        elif moeda == "BTC" and self.bloco:
            self._txt(16, y + 42, f"BLOCO {self.bloco}", "#94b0c2", anchor="nw")
        # ----- botão de afiliado -----
        y = self.Y_BOTAO
        self._moldura(6, y, L - 6, y + 36, "#ef7d57", luz="#ffcd75", sombra="#b13e53", tags=("botao",))
        self._txt(L // 2, y + 18, "COMPRAR A QUEDA ANTES\nQUE ELE MORRA!", C_TINTA, tags=("botao",))

    def _nova_frase(self):
        extras = self.plugins.get(self.cfg["skin"], {}).get("frases")
        self.frase_atual = arts.frase(self.estado, self.cfg["moeda"], extras)

    # ---------- loops da GUI ----------
    def atualizar_tela(self):
        if self.pro:
            self._checar_alertas()
        self.root.after(1000, self.atualizar_tela)

    def animar(self):
        self.frame = (self.frame + 1) % FRAMES
        if self.reacao:
            self.reacao -= 1
        if self.toast:
            self.toast[1] -= 1
            if self.toast[1] <= 0:
                self.toast = None
        self._desenhar()
        self.root.after(FRAME_MS, self.animar)

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
