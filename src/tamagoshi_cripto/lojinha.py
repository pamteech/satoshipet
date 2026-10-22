"""lojinha.py - v1.4 fase 4 no app: loja de skins (destrave por Pro/código) + overlay de streamer com chat da Twitch.

Mixin do Tamagoshi. Pagamento NÃO acontece aqui: o código SKIN-... vem do provedor de licença de sempre
(ou de um concurso). Pacotes de marca aparecem com o selo PATROCINADO, sempre.
"""
import time

from . import cenas, config, loja

COMANDOS_TWITCH = {"!pet", "!moon", "!rekt", "!price", "!dna", "!dance"}
COOLDOWN = 8  # s entre comandos do chat (o bicho não é escravo do chat)


class MixinLoja:
    def _init_loja(self, extra=None):
        self.catalogo = loja.catalogo(extra)
        self.stream = {"ultimo": None, "t": 0, "chat": []}
        self._ultimo_cmd_twitch = 0.0

    # ---------- loja ----------
    def pack_ativo(self):
        sk = self.cfg.get("skin", "")
        return self.catalogo.get(sk[5:]) if sk.startswith("loja:") else None

    def pack_visivel(self, meta):
        return loja.vigente(meta) and (loja.em_temporada(meta) or loja.destravado(
            meta, self.pro, self.cfg.get("loja_codigos", [])))

    def pack_liberado(self, pid):
        meta = self.catalogo.get(pid)
        return bool(meta) and loja.destravado(meta, self.pro, self.cfg.get("loja_codigos", []))

    def resgatar(self, codigo):
        pid = loja.validar_codigo(codigo, self.cfg.get("email", ""))
        if not pid or pid not in self.catalogo:
            return ["código inválido (ou de outro e-mail). confere e tenta de novo"]
        cods = self.cfg.setdefault("loja_codigos", [])
        if pid not in cods:
            cods.append(pid)
        config.salvar(self.cfg)
        self._preencher_skins()
        return [f"pacote '{self.catalogo[pid]['nome']}' destravado! menu > Trocar skin"]

    def usar_pack(self, pid):
        if not self.pack_liberado(pid):
            return [f"'{pid}' ainda tá trancado ({self.catalogo.get(pid, {}).get('tier', '?')})"]
        self.cfg["skin"] = "loja:" + pid
        self.cache_sprites.clear()
        config.salvar(self.cfg)
        return [f"skin: {self.catalogo[pid]['nome']}"]

    def loja_linhas(self):
        out = []
        for pid, m in self.catalogo.items():
            if not self.pack_visivel(m):
                continue
            st = "OK" if self.pack_liberado(pid) else m["tier"].upper()
            out.append(f"{pid:<13} {loja.ROTULO_TIPO[m['tipo']]:<11} {st:<6} {m['nome']}")
        return out + ["'redeem <SKIN-...>' destrava código, 'skin loja:<id>' usa"]

    def abrir_loja(self):
        self.console_aberto = False
        self.cena = cenas.Loja(self)
        self._desenhar()
        return ["loja de skins aberta"]

    def _menu_resgatar(self):
        self.abrir_ajustes("conta")
        self.cena.sel = next(i for i, it in enumerate(self.cena.itens()) if it.rotulo == "Código da loja")

    # ---------- overlay de streamer ----------
    def folha_png(self):
        """PNG da folha atual com DNA/fantasma aplicados (chamado pela thread da API: só PIL, nada de Tk)."""
        import io

        from PIL import Image

        from . import genetica
        chave = (str(self._caminho_folha()), self._chave_dna())
        cache = self.__dict__.setdefault("_cache_folha", {})
        if chave not in cache:
            folha = Image.open(self._caminho_folha()).convert("RGBA")
            d = self._dna()
            out = Image.new("RGBA", folha.size, (0, 0, 0, 0))
            for j in range(4):
                for f in range(4):
                    fr = folha.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48))
                    fr = genetica.fantasma(fr) if d["fantasma"] else genetica.aplicar(fr, d["genes"])
                    out.paste(fr, (f * 48, j * 48))
            buf = io.BytesIO()
            out.save(buf, "PNG")
            cache.clear()
            cache[chave] = buf.getvalue()
        return cache[chave]

    def iniciar_twitch(self):
        from . import twitch
        canal = (self.cfg.get("twitch_canal") or "").strip()
        if not canal or self.op.get("sem_twitch"):
            return None
        if not twitch.canal_valido(canal):
            print("[twitch] canal inválido, ignorando:", canal)
            return None

        def ao_comando(usuario, cmd):  # thread do IRC: só enfileira
            with self.lock:
                self.eventos.append(("twitch", usuario, cmd))
        self.twitch = twitch.Leitor(canal, COMANDOS_TWITCH, ao_comando).iniciar()
        return self.twitch

    def config_twitch(self):
        self.abrir_ajustes("conta")
        self.cena.sel = next(i for i, it in enumerate(self.cena.itens()) if it.rotulo == "Canal Twitch")

    def aplicar_twitch(self, canal):
        """Liga/desliga o leitor anônimo do chat. Vazio = desligar. Devolve linhas de resposta."""
        from . import twitch
        c = (canal or "").strip().lower().lstrip("#")
        if c and not twitch.canal_valido(c):
            return ["canal inválido (a-z, 0-9, _)"]
        self.cfg["twitch_canal"] = c
        config.salvar(self.cfg)
        if getattr(self, "twitch", None):
            self.twitch.parar = True
            self.twitch = None
        if not c:
            return ["chat da Twitch desligado"]
        self.iniciar_twitch()
        porta = getattr(self.api, "server_address", (0, 8737))[1]
        return [f"OBS > Browser Source > http://127.0.0.1:{porta}/stream", "(600x400) docs/STREAMER_OVERLAY.md"]

    # ---------- Twitch (thread -> fila -> GUI) ----------
    def evento_twitch(self, usuario, cmd, agora=None):
        agora = agora or time.time()
        self.stream["chat"] = (self.stream["chat"] + [f"{usuario}: {cmd}"])[-5:]
        if agora - self._ultimo_cmd_twitch < COOLDOWN:
            return False
        self._ultimo_cmd_twitch = agora
        self.stream.update(ultimo=f"{usuario}: {cmd}", t=int(agora))
        if cmd == "!pet":
            self.carinho()
            self.frase_atual = f"valeu pelo carinho, {usuario}!"
        elif cmd in ("!moon", "!dance"):
            self.estado_forcado = ("moon", agora + 10)
            self.reacao = 12
            self.frase_atual = f"{usuario} mandou TO THE MOON!"
        elif cmd == "!rekt":
            self.estado_forcado = ("rekt", agora + 6)
            self.frase_atual = f"{usuario}, isso foi cruel"
        elif cmd == "!price":
            st = self.status()
            self.frase_atual = f"{st['moeda']} {st['preco_fmt']} ({st['variacao_pct']:+.2f}%)"
        elif cmd == "!dna":
            st = self.status()
            self.frase_atual = f"DNA {st['raridade']}: " + " ".join(str(v) for v in st["genes"].values())
        return True
