"""rede.py - threads de rede (preço, lore, on-chain, update, licença) e a fila thread -> GUI.

Mixin do Tamagoshi (main.py). Roda na thread da GUI, exceto os loop_* (threads daemon)."""
import time
import webbrowser
from tkinter import messagebox

from . import (
    __version__,
    config,
    crashlog,
    licencas,
    license,
    logic,
    lore,
    onchain,
    ranking,
    updates,
)
from .sprites import FRAMES


class MixinRede:
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
            if self._evento_mercado(ev):
                continue
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
                    self.toast = ["RECEBEU +{} sats".format(f"{delta:,}".replace(",", ".")), 22]
                elif delta < 0:
                    self.frase_atual = f"{delta:,} sats saíram... era pra HODL".replace(",", ".")
                    self.som.tocar("rekt")

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
