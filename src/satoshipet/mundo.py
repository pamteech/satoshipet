"""mundo.py - v1.7: clima, calendário cripto, conquistas de mercado, amigos na LAN e acessibilidade."""
from __future__ import annotations

import datetime as dt
import random
import threading
import time

import requests

from . import acessibilidade, calendario, clima, conquistas, i18n, lan, marcos
from .config import MOEDAS
from .graficos import C_TINTA, carregar_frames


class MixinMundo:
    def _init_mundo(self):
        self.clima_cache = clima.Cache()
        self.clima_dado = None
        self.conq_mercado = conquistas.Mercado()
        self.locutor = acessibilidade.Locutor()
        self._rm_sistema = False
        self.badge = None
        self.lan_id = lan.novo_id()
        self.vizinhos = lan.Vizinhos(self.lan_id)
        self.visita = None
        self._ultima_visita = 0.0
        self._lan_sock = None
        self.evento = None
        self._evento_avisado = None
        self._ultimo_calendario = 0.0
        self._ath_t = 0.0
        self._ath_pendente = None
        self._foco_dica = -1

    def _iniciar_mundo(self):
        threading.Thread(target=self.loop_mundo, daemon=True).start()
        threading.Thread(target=self.loop_lan, daemon=True).start()
        try:
            self._rm_sistema = acessibilidade.reduzir_movimento_sistema()
        except Exception:
            self._rm_sistema = False

    # ---------- acessibilidade ----------
    def movimento_reduzido(self):
        return bool(self.cfg.get("reduzir_movimento")) or bool(getattr(self, "_rm_sistema", False))

    def anunciar(self, texto):
        return self.locutor.falar(i18n.t(texto), bool(self.cfg.get("voz")))

    def abrir_menu_teclado(self):
        e = type("E", (), {"x_root": self.root.winfo_rootx() + 20, "y_root": self.root.winfo_rooty() + 40})()
        self.abrir_menu(e)

    def focar_proxima_dica(self, passo=1):
        """Tab/Shift+Tab: passeia pelas dicas sem mouse (e fala, se a voz estiver ligada)."""
        zs = list(self._zonas().items())
        self._foco_dica = (self._foco_dica + passo) % len(zs)
        chave, (x0, y0, x1, y1) = zs[self._foco_dica]
        self.mouse = ((x0 + x1) // 2, (y0 + y1) // 2)
        self.dica = [chave, 2]
        txt = self._texto_dica(chave)
        if txt:
            self.anunciar(txt)
        return chave

    def definir_cidade(self, txt):
        """'São Paulo' (geocoding Open-Meteo) ou '-23.55,-46.63'. Vazio = apaga."""
        t = (txt or "").strip()
        if not t:
            self.cfg.update(clima_cidade="", clima_lat=None, clima_lon=None)
            return ["cidade apagada"]
        ll = clima.parse_latlon(t)
        try:
            r = (t, *ll) if ll else clima.geocodificar(t)
        except Exception:
            return ["sem rede pra achar a cidade agora"]
        if not r:
            return ["cidade não encontrada"]
        self.cfg.update(clima_cidade=r[0][:40], clima_lat=r[1], clima_lon=r[2])
        if self.cfg.get("clima", "off") == "off":
            self.cfg["clima"] = "cidade"
        self.clima_cache.prox = 0
        from . import config
        config.salvar(self.cfg)
        return [f"clima de {r[0][:20]} ligado ({r[1]}, {r[2]})"]

    # ---------- threads de rede ----------
    def loop_mundo(self):
        while True:
            try:
                self._atualizar_clima()
            except Exception:
                pass
            try:
                self._atualizar_ath()
            except Exception:
                pass
            self.dormir_rede(30)

    def _local_clima(self):
        """(lat, lon) a usar, ou None. 'auto' resolve por IP UMA vez e guarda arredondado."""
        modo = self.cfg.get("clima", "off")
        if modo == "off":
            return None
        lat, lon = self.cfg.get("clima_lat"), self.cfg.get("clima_lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
        if modo == "auto":
            r = clima.por_ip()
            if r:
                self.cfg["clima_cidade"], self.cfg["clima_lat"], self.cfg["clima_lon"] = r
                return r[1], r[2]
        return None

    def _atualizar_clima(self):
        if self.cfg.get("clima", "off") == "off":
            self.clima_dado = None
            return
        if not self.clima_cache.hora():
            return
        loc = self._local_clima()
        if not loc:
            return
        try:
            d = clima.buscar(*loc)
            self.clima_cache.ok(d)
            self.clima_dado = d
        except Exception:
            self.clima_cache.erro()  # offline: segue com o último clima do cache

    def _atualizar_ath(self):
        if time.time() - self._ath_t < 6 * 3600:
            return
        moeda = self.cfg["moeda"]
        ids = sorted({MOEDAS[moeda], MOEDAS["BTC"]})
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets",
                         params={"vs_currency": "usd", "ids": ",".join(ids)}, timeout=10,
                         headers={"User-Agent": "SatoshiPet/1.8"})
        r.raise_for_status()
        por_id = {x.get("id"): x for x in r.json() or []}
        x = por_id.get(MOEDAS[moeda])
        if x and x.get("ath"):
            self.conq_mercado.ath[moeda] = float(x["ath"])
        b = por_id.get(MOEDAS["BTC"])
        if b and b.get("ath"):
            self._ath_pendente = (float(b["ath"]), float(b.get("current_price") or 0))  # GUI consome no tick
        self._ath_t = time.time()

    def loop_lan(self):
        ultimo_envio = 0.0
        while True:
            if not self.cfg.get("amigos_lan"):
                if self._lan_sock:
                    self._lan_sock.close()
                    self._lan_sock = None
                time.sleep(3)
                continue
            try:
                if not self._lan_sock:
                    self._lan_sock = lan.abrir_socket()
                if time.monotonic() - ultimo_envio > 60:
                    lan.anunciar(self._lan_sock, self._pacote_lan())
                    ultimo_envio = time.monotonic()
                try:
                    dados, _end = self._lan_sock.recvfrom(lan.MAX_BYTES + 1)  # o endereço é descartado
                except (TimeoutError, OSError):
                    continue
                p = self.vizinhos.receber(dados)
                if p:
                    with self.lock:
                        self.eventos.append(("amigo", p))
            except OSError:
                if self._lan_sock:
                    self._lan_sock.close()
                self._lan_sock = None
                time.sleep(30)

    def _pacote_lan(self):
        return lan.montar(self.lan_id, self.nome_pet(), self.cfg["moeda"], self.cfg["skin"], self.estado,
                          random.choice(lan.EMOTES))

    # ---------- GUI: por frame ----------
    def _tick_mundo(self):
        if self.visita:
            self.visita.tick()
            if not self.visita.viva:
                self.visita = None
        elif self.cfg.get("amigos_lan") and time.time() - self._ultima_visita > 600:
            amigos = self.vizinhos.lista()
            if amigos and random.random() < 0.02:
                self.iniciar_visita(random.choice(amigos))
        if time.time() - self._ultimo_calendario > 60:
            self._ultimo_calendario = time.time()
            self._checar_calendario()
            self._checar_marcos()
        if self._ath_pendente:
            ath, preco = self._ath_pendente
            self._ath_pendente = None
            self.checar_ath_btc(ath, preco)

    def iniciar_visita(self, amigo, lado=None):
        self._ultima_visita = time.time()
        self.visita = lan.Visita(amigo, self.LARG, lado if lado is not None else random.choice((-1, 1)),
                                 random.choice(lan.EMOTES))
        self.anunciar(f"{amigo['nome']} veio visitar")

    def _checar_calendario(self, hoje=None):
        altura = self.estomago.d.get("altura")
        self.evento = calendario.ativo(hoje, altura)
        if self.evento:
            chave = (self.evento["id"], (hoje or dt.date.today()).isoformat())
            if self._evento_avisado != chave:
                self._evento_avisado = chave
                self.toast = [random.choice(self.evento["frases"]), 26, self.evento["nome"]]
                self.cache_sprites.clear()  # chapéu do evento
                self.anunciar(self.evento["nome"])

    # ---------- v1.8: aniversários e ATH ----------
    def _checar_marcos(self, agora=None):
        m = marcos.pendente(self.cfg.get("nasceu_em") or 0, self.cfg.setdefault("marcos", []), agora)
        if not m:
            return None
        self.cfg["marcos"] = sorted(set(self.cfg["marcos"]) | set(m["alcancados"]))
        self.festa(m["fx"], m["titulo"], m["frase"], m["conquista"])
        from . import config
        config.salvar(self.cfg)
        return m

    def checar_ath_btc(self, ath_api, preco=None, agora=None):
        novo = marcos.checar_ath(self.cfg, ath_api, preco or self.precos.get("BTC"), agora)
        if novo:
            self.festa("fogos", "NOVO ATH!", marcos.texto_ath(novo), "ath_festa")
            from . import config
            config.salvar(self.cfg)
        return novo

    def frase_evento(self):
        h = calendario.halving(self.estomago.d.get("altura"))
        cont = calendario.contagem(h)
        if cont and random.random() < 0.5:
            self.frase_atual = cont
            return True
        if self.evento and random.random() < 0.4:
            self.frase_atual = random.choice(self.evento["frases"])
            return True
        return False

    def chapeu_evento(self):
        return (self.evento or {}).get("chapeu")

    def _checar_conq_mercado(self):
        moeda = self.cfg["moeda"]
        p = self.precos.get(moeda)
        novas = []
        if p:
            novas += [c for c in self.conq_mercado.preco(moeda, p) if c != "crash_10" or self.conq.vida > 0]
        novas += self.conq_mercado.fng(self.fng[0] if self.fng else None)
        novas += self.conq_mercado.hodl(float(self.cfg.get("nasceu_em") or 0))
        novas += self.conq_mercado.bloco(self.estomago.d.get("altura") or 0)
        for c in novas:
            self._comemorar(self.conq.especial(c))
        if p and moeda == "BTC" and "ath_vivo" in novas:  # v1.8: ATH ao vivo também vira festa
            self.checar_ath_btc(None, p)

    # ---------- desenho ----------
    def _clima_atual(self):
        return clima.efetivo(self.clima_dado, time.localtime().tm_hour)

    def _desenhar_clima_fundo(self):
        c, L = self.cv, self.LARG
        cl = self._clima_atual()
        topo, base = self.Y_BALAO + 6, self.Y_NOME - 6
        mov = 0 if self.movimento_reduzido() else self.frame
        if not cl["dia"] and cl["tipo"] in (None, "sol", "nublado"):
            rnd = random.Random(7)
            for i in range(14):
                x, y = rnd.randint(8, L - 8), rnd.randint(topo, base - 20)
                if (i + mov) % 5 == 0:
                    continue  # pisca
                t = 2 if i % 4 == 0 else 1
                c.create_rectangle(x, y, x + t * 2, y + t * 2, fill="#f4f4f4" if i % 3 else "#ffcd75", width=0)
            # lua minguante em pixels grandes
            mx, my, P = L - 36, topo + 6, 3
            for j, row in enumerate(["..111..", ".11....", "111....", "111....", "111....", ".11....", "..111.."]):
                for i, b in enumerate(row):
                    if b == "1":
                        c.create_rectangle(mx + i * P, my + j * P, mx + i * P + P, my + j * P + P, fill="#f4f4f4", width=0)
        elif cl["tipo"] == "sol" and cl["dia"]:
            sx, sy, P = 18, topo + 6, 3
            for j, row in enumerate(["..1.1..", ".11111.", "1111111", ".11111.", "1111111", ".11111.", "..1.1.."]):
                for i, b in enumerate(row):
                    if b == "1":
                        c.create_rectangle(sx + i * P, sy + j * P, sx + i * P + P, sy + j * P + P, fill="#ffcd75", width=0)

    def _desenhar_clima_frente(self):
        tipo = self._clima_atual()["tipo"]
        if tipo not in ("chuva", "tempestade", "neve", "neblina"):
            return
        c, L = self.cv, self.LARG
        topo, base = self.Y_BALAO + 4, self.Y_NOME - 4
        h = max(1, base - topo)
        mov = 0 if self.movimento_reduzido() else self.frame * (9 if tipo != "neve" else 3)
        rnd = random.Random(3)
        if tipo in ("chuva", "tempestade"):
            for _ in range(22):
                x, y0 = rnd.randint(4, L - 6), rnd.randint(0, h)
                y = topo + (y0 + mov) % h
                c.create_rectangle(x, y, x + 2, y + 6, fill="#41a6f6", width=0)
                c.create_rectangle(x, y, x + 2, y + 2, fill="#73eff7", width=0)
            if tipo == "tempestade" and not self.movimento_reduzido() and self.frame % 23 == 0:
                c.create_rectangle(0, topo, L, base, fill="#f4f4f4", width=0)
        elif tipo == "neve":
            for i in range(20):
                x0, y0 = rnd.randint(4, L - 6), rnd.randint(0, h)
                y = topo + (y0 + mov) % h
                x = x0 + (2 if ((y // 8) + i) % 2 else 0)
                c.create_rectangle(x, y, x + 3, y + 3, fill="#f4f4f4", width=0)
        else:  # neblina: faixas pontilhadas (sem alfa: funciona no Mac e no Windows)
            for k in range(4):
                y = topo + 20 + k * (h // 4)
                for x in range(0, L, 6):
                    if (x // 6 + k + (mov // 9)) % 3:
                        c.create_rectangle(x, y, x + 4, y + 2, fill="#94b0c2", width=0)

    def _desenhar_acessorios(self, cx, cy):
        """Guarda-chuva na chuva, óculos escuros no sol, pizza no Pizza Day. Desenhado no canvas."""
        if self.estagio == "ovo" or getattr(self, "fx_evo", None):
            return
        c, S, E = self.cv, self.S, self.escala
        tipo, dia = self._clima_atual()["tipo"], self._clima_atual()["dia"]
        if tipo in ("chuva", "tempestade"):
            ux, uy = cx + S // 3, cy - S // 2 - 2
            P = max(2, E)
            arte = ["....111....", "..1222221..", ".122222221.", "12222222221", "1.1.1.1.1.1", ".....3.....",
                    ".....3.....", ".....3.....", ".....3.....", "...3.3.....", "....3......"]
            cores = {"1": C_TINTA, "2": "#b13e53", "3": "#94b0c2"}
            for j, row in enumerate(arte):
                for i, b in enumerate(row):
                    if b in cores:
                        x = ux - len(row) * P // 2 + i * P
                        c.create_rectangle(x, uy + j * P, x + P, uy + j * P + P, fill=cores[b], width=0)
        elif tipo == "sol" and dia:
            olhos = self._olhos()
            if olhos:  # óculos escuros em cima dos olhos de verdade (detectados na folha)
                y, xe, xd = olhos
                x0, x1 = cx + (xe - 24) * E - 2 * E, cx + (xd - 24) * E + 3 * E
                oy = cy + (y - 24) * E - E
                meio = (x0 + x1) // 2
                for a, b in ((x0, meio - E), (meio + E, x1)):
                    c.create_rectangle(a, oy, b, oy + 3 * E, fill=C_TINTA, width=0)
                    c.create_rectangle(a + E, oy + E, a + 2 * E, oy + 2 * E, fill="#566c86", width=0)
                c.create_rectangle(meio - E, oy, meio + E, oy + E, fill=C_TINTA, width=0)
        if (self.evento or {}).get("item") == "pizza":
            px, py, P = cx - S // 2 - 4, cy + S // 6, max(2, E)
            for j, row in enumerate(["1111111", ".12321.", ".12221.", "..131..", "..121..", "...1..."]):
                for i, b in enumerate(row):
                    cor = {"1": "#ef7d57", "2": "#ffcd75", "3": "#b13e53"}.get(b)
                    if cor:
                        c.create_rectangle(px + i * P, py + j * P, px + i * P + P, py + j * P + P, fill=cor, width=0)

    def _olhos(self):
        """(y, x_esq, x_dir) dos olhos no frame 48x48 da folha atual: pixels escuros da cabeça. Cache por folha."""
        caminho = str(self._caminho_folha())
        cache = self.__dict__.setdefault("_cache_olhos", {})
        if caminho not in cache:
            cache[caminho] = None
            try:
                from PIL import Image

                from .juice import _topo_cabeca
                fr = Image.open(caminho).convert("RGBA").crop((0, 0, 48, 48))
                _cx, topo = _topo_cabeca(fr)
                px = fr.load()
                for y in range(topo + 2, min(48, topo + 20)):
                    def escuro(x, y=y):
                        return px[x, y][3] > 128 and sum(px[x, y][:3]) < 140

                    def claro(x, y=y):
                        return px[x, y][3] > 128 and not escuro(x)
                    # olho = pixel escuro DENTRO da cara (vizinhos claros dos dois lados), não o contorno
                    xs = [x for x in range(1, 47) if escuro(x) and claro(x - 1) and claro(x + 1)]
                    grupos = [x for i, x in enumerate(xs) if i == 0 or xs[i - 1] != x - 1]
                    if 2 <= len(grupos) <= 3 and xs[-1] - xs[0] >= 4:
                        cache[caminho] = (y, xs[0], xs[-1])
                        break
            except Exception:
                cache[caminho] = None
        return cache[caminho]

    def _desenhar_badge(self):
        if not self.toast or len(self.toast) > 2 or not self.badge:
            return
        cor, arte = conquistas.BADGES.get(self.badge, conquistas.BADGE_PADRAO)
        P = 3 * self.G
        x0, y0 = 14, (self.Y_BALAO - 8 * P) // 2 + 1
        for j, row in enumerate(arte):
            for i, b in enumerate(row):
                if b in "12":
                    c = cor if b == "1" else "#f4f4f4"
                    self.cv.create_rectangle(x0 + i * P, y0 + j * P, x0 + i * P + P, y0 + j * P + P, fill=c, width=0)

    def _sprite_amigo(self, amigo):
        from . import recursos
        from .sprites import nome_folha
        chave = ("amigo", amigo["moeda"], amigo["skin"])
        if chave not in self.cache_sprites:
            caminho = recursos.ASSETS / "sprites" / nome_folha(amigo["moeda"], amigo["skin"], "adulto")
            if not caminho.exists():
                caminho = recursos.ASSETS / "sprites" / nome_folha(amigo["moeda"], "padrao", "adulto")
            self.cache_sprites[chave] = carregar_frames(caminho, max(1, self.escala - 1))
        return self.cache_sprites[chave]

    def _desenhar_amigo(self):
        v = self.visita
        if not v:
            return
        frames = self._sprite_amigo(v.amigo)
        h = v.amigo["humor"]
        img = frames[(h, self.frame % 4)] if (h, 0) in frames else frames[("garimpando", 0)]
        S2 = img.height()
        cx = self.LARG // 2
        x = v.x(cx, self.S // 4 + S2 // 2 - 4)
        y = self.Y_SPRITE + self.S - S2 // 2
        self.cv.create_image(x, y, image=img)
        nome = v.amigo["nome"]
        nx = max(8 + len(nome) * 4, min(self.LARG - 8 - len(nome) * 4, x))
        self._txt(nx, y - S2 // 2 - 6, nome, "#a7f070", sombra=C_TINTA)
        em = v.emote()
        if em:
            quem, txt = em
            bx = max(40, min(self.LARG - 40, x)) if quem == "amigo" else cx - self.S // 4
            by = (y - S2 // 2 - 22) if quem == "amigo" else self.Y_SPRITE + 4
            w = len(txt) * 8 + 10
            self._moldura(bx - w // 2, by - 8, bx + w // 2, by + 8, "#f4f4f4", luz="#ffffff")
            self._txt(bx, by, txt, C_TINTA)
