"""menus.py - menu do botão direito (enxuto: o resto mora na tela de Ajustes) e os helpers aplicar_*.

Mixin do SatoshiPet (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import tkinter as tk

from . import (
    __version__,
    arts,
    cenas,
    config,
    i18n,
    licencas,
    ranking,
    sistema,
)
from .graficos import (
    C_TINTA,
    SKINS_PRO,
)


class MixinMenus:
    # ---------- menu ----------
    def _montar_menu(self):
        """Menu enxuto: atalhos de ação. Opções/ligações moram em Ajustes (S). Rótulos passam pelo i18n."""
        t = i18n.t
        m = tk.Menu(self.root, tearoff=0)
        self.menu_moedas = tk.Menu(m, tearoff=0)
        for s in config.MOEDAS:
            self.menu_moedas.add_command(label=f"{s} - {arts.NOMES[s]}" + ("" if s == "BTC" else "  [Pro]"),
                                         command=lambda s=s: self.trocar_moeda(s))
        self.menu_skins = tk.Menu(m, tearoff=0)
        self._preencher_skins()
        m.add_command(label=t("Ajustes... (S)"), command=self.abrir_ajustes)
        m.add_separator()
        m.add_cascade(label=t("Trocar moeda"), menu=self.menu_moedas)
        m.add_cascade(label=t("Trocar skin"), menu=self.menu_skins)
        m.add_command(label=t("Conquistas"), command=self.ver_conquistas)
        m.add_command(label=t("Console hacker (`)"), command=self.alternar_console)
        m.add_command(label=t("Compartilhar card (X)"), command=self._menu_share)
        m.add_command(label=t("Brincar: Pega os Sats (P)"), command=self.brincar)
        self.menu_genetica(m)
        mm = tk.Menu(m, tearoff=0)
        mm.add_command(label=t("Corretora de mentirinha (paper trading)"), command=self.abrir_corretora)
        m.add_cascade(label=t("Mercado"), menu=mm)
        ml = tk.Menu(m, tearoff=0)
        ml.add_command(label=t("Abrir loja de skins"), command=self.abrir_loja)
        ml.add_command(label=t("Resgatar código..."), command=self._menu_resgatar)
        ml.add_command(label=t("Overlay de streamer (OBS + Twitch)..."), command=self.config_twitch)
        m.add_cascade(label=t("Loja de skins"), menu=ml)
        mh = tk.Menu(m, tearoff=0)
        mh.add_command(label=t("Rever introdução"), command=self.rever_intro)
        mh.add_command(label=t("Procurar atualização"), command=self.checar_update_agora)
        mh.add_command(label=t("Enviar relatório de erro..."), command=self.enviar_relatorio)
        mh.add_command(label=f"SatoshiPet v{__version__}", state="disabled")
        m.add_cascade(label=t("Ajuda"), menu=mh)
        m.add_command(label=t("Esconder (bandeja)"), command=self.esconder,
                      state="normal" if sistema.tray_disponivel(self.cfg.get("menubar_mac")) else "disabled")
        m.add_separator()
        m.add_command(label=t("Ativar Pro"), command=self.ativar_pro)
        m.add_command(label=t("Sair"), command=self.sair)
        self.menu = m

    def _preencher_skins(self):
        ms = self.menu_skins
        ms.delete(0, "end")
        for sk in arts.SKINS_DISPONIVEIS:
            ms.add_command(label=sk + ("  [Pro]" if sk in SKINS_PRO else ""),
                           command=lambda sk=sk: self.trocar_skin(sk))
        for sk in sorted(self.cfg.get("segredos", [])):
            ms.add_command(label=f"{sk}  [secreta]", command=lambda sk=sk: self.trocar_skin(sk))
        packs = [pid for pid in self.catalogo if self.pack_liberado(pid)]
        if packs:
            ms.add_separator()
            for pid in packs:
                m = self.catalogo[pid]
                ms.add_command(label=f"{m['nome']}  [loja" + (", patrocinado]" if m["tipo"] == "patrocinado" else "]"),
                               command=lambda pid=pid: self.trocar_skin("loja:" + pid))
        if self.plugins:
            ms.add_separator()
            for pid, meta in self.plugins.items():
                ms.add_command(label=f"{meta['nome']} (por {meta['autor']})",
                               command=lambda pid=pid: self.trocar_skin(pid))

    def abrir_menu(self, e):
        self.menu.entryconfig(self.menu.index("end") - 1, label=i18n.t("Pro ativo" if self.pro else "Ativar Pro"))
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    # ---------- v1.5: tudo que era diálogo agora mora na tela de Ajustes ----------
    def abrir_ajustes(self, aba="geral", msg=""):
        from .ajustes import Ajustes
        self.console_aberto = False
        self.cena = Ajustes(self, aba)
        sistema.focar_teclado(self.root, self.cv)
        if msg:
            self.cena._dizer(msg)
        self._desenhar()

    def configuracoes(self):
        self.abrir_ajustes("grana")

    def config_alertas(self):
        self.abrir_ajustes("grana")

    def config_carteira(self):
        self.abrir_ajustes("grana")

    def config_ranking(self):
        self.abrir_ajustes("conta")

    def ativar_pro(self):
        self.abrir_ajustes("conta", "Pro ativo" if self.pro else "")

    def definir_idioma(self, escolha):
        self.cfg["idioma"] = escolha
        i18n.definir(escolha)
        config.salvar(self.cfg)
        self._montar_menu()  # menu do Tk não passa pelo _txt: remonta traduzido

    def autostart_ligado(self):
        return sistema.autostart_ativo()

    def autostart_suportado(self):
        return sistema.autostart_suportado()

    def avisar(self, linhas, titulo="INFO", ticks=40):
        """Substitui o messagebox.showinfo: vira toast no estilo do app (e cai no console pra reler)."""
        linhas = [linhas] if isinstance(linhas, str) else [str(x) for x in linhas if x]
        if not linhas:
            return
        self.toast = [linhas[0][:60], ticks, titulo]
        self.console_linhas = (self.console_linhas + [f"[{titulo.lower()}] " + x for x in linhas])[-60:]

    def aplicar_limites(self, alta=None, queda=None, ref=None):
        if not self.pro:
            return False
        if alta is not None:
            self.cfg["limite_alta"] = round(max(0.5, min(50.0, abs(float(alta)))), 2)
        if queda is not None:
            self.cfg["limite_queda"] = round(-max(0.5, min(50.0, abs(float(queda)))), 2)
        if ref is not None:
            moeda = self.cfg["moeda"]
            if ref > 0:
                self.cfg["preco_referencia"][moeda] = float(ref)
            else:
                self.cfg["preco_referencia"].pop(moeda, None)
        config.salvar(self.cfg)
        return True

    def aplicar_alertas(self, acima=None, abaixo=None):
        if not self.pro:
            return False
        moeda = self.cfg["moeda"]
        self.cfg["alertas"][moeda] = {k: float(v) for k, v in (("acima", acima), ("abaixo", abaixo))
                                      if v and float(v) > 0}
        self.alertados.discard(moeda)
        config.salvar(self.cfg)
        return True

    def aplicar_carteira(self, endereco):
        """BTC watch-only. Vazio = remover. Devolve linhas de resposta (mesmas do console)."""
        if not (endereco or "").strip():
            self.cfg["carteira"] = ""
            self.saldo = None
            config.salvar(self.cfg)
            return ["carteira removida"]
        return self.carteira(endereco.strip())

    def aplicar_licenca(self, email, chave):
        email, chave = (email or "").strip(), (chave or "").strip()
        if not email or not chave:
            return licencas.Resultado(False, "preencha e-mail e chave")
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            res = licencas.verificar(self.cfg, email, chave, forcar=True)
        finally:
            self.root.config(cursor="")
        if res.ok:
            self.pro = True
            hmac_ = (self.cfg.get("licenca_provedor") or "hmac") == "hmac"
            self.cfg["email"], self.cfg["licenca"] = email.lower(), chave.upper() if hmac_ else chave
            config.salvar(self.cfg)
            self.cache_sprites.clear()
            self.som.tocar("conquista")
        return res

    def ligar_ranking(self, url, nick):
        self.cfg["ranking_url"] = (url or "").strip()
        return ranking.comando(self.cfg, self.status(), ["on", (nick or "").strip()], config.salvar)

    def _exige_pro(self):
        if self.pro:
            return True
        from .ajustes import Ajustes
        if isinstance(self.cena, Ajustes):
            self.cena._dizer("precisa do Pro")
        else:
            self.abrir_ajustes("conta", "precisa do Pro")
        return False

    def ver_conquistas(self):
        self.avisar(self.conq.resumo().split("\n"), "CONQUISTAS", 50)

    def alternar_mudo(self):
        self.som.mudo = self.cfg["mudo"] = bool(self.var_mudo.get())
        config.salvar(self.cfg)

    def alternar_crt(self):
        self.cfg["crt"] = bool(self.var_crt.get()) if hasattr(self, "var_crt") else not self.cfg.get("crt")
        self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def alternar_autostart(self):
        if not self._exige_pro():
            return
        if not sistema.definir_autostart(not sistema.autostart_ativo()):
            self.avisar("Não consegui configurar a inicialização automática.", "OPS")

    def _menu_share(self):
        self.avisar(self.compartilhar(), "SHARE")

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

    # ---------- acessibilidade e juice ----------
    def mudar_escala(self, e):
        self.escala = self.cfg["escala"] = max(1, min(6, int(e)))
        self._medidas()
        self.cv.config(width=self.LARG, height=self.ALT)
        self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def alternar_opcao(self, chave, var=None):
        padrao = config.PADRAO.get(chave, False)
        self.cfg[chave] = bool(var.get()) if var is not None else not self.cfg.get(chave, padrao)
        if chave == "crt":
            self.cache_sprites.clear()
        if chave == "musica":
            self.som.musica(self.cfg["musica"])
        if chave == "chapeus":
            self.cache_sprites.clear()
        config.salvar(self.cfg)
        self._desenhar()

    def rever_intro(self):
        self.cena = cenas.Onboarding(self)
        sistema.focar_teclado(self.root, self.cv)
        self._desenhar()
