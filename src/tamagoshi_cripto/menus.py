"""menus.py - menu do botão direito e os diálogos antigos (Tk) que ainda sobraram.

Mixin do Tamagoshi (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import tkinter as tk
from tkinter import messagebox, simpledialog

from . import (
    __version__,
    arts,
    cenas,
    config,
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
        self.menu_genetica(m)
        mm = tk.Menu(m, tearoff=0)
        mm.add_command(label="Corretora de mentirinha (paper trading)", command=self.abrir_corretora)
        mm.add_command(label="Carteiras ETH/SOL watch-only...", command=self.config_carteiras_multi)
        for chave, rot in (("baleias", "Alerta de baleia (mempool.space)"), ("noticias", "Manchetes RSS no balão")):
            v = self.vars_op_m = getattr(self, "vars_op_m", {})
            v[chave] = tk.BooleanVar(value=bool(self.cfg.get(chave, True)))
            mm.add_checkbutton(label=rot, variable=v[chave], command=lambda c=chave: self.alternar_opcao(c, self.vars_op_m[c]))
        m.add_cascade(label="Mercado", menu=mm)
        ml = tk.Menu(m, tearoff=0)
        ml.add_command(label="Abrir loja de skins", command=self.abrir_loja)
        ml.add_command(label="Resgatar código...", command=self._menu_resgatar)
        ml.add_command(label="Overlay de streamer (OBS + Twitch)...", command=self.config_twitch)
        m.add_cascade(label="Loja de skins", menu=ml)
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
        self.menu.entryconfig(self.menu.index("end") - 1, label="Pro ativo" if self.pro else "Ativar Pro")
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

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

    def _exige_pro(self):
        if self.pro:
            return True
        if messagebox.askyesno("Recurso Pro", "Isso é coisa da versão Pro!\nQuer ativar sua licença agora?",
                               parent=self.root):
            self.ativar_pro()
        return self.pro

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

    def _menu_share(self):
        linhas = self.compartilhar()
        messagebox.showinfo("Compartilhar", "\n".join(linhas), parent=self.root)

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
