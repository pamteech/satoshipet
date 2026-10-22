"""vida.py - o bicho em si: comer, XP, carinho, vida, conquistas, mini-game, moedas/skins e status().

Mixin do Tamagoshi (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import random
import threading
import time
import webbrowser

from . import (
    arts,
    cenas,
    config,
    conquistas,
    evolucao,
    genetica,
    logic,
    lore,
    onchain,
    papel,
    ranking,
    share,
    sistema,
)
from .graficos import (
    SKINS_PRO,
)
from .sprites import FRAMES, SKINS_SECRETAS


class MixinVida:
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
            velho, self.estagio = self.estagio, novo
            self.iniciar_evolucao(velho, novo)
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
        self._tocar()
        if self.cfg.get("fantasma"):
            self.frase_atual = random.choice(["buuu... sua mão atravessou", "fantasma não sente carinho :(",
                                              "renasce eu? (menu > Genética)"])
            return self.frase_atual
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
        if self.cfg.get("fantasma"):  # fantasma não envelhece, não ganha XP, só assombra
            self.root.after(10000, self.tick_vida)
            return
        bonus = lore.ajuste_vida_fng(self.fng[0] if self.fng else None)
        crashes = self.conq.d["crashes"]
        self._comemorar(self.conq.tick(self.estado, 10, bonus))
        if self.conq.d["crashes"] > crashes:
            self._ganhar_xp("crash")
        self._ganhar_xp("minuto", 10)
        self._checar_conq_mercado()
        d = max(0.0, float(self.cfg.get("diversao", 100.0)) - 100 / (3 * 360))  # zera em ~3 h sem brincar
        self.cfg["diversao"] = d
        if d < 25 and random.random() < 0.15 and not self.toast:
            self.frase_atual = random.choice(["tô entediado... bora jogar? (P)", "quero brincar! aperta P",
                                              "pega uns sats comigo? (P)"])
        if self.checar_hardcore():
            self.cena = cenas.Cemiterio(self)
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
            self.badge = cid  # v1.7: medalha pixel no toast
            self.anunciar("conquista: " + conquistas.LISTA[cid][0])
            self.som.tocar("conquista")
            self._salvar_progresso()

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

    # ---------- mini-game ----------
    def brincar(self):
        if isinstance(self.cena, cenas.PegaSats):
            return ["já tá jogando!"]
        self.console_aberto = False
        self.cena = cenas.PegaSats(self)
        sistema.focar_teclado(self.root, self.cv)
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
        self._tocar()
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
                + ["loja:" + p for p in self.catalogo] if self._skin_permitida(sk)]

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
            return [f"watch-only: {self.cfg['carteira'][:12]}...",
                    f"saldo: {s['total']:,} sats ({s['txs']} txs)".replace(",", ".")
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

    def ranking(self, args):
        """Roda em thread (rede); a resposta cai no console quando chegar."""
        def tarefa():
            linhas = ranking.comando(self.cfg, self.status(), list(args), config.salvar)
            with self.lock:
                self.eventos.append(("console", linhas))
        threading.Thread(target=tarefa, daemon=True).start()
        return ["consultando ranking..."]

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
        return f"skin: {sk}"

    # ---------- Free vs Pro ----------
    def _skin_permitida(self, sk):
        if sk.startswith("loja:"):
            return self.pack_liberado(sk[5:])
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
            # saldo NUNCA entra aqui (status vai pra API local, card, ranking, overlay e IA)
            "carteira": {"endereco": self.cfg.get("carteira") or None},
            "genes": {k: v for k, v in self.genes().items() if k in genetica.GENES},
            "raridade": genetica.raridade(self.genes())[0],
            "hardcore": bool(self.cfg.get("hardcore")), "fantasma": bool(self.cfg.get("fantasma")),
            "batalhas": dict(self.cfg.get("batalhas") or {}),
            "papel": ({k: round(v, 2) for k, v in papel.resumo(self.cfg["papel"], self.precos).items()
                       if k in ("total", "pnl", "pnl_pct")} | {"aviso": papel.AVISO})
            if (self.cfg.get("papel") or {}).get("hist") else None,
            "frase": self.frase_atual,
            "patrocinado": bool((self.pack_ativo() or {}).get("tipo") == "patrocinado"),
            "stream": {"ultimo": self.stream.get("ultimo"), "t": self.stream.get("t"),
                       "chat": list(self.stream.get("chat", []))},
        }
