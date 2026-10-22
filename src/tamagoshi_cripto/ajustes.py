"""ajustes.py - A tela de ajustes: UMA cena com abas no lugar daquele desfile de diálogos do Tk.

Abas: GERAL | VISUAL | GRANA | CONTA | SOBRE. Teclado em tudo:
  TAB / Shift+TAB  -> próximo / anterior item     setas ↑ ↓ -> linha     ← → -> muda valor (ou aba)
  ENTER / espaço   -> alterna / edita / aperta     1-5 -> pula pra aba    ESC -> sai (ou cancela edição)
Campos de texto editam inline (ENTER salva, ESC cancela). Chave de licença aparece mascarada.
Toda mudança chama a MESMA função que o menu/console usam: nada de regra duplicada aqui.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import __version__, config, i18n, ui
from .cenas import _Cena


@dataclass
class Item:
    rotulo: str
    valor: Callable[[], str]            # texto mostrado à direita
    tipo: str = "acao"                   # bool | escolha | numero | texto | acao
    mudar: Callable[..., Any] | None = None   # bool/acao: f(); escolha/numero: f(delta); texto: f(str)
    inicial: Callable[[], str] | None = None  # texto: valor que aparece ao começar a editar
    ativo: Callable[[], bool] = lambda: True
    segredo: bool = False


def _sim(v: Any) -> str:
    return i18n.t("ligado") if v else i18n.t("desligado")


class Ajustes(_Cena):
    NAV_PROPRIA = True
    ABAS = ("GERAL", "VISUAL", "GRANA", "CONTA", "SOBRE")
    ABA_POR_NOME = {"geral": 0, "visual": 1, "grana": 2, "conta": 3, "sobre": 4}

    def __init__(self, app: Any, aba: str | int = 0):
        super().__init__(app)
        self.acabou = False
        self.alvos: list = []
        self.aba = self.ABA_POR_NOME.get(aba, 0) if isinstance(aba, str) else int(aba)
        self.sel = 0              # linha selecionada (-1 = na barra de abas)
        self.editando: str | None = None
        self.msg = ""
        self.msg_t = 0

    # ---------------- conteúdo das abas ----------------
    def itens(self) -> list[Item]:
        a, cfg = self.app, self.app.cfg
        def b(par: tuple[str, str]) -> Item:
            rotulo, chave = par
            return Item(rotulo, lambda: _sim(cfg.get(chave)), "bool", lambda: a.alternar_opcao(chave))
        if self.aba == 0:
            return [
                Item("Idioma", lambda: i18n.NOMES[cfg.get("idioma", "auto")], "escolha", self._mudar_idioma),
                Item("Moeda", lambda: cfg["moeda"], "escolha", self._mudar_moeda),
                Item("Skin", lambda: cfg["skin"].replace("loja:", "")[:12], "escolha", self._mudar_skin),
                Item("Nome do bicho", lambda: (cfg.get("nome_pet") or "-")[:12], "texto", self._mudar_nome,
                     inicial=lambda: cfg.get("nome_pet", "")),
                Item("Mostrar em sats ", lambda: _sim(cfg.get("unidade") == "sats"), "bool", lambda: a.alternar_sats()),
                Item("Som", lambda: _sim(not cfg.get("mudo")), "bool", self._mudar_som),
                b(("Música", "musica")),
                b(("Modo economia", "economia")),
                Item("Iniciar c/ sistema", lambda: _sim(a.autostart_ligado()), "bool", a.alternar_autostart,
                     ativo=a.autostart_suportado),
            ]
        if self.aba == 1:
            return [
                Item("Tamanho", lambda: f"{a.escala}x", "numero", lambda d: a.mudar_escala(a.escala + d)),
                b(("Alto contraste", "alto_contraste")), b(("Paleta dia/noite", "dia_noite")),
                b(("Chapéus de época", "chapeus")), b(("Tremidinha", "juice")), b(("Efeito CRT", "crt")),
            ]
        if self.aba == 2:
            m = cfg["moeda"]
            alvo = cfg["alertas"].get(m, {})
            return [
                Item("Limite MOON %", lambda: f"{cfg['limite_alta']:+.1f}", "numero",
                     lambda d: self._limites(alta=cfg["limite_alta"] + d * .5), ativo=lambda: a.pro),
                Item("Limite REKT %", lambda: f"{cfg['limite_queda']:+.1f}", "numero",
                     lambda d: self._limites(queda=cfg["limite_queda"] + d * .5), ativo=lambda: a.pro),
                Item("Alerta acima $", lambda: f"{alvo.get('acima', 0):g}" if alvo.get("acima") else "-", "texto",
                     lambda s: self._alerta("acima", s), inicial=lambda: f"{alvo.get('acima', '') or ''}", ativo=lambda: a.pro),
                Item("Alerta abaixo $", lambda: f"{alvo.get('abaixo', 0):g}" if alvo.get("abaixo") else "-", "texto",
                     lambda s: self._alerta("abaixo", s), inicial=lambda: f"{alvo.get('abaixo', '') or ''}", ativo=lambda: a.pro),
                b(("Baleias", "baleias")), b(("Manchetes RSS", "noticias")),
                Item("Hardcore", lambda: _sim(cfg.get("hardcore")), "bool", lambda: self._dizer(a.alternar_hardcore())),
                Item("Carteira BTC", lambda: (cfg.get("carteira") or i18n.t("nenhuma"))[:10], "texto", self._carteira,
                     inicial=lambda: cfg.get("carteira", "")),
                Item("Carteira ETH", lambda: (cfg.get("carteira_eth") or i18n.t("nenhuma"))[:10], "texto",
                     lambda s: self._dizer(a.carteira_multi("eth", s.strip() or "-")),
                     inicial=lambda: cfg.get("carteira_eth", "")),
                Item("Carteira SOL", lambda: (cfg.get("carteira_sol") or i18n.t("nenhuma"))[:10], "texto",
                     lambda s: self._dizer(a.carteira_multi("sol", s.strip() or "-")),
                     inicial=lambda: cfg.get("carteira_sol", "")),
                Item("Saldo em", lambda: {"auto": "auto", "brl": "R$", "usd": "US$"}[cfg.get("saldo_fiat", "auto")],
                     "escolha", self._mudar_fiat),
                Item("Esconder saldo", lambda: _sim(cfg.get("saldo_oculto")), "bool",
                     lambda: a.alternar_opcao("saldo_oculto")),
            ]
        if self.aba == 3:
            return [
                Item("Licença", lambda: "PRO" if a.pro else i18n.t("grátis"), "acao", None),
                Item("E-mail", lambda: (self.email or cfg.get("email") or "-")[:14], "texto", self._email,
                     inicial=lambda: self.email or cfg.get("email", ""), ativo=lambda: not a.pro),
                Item("Chave", lambda: "****" if (self.chave or cfg.get("licenca")) else "-", "texto", self._chave,
                     inicial=lambda: "", ativo=lambda: not a.pro, segredo=True),
                Item("ATIVAR PRO", lambda: ">", "acao", self._ativar, ativo=lambda: not a.pro),
                Item("Ranking", lambda: _sim(cfg.get("ranking")), "bool", self._ranking),
                Item("Servidor", lambda: (cfg.get("ranking_url") or "-")[-14:], "texto", self._ranking_url,
                     inicial=lambda: cfg.get("ranking_url") or "http://127.0.0.1:8740"),
                Item("Apelido", lambda: (cfg.get("nick") or "-")[:14], "texto", self._nick,
                     inicial=lambda: cfg.get("nick", "")),
                Item("Código da loja", lambda: str(len(cfg.get("loja_codigos", []))), "texto",
                     lambda s: self._dizer(a.resgatar(s.strip())) if s.strip() else None, inicial=lambda: ""),
                Item("Canal Twitch", lambda: (cfg.get("twitch_canal") or "-")[:14], "texto",
                     lambda s: self._dizer(a.aplicar_twitch(s)), inicial=lambda: cfg.get("twitch_canal", "")),
                Item("IA (BYO)", lambda: _sim(cfg.get("ai_url")), "acao", self._ia_off, ativo=lambda: bool(cfg.get("ai_url"))),
            ]
        return [
            Item("Versão", lambda: __version__, "acao", None),
            b(("Avisar versão nova", "checar_updates")),
            Item("API local", lambda: "127.0.0.1" if cfg.get("api", True) else i18n.t("desligado"), "bool",
                 lambda: a.alternar_opcao("api")),
            Item("Atualização", lambda: i18n.t("PROCURAR"), "acao", self._update),
            Item("Rever intro", lambda: i18n.t("ABRIR"), "acao", a.rever_intro),
            Item("Conquistas", lambda: str(len(a.conq.d.get("desbloqueadas", []))), "acao", a.ver_conquistas),
            Item("Relatório de erro", lambda: i18n.t("ENVIAR"), "acao", lambda: self._dizer(a.enviar_relatorio())),
            Item("Privacidade", lambda: i18n.t("VER"), "acao", self._privacidade),
        ]

    email = ""
    chave = ""

    # ---------------- ações (reaproveitam as do app) ----------------
    def _dizer(self, r: Any) -> None:
        if isinstance(r, (list, tuple)):
            r = r[0] if r else ""
        if r:
            self.msg, self.msg_t = str(r), 40

    def _privacidade(self) -> None:
        self._dizer("nada sai do seu PC sem você ligar")
        self.app.avisar(["ranking, IA, Twitch e updates são opt-in", "carteiras: só endereço público",
                         "detalhes: PRIVACY.md"], "PRIVACIDADE", 60)

    def _update(self) -> None:
        self.app.checar_update_agora()
        if self.app.toast:
            self._dizer(self.app.toast[0])

    def _mudar_idioma(self, d: int) -> None:
        ops = list(i18n.IDIOMAS)
        atual = self.app.cfg.get("idioma", "auto")
        self.app.definir_idioma(ops[(ops.index(atual) + d) % len(ops)] if atual in ops else "auto")

    def _mudar_moeda(self, d: int) -> None:
        ms = config.MOEDAS if isinstance(config.MOEDAS, list) else list(config.MOEDAS)
        i = ms.index(self.app.cfg["moeda"]) if self.app.cfg["moeda"] in ms else 0
        self._dizer(self.app.trocar_moeda(ms[(i + d) % len(ms)]))

    def _mudar_skin(self, d: int) -> None:
        sk = self.app.skins() or ["padrao"]
        i = sk.index(self.app.cfg["skin"]) if self.app.cfg["skin"] in sk else 0
        self._dizer(self.app.trocar_skin(sk[(i + d) % len(sk)]))

    def _mudar_nome(self, s: str) -> None:
        nome = "".join(ch for ch in s if ch.isprintable())[:12].strip()
        self.app.cfg["nome_pet"] = nome
        config.salvar(self.app.cfg)
        self._dizer("salvo!")

    def _mudar_som(self) -> None:
        a = self.app
        a.som.mudo = a.cfg["mudo"] = not a.cfg.get("mudo")
        config.salvar(a.cfg)

    def _limites(self, alta: float | None = None, queda: float | None = None) -> None:
        self.app.aplicar_limites(alta=alta, queda=queda)

    def _alerta(self, lado: str, s: str) -> None:
        try:
            v = float(s.replace(",", ".")) if s.strip() else 0.0
        except ValueError:
            return self._dizer("valor inválido")
        alvo = dict(self.app.cfg["alertas"].get(self.app.cfg["moeda"], {}))
        alvo[lado] = v
        self.app.aplicar_alertas(alvo.get("acima"), alvo.get("abaixo"))
        self._dizer("salvo!")

    def _mudar_fiat(self, d: int) -> None:
        ops = ["auto", "brl", "usd"]
        atual = self.app.cfg.get("saldo_fiat", "auto")
        self.app.cfg["saldo_fiat"] = ops[(ops.index(atual) + d) % 3] if atual in ops else "auto"
        config.salvar(self.app.cfg)

    def _carteira(self, s: str) -> None:
        self._dizer(self.app.aplicar_carteira(s))

    def _email(self, s: str) -> None:
        self.email = s.strip()

    def _chave(self, s: str) -> None:
        self.chave = s.strip()

    def _ativar(self) -> None:
        email = self.email or self.app.cfg.get("email", "")
        self._dizer(self.app.aplicar_licenca(email, self.chave).msg)

    def _ranking(self) -> None:
        a = self.app
        if a.cfg.get("ranking"):
            self._dizer(a.ranking(["off"]))
        elif a.cfg.get("nick") and a.cfg.get("ranking_url"):
            self._dizer(a.ligar_ranking(a.cfg["ranking_url"], a.cfg["nick"]))
        else:
            self._dizer("Servidor + Apelido")

    def _ranking_url(self, s: str) -> None:
        if s.strip() and not s.strip().startswith(("https://", "http://127.0.0.1", "http://localhost")):
            return self._dizer("valor inválido")
        self.app.cfg["ranking_url"] = s.strip()
        config.salvar(self.app.cfg)

    def _nick(self, s: str) -> None:
        a = self.app
        if a.cfg.get("ranking") and a.cfg.get("ranking_url"):
            self._dizer(a.ligar_ranking(a.cfg["ranking_url"], s.strip()))
        else:
            a.cfg["nick"] = s.strip()[:16]
            config.salvar(a.cfg)

    def _ia_off(self) -> None:
        self._dizer(self.app.console.executar("ai off"))

    # ---------------- navegação ----------------
    def _trocar_aba(self, i: int) -> None:
        self.aba, self.sel, self.editando = i % len(self.ABAS), 0, None

    def _ativar_item(self, it: Item, delta: int = 1) -> None:
        if not it.ativo():
            return self._dizer("precisa do Pro") if self.aba == 2 else None
        if it.tipo == "texto":
            self.editando = it.inicial() if it.inicial else ""
            return None
        if it.mudar is None:
            return None
        if it.tipo in ("escolha", "numero"):
            it.mudar(delta)
        else:
            it.mudar()
        return None

    def tecla(self, e: Any) -> None:
        k, ch = e.keysym, getattr(e, "char", "") or ""
        its = self.itens()
        if self.editando is not None:
            if k == "Escape":
                self.editando = None
            elif k in ("Return", "KP_Enter"):
                txt, self.editando = self.editando, None
                f = its[self.sel].mudar if 0 <= self.sel < len(its) else None
                if f:
                    f(txt)
            elif k == "BackSpace":
                self.editando = self.editando[:-1]
            elif ch and ch.isprintable() and len(self.editando) < 80:
                self.editando += ch
            return
        if k in ("Escape", "q"):
            self.acabou = True
        elif k in ("Tab", "ISO_Left_Tab"):
            volta = k == "ISO_Left_Tab" or bool(getattr(e, "state", 0) & 1)
            self.sel = (self.sel + (-1 if volta else 1) + 1) % (len(its) + 1) - 1   # -1 = barra de abas
        elif k in ("Down", "j"):
            self.sel = min(len(its) - 1, self.sel + 1)
        elif k in ("Up", "k"):
            self.sel = max(-1, self.sel - 1)
        elif k in ("Left", "h", "Right", "l"):
            d = -1 if k in ("Left", "h") else 1
            if self.sel < 0:
                self._trocar_aba(self.aba + d)
            elif its[self.sel].tipo in ("escolha", "numero"):
                self._ativar_item(its[self.sel], d)
            else:
                self._trocar_aba(self.aba + d)
        elif k in ("Return", "space", "KP_Enter"):
            if self.sel < 0:
                self._trocar_aba(self.aba + 1)
            elif self.sel < len(its):
                self._ativar_item(its[self.sel])
        elif ch in "12345" and ch:
            self._trocar_aba(int(ch) - 1)

    def acao(self, tag: str | None) -> None:
        if not tag:
            return
        if tag == "sair":
            self.acabou = True
        elif tag.startswith("aba:"):
            self._trocar_aba(int(tag[4:]))
        elif tag.startswith(("item:", "menos:", "mais:")):
            tipo, i = tag.split(":")
            its = self.itens()
            if int(i) < len(its):
                self.sel = int(i)
                self.editando = None
                self._ativar_item(its[int(i)], -1 if tipo == "menos" else 1)

    def tick(self) -> bool:
        self.t += 1
        if self.msg_t:
            self.msg_t -= 1
        return not self.acabou

    # ---------------- desenho ----------------
    def desenhar(self) -> None:
        a, L, H = self.app, self.app.LARG, self.app.ALT
        self.alvos = []
        ui.cabecalho(a, "AJUSTES")
        ui.abas(a, self.alvos, 28, [i18n.t(n) for n in self.ABAS], self.aba, foco=0 if self.sel < 0 else None)
        if self.sel < 0:  # foco na barra de abas: anel só na aba ativa
            pass
        its = self.itens()
        self.sel = min(self.sel, len(its) - 1)
        y0 = 28 + ui.ALT_ABA + 6
        visiveis = max(1, (H - y0 - 40) // ui.ALT_LINHA)
        topo = max(0, min(self.sel - visiveis + 1, len(its) - visiveis)) if self.sel >= visiveis else 0
        for n, it in enumerate(its[topo:topo + visiveis]):
            i = topo + n
            y = y0 + n * ui.ALT_LINHA
            ed = self.editando if i == self.sel else None
            editar = ed is not None
            if ed is not None:
                txt = ("*" * len(ed) if it.segredo else ed)[-14:]
                valor = txt + ("_" if self.t // 4 % 2 == 0 else " ")
            else:
                valor = i18n.t(it.valor())
            cor = ui.VERDE_LUZ if valor == i18n.t("ligado") else (ui.OURO if it.tipo == "acao" else ui.PAPEL)
            ui.linha_ajuste(a, y, i18n.t(it.rotulo), valor, foco=i == self.sel, ativo=it.ativo(), cor_valor=cor,
                            editando=editar)
            if it.tipo in ("escolha", "numero"):
                self.alvos.append((L // 2 - 10, y, L // 2 + 10, y + ui.ALT_LINHA - 2, f"menos:{i}"))
                self.alvos.append((L // 2 + 12, y, L - ui.PAD, y + ui.ALT_LINHA - 2, f"mais:{i}"))
                if i == self.sel:
                    a._txt(L // 2, y + 4, "<", ui.CINZA_CLARO, anchor="n")
            else:
                self.alvos.append((ui.PAD, y, L - ui.PAD, y + ui.ALT_LINHA - 2, f"item:{i}"))
        if self.msg_t and self.msg:
            a._txt(L // 2, H - 44, self.msg[:40], ui.VERDE_LUZ, max_chars=(L - 16) // 8)
        dica = "ENTER salva - ESC cancela" if self.editando is not None else "TAB/setas - ENTER muda - ESC sai"
        self.botao(L // 2 - 36, H - 34, L // 2 + 36, H - 14, "SAIR", fundo=ui.CINZA_CLARO, tag="sair")
        ui.rodape(a, i18n.t(dica))
