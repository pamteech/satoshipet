"""mercado.py - v1.4 fase 2: paper trading (fictício!), ETH/SOL watch-only, alerta de baleia e manchetes RSS.

Mixin do SatoshiPet. A rede roda em thread própria (loop_mercado) e só empurra eventos pra fila;
a GUI processa em _evento_mercado. Tudo sem chave de API, tudo só leitura.
"""
import random
import time
import webbrowser

from . import baleias, cenas, config, i18n, multichain, noticias, papel, saldo

BALEIA_INTERVALO = 5 * 60   # no máximo 1 susto a cada 5 min (o bicho tem coração fraco)


class MixinMercado:
    def _init_mercado(self):
        self.manchetes = []
        self.link_balao = None
        self.saldos_multi = {}      # {"eth": 1.23, "sol": 4.5}  (só memória, nunca disco)
        self.fiat_precos = {}       # {"BTC": {"brl": .., "usd": ..}}
        self._fiat_backoff = saldo.Backoff()
        self.radar = baleias.Radar(self.cfg.get("baleia_btc", 50))
        self.ultima_baleia = 0.0

    # ---------- thread de rede ----------
    def loop_mercado(self):
        n = 0
        while True:
            if self.cfg.get("baleias", True):
                try:
                    novas = self.radar.filtrar(baleias.recentes())
                    if novas and not self.radar.primeira:
                        with self.lock:
                            self.eventos.append(("baleia", novas[0]))
                    self.radar.primeira = False
                except Exception:
                    pass
            if self.cfg.get("noticias", True) and n % 60 == 0:  # a cada ~30 min
                try:
                    lista = noticias.buscar()
                    if lista:
                        with self.lock:
                            self.eventos.append(("noticias", lista))
                except Exception:
                    pass
            if n % 4 == 0:  # ~2 min
                for rede, fn in (("eth", multichain.saldo_eth), ("sol", multichain.saldo_sol)):
                    end = self.cfg.get("carteira_" + rede)
                    if end:
                        try:
                            v = fn(end)
                            with self.lock:
                                self.eventos.append(("saldo_multi", rede, v))
                        except Exception:
                            pass
            self._atualizar_fiat()
            n += 1
            self.dormir_rede(30)

    def _atualizar_fiat(self):
        """Cotação em R$/US$ das moedas com carteira, a cada ~3 min (erro = espera o dobro)."""
        sims = list(self.saldos_vivos())
        if not sims or not self._fiat_backoff.hora():
            return
        try:
            p = saldo.buscar_fiat(sims)
            with self.lock:
                self.fiat_precos = p
            self._fiat_backoff.ok()
        except Exception:
            self._fiat_backoff.erro()

    def saldos_vivos(self):
        """{"BTC": 0.0123, "ETH": 1.5} - só memória. NUNCA entra no status()/API/card/ranking."""
        out = {}
        if self.cfg.get("carteira") and getattr(self, "saldo", None):
            out["BTC"] = self.saldo["total"] / 1e8
        for rede in ("eth", "sol"):
            if self.cfg.get("carteira_" + rede) and self.saldos_multi.get(rede) is not None:
                out[rede.upper()] = self.saldos_multi[rede]
        return out

    def linhas_saldo(self):
        fiat = saldo.fiat_efetiva(self.cfg.get("saldo_fiat"), i18n.atual())
        return saldo.linhas(self.saldos_vivos(), self.fiat_precos, fiat, bool(self.cfg.get("saldo_oculto")))

    def _comemorar_marco(self, sim, antes, agora):
        m = saldo.marco_novo(sim, antes, agora)
        if m is None:
            return
        self.reacao = max(getattr(self, "reacao", 0), 12)
        txt = "carteira cresceu!" if self.cfg.get("saldo_oculto") else f"{m:g} {sim} na carteira!"
        self.toast = [txt, 22, "MARCO!"]

    def comando_saldo(self, args):
        """console: saldo [on|off|brl|usd|auto]"""
        a = (args[0].lower() if args else "")
        if a in ("off", "hide", "esconder"):
            self.cfg["saldo_oculto"] = True
        elif a in ("on", "show", "mostrar"):
            self.cfg["saldo_oculto"] = False
        elif a in saldo.FIATS:
            self.cfg["saldo_fiat"] = a
        elif a:
            return ["uso: saldo [on|off|brl|usd|auto]"]
        config.salvar(self.cfg)
        ls = [t for t, _ in self.linhas_saldo()] or ["nenhuma carteira watch-only (wallet <endereço público>)"]
        return ls + [("valores ESCONDIDOS (saldo on mostra)" if self.cfg.get("saldo_oculto") else "saldo off esconde")
                     + " · só memória, nunca sai daqui"]

    # ---------- eventos (thread da GUI) ----------
    def _evento_mercado(self, ev):
        if ev[0] == "baleia":
            self.baleia(ev[1])
        elif ev[0] == "twitch":
            self.evento_twitch(ev[1], ev[2])
        elif ev[0] == "noticias":
            self.manchetes = ev[1]
        elif ev[0] == "saldo_multi":
            _, rede, v = ev
            antes = self.saldos_multi.get(rede)
            self.saldos_multi[rede] = v
            self._comemorar_marco(rede.upper(), antes, v)
            if antes is not None and abs(v - antes) > 1e-9:
                sim = rede.upper()
                if v > antes:
                    self.reacao = 18
                    self.som.tocar("moon")
                    self.toast = [f"+{v - antes:.4f} {sim} chegou!", 22, "CARTEIRA " + sim]
                else:
                    self.som.tocar("rekt")
                    self.frase_atual = f"{v - antes:.4f} {sim} saiu... era pra HODL"
        else:
            return False
        return True

    def baleia(self, b, agora=None):
        agora = agora or time.time()
        if agora - self.ultima_baleia < BALEIA_INTERVALO:
            return False
        self.ultima_baleia = agora
        self.panico_t = 12
        self._comemorar(self.conq_mercado.baleia())
        self.som.tocar("panico")
        self.juice.tremor = 6
        self.toast = [baleias.frase(b), 30, "ALERTA DE BALEIA"]
        self.link_balao = b["url"]
        self.link_do_toast = True
        self.frase_atual = random.choice(["AAA UMA BALEIA!", "socorro, a baleia vai despejar!", "whale alert!!!"])
        return True

    def frase_noticia(self):
        """Às vezes (20%) o balão vira manchete. Retorna True se trocou."""
        if not (self.cfg.get("noticias", True) and self.manchetes) or random.random() > 0.2:
            self.link_balao = None if not self.toast else self.link_balao
            return False
        m = random.choice(self.manchetes)
        mc = (self.LARG - 30) // 8
        tit = m["titulo"]
        maximo = mc * 2 - 6
        if len(tit) > maximo:
            tit = tit[:maximo - 3].rsplit(" ", 1)[0] + "..."
        self.frase_atual = "NEWS: " + tit
        self.link_balao = m["link"]
        self.link_do_toast = False
        return True

    def clique_balao(self):
        if self.link_balao:
            webbrowser.open(self.link_balao)
            return True
        return False

    # ---------- carteiras ETH / SOL ----------
    def carteira_multi(self, rede, endereco):
        rede = rede.lower()
        if endereco is None:
            end = self.cfg.get("carteira_" + rede)
            if not end:
                return [f"nenhuma carteira {rede.upper()}. uso: wallet {rede} <endereço PÚBLICO>"]
            v = self.saldos_multi.get(rede)
            return [f"watch-only {rede.upper()}: {end[:10]}...",
                    f"saldo: {v:.6f} {rede.upper()}" if v is not None else "saldo: consultando..."]
        if endereco.strip().lower() in ("off", "remover", "-"):
            self.cfg["carteira_" + rede] = ""
            self.saldos_multi.pop(rede, None)
            config.salvar(self.cfg)
            return [f"carteira {rede.upper()} removida"]
        ok, msg = multichain.validar(rede, endereco)
        if not ok:
            return [msg]
        self.cfg["carteira_" + rede] = endereco.strip()
        self.saldos_multi.pop(rede, None)
        config.salvar(self.cfg)
        self._comemorar(self.conq.especial("not_your_keys"))
        return [f"carteira {rede.upper()} watch-only salva. só leitura, via RPC público sem chave."]

    def config_carteiras_multi(self):
        self.abrir_ajustes("grana")
        self.cena.sel = next(i for i, it in enumerate(self.cena.itens()) if it.rotulo == "Carteira ETH")

    # ---------- paper trading ----------
    def corretora(self):
        c = self.cfg.setdefault("papel", {})
        if not c:
            c.update(papel.nova())
        return c

    def paper(self, args):
        c = self.corretora()
        a = [x.lower() for x in args]
        if not a or a[0] in ("status", "pnl"):
            return self._paper_status()
        if a[0] == "reset":
            self.cfg["papel"] = papel.nova()
            config.salvar(self.cfg)
            return ["carteira fictícia zerada: $10.000 de mentirinha de novo"]
        if a[0] in ("hist", "history"):
            h = c.get("hist", [])[-8:]
            return [f"{time.strftime('%d/%m %H:%M', time.localtime(x['t']))} {x['lado']:<6} {x['moeda']} "
                    f"${x['usd']:,.2f}" + (f" ({x['lucro']:+.2f})" if "lucro" in x else "") for x in h] \
                or ["sem trades ainda"]
        if a[0] in ("buy", "sell") and len(a) >= 3:
            m = a[1].upper()
            if m not in config.MOEDAS:
                return [f"{m}? só BTC ETH SOL DOGE PEPE"]
            preco = self.precos.get(m)
            if not preco and m not in self.precos:
                return [f"sem preço de {m} (free só busca BTC; Pro busca as 5)"]
            try:
                valor = "all" if a[2] == "all" else float(a[2].replace(",", ".").lstrip("$"))
            except ValueError:
                return ["valor inválido. ex.: paper buy BTC 100  |  paper sell BTC all"]
            fn = papel.comprar if a[0] == "buy" else papel.vender
            ok, msg = fn(c, m, valor, preco)
            if ok:
                self._reagir_papel()
                config.salvar(self.cfg)
            return [msg]
        return ["uso: paper [status|buy <moeda> <usd|all>|sell <moeda> <qtd|all>|hist|reset]",
                "(DINHEIRO FICTÍCIO - preço real, prejuízo de mentira)"]

    def _paper_status(self):
        r = papel.resumo(self.corretora(), self.precos)
        linhas = [f"== {papel.AVISO} ==", f"caixa  ${r['usd']:,.2f}", f"total  ${r['total']:,.2f}",
                  f"PnL    {r['pnl']:+,.2f} ({r['pnl_pct']:+.2f}%)"]
        for m, p in r["pos"].items():
            linhas.append(f"{m:<5} {p['qtd']:.6g} = ${p['valor']:,.2f} ({p['pnl_pct']:+.1f}%)")
        return linhas

    def _reagir_papel(self):
        r = papel.resumo(self.corretora(), self.precos)
        h = papel.humor(r["pnl_pct"])
        if h == "moon":
            self.reacao = 18
            self.frase_atual = f"PnL fictício {r['pnl_pct']:+.1f}%! sou um gênio (de mentira)"
            if self.cfg.get("juice", True):
                self.juice.emitir("moon", self.LARG // 2, self.Y_SPRITE + self.S // 2, self.escala)
        elif h == "rekt":
            self.panico_t = 6
            self.frase_atual = f"PnL fictício {r['pnl_pct']:+.1f}%... ainda bem que é de mentira"
        else:
            self.frase_atual = random.choice(["ordem executada (no mundo da fantasia)", "trade fictício feito!",
                                              "comprei no papel, HODL no papel"])

    def frase_papel(self):
        c = self.cfg.get("papel") or {}
        if not c.get("hist") or random.random() > 0.12:
            return False
        r = papel.resumo(c, self.precos)
        h = papel.humor(r["pnl_pct"])
        if h:
            self.frase_atual = (f"meu PnL fictício: {r['pnl_pct']:+.1f}% " +
                                ("TO THE MOON" if h == "moon" else "me segura que eu choro"))
            return True
        return False

    def abrir_corretora(self):
        self.console_aberto = False
        self.cena = cenas.Corretora(self)
        self._desenhar()
        return ["corretora de mentirinha aberta (dinheiro FICTÍCIO)"]
