"""v1.5 - testes de cobertura do núcleo: rede mockada, nada de internet de verdade (o CI agradece)."""
import socket
import ssl

import pytest

from satoshipet import config, console, evolucao, hardcore, logic, multichain, noticias, sprites, twitch


class Resp:
    def __init__(self, j=None, status=200, content=b""):
        self._j, self.status_code, self.content = j, status, content

    def json(self):
        return self._j

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")


# ---------------- logic ----------------
def test_logic_precos_e_ratelimit(monkeypatch):
    monkeypatch.setattr(logic.requests, "get", lambda *a, **k: Resp({"bitcoin": {"usd": 65000}, "x": {}}))
    assert logic.buscar_precos(["BTC", "LOL"]) == {"BTC": 65000.0}
    monkeypatch.setattr(logic.requests, "get", lambda *a, **k: Resp({}, 429))
    with pytest.raises(logic.RateLimit):
        logic.buscar_precos(["BTC"])


def test_logic_humor_alerta_historico():
    assert logic.estado_do_bicho(3) == "moon" and logic.estado_do_bicho(-3) == "rekt"
    assert logic.estado_do_bicho(0) == "garimpando"
    assert logic.variacao_pct(110, 100) == pytest.approx(10) and logic.variacao_pct(1, 0) == 0
    assert logic.formatar_preco(0.5) == "$0.5000" and logic.formatar_preco(0.00001234).startswith("$0.0000123")
    assert logic.checar_alerta(10, {}) is None
    assert "passou" in logic.checar_alerta(10, {"acima": 5})
    assert "abaixo" in logic.checar_alerta(1, {"abaixo": 5})
    assert logic.checar_alerta(7, {"acima": 9, "abaixo": 5}) is None
    h = logic.Historico(maximo=100)
    for i in range(100):
        h.adicionar("BTC", float(i), t=i + 1)
    s = h.serie("BTC", 10)
    assert len(s) == 10 and s[0] < s[-1]
    assert h.serie("ETH") == []


# ---------------- multichain ----------------
def test_multichain_rpc_fallback_e_saldos(monkeypatch):
    chamadas = []

    def post(url, json, **k):
        chamadas.append(url)
        if len(chamadas) == 1:
            raise OSError("rpc 1 caiu")
        return Resp({"result": "0xde0b6b3a7640000"} if json["method"] == "eth_getBalance" else {"result": {"value": 2_000_000_000}})

    monkeypatch.setattr(multichain.requests, "post", post)
    assert multichain.saldo_eth("0x" + "a" * 40) == pytest.approx(1.0)
    assert multichain.saldo_sol("So11111111111111111111111111111111111111112") == pytest.approx(2.0)
    with pytest.raises(ValueError):
        multichain.saldo_eth("nope")
    with pytest.raises(ValueError):
        multichain.saldo_sol("0x123")
    monkeypatch.setattr(multichain.requests, "post", lambda *a, **k: Resp({"error": "nananinanão"}))
    with pytest.raises(RuntimeError):
        multichain._rpc(["u1", "u2"], "x", [])
    assert multichain.validar("eth", "vitalik.eth")[0] is False
    assert multichain.validar("doge", "x") == (False, "rede desconhecida")


# ---------------- notícias ----------------
def test_noticias_buscar_sobrevive_feed_quebrado(monkeypatch):
    rss = b"<rss><channel><item><title>BTC sobe</title><link>https://a.b/1</link></item></channel></rss>"
    respostas = iter([Resp(content=rss), Resp(status=500)] * 5)
    monkeypatch.setattr(noticias.requests, "get", lambda *a, **k: next(respostas))
    itens = noticias.buscar()
    assert itens and itens[0]["titulo"] == "BTC sobe"


# ---------------- hardcore / evolução / config ----------------
def test_hardcore_risco_textos():
    assert hardcore.risco({"hardcore": False}, 0) is None
    assert hardcore.risco({"hardcore": True}, 5) is None
    assert "vida baixa" in hardcore.risco({"hardcore": True}, 1)
    assert "morre em" in hardcore.risco({"hardcore": True, "zero_desde": 1000}, 0, agora=1060)


def test_evolucao_proximo_estagio():
    nome, minimo = evolucao.proximo_estagio(0)
    assert nome and minimo > 0
    assert evolucao.proximo_estagio(10**9) == (None, None)


def test_config_migra_v1_e_salva_com_erro(tmp_path, monkeypatch, capsys):
    cfg = config.migrar({"skin": "default", "licenca": "x", "escala": "lixo"})
    assert cfg["skin"] == "padrao" and cfg["escala"] == 3 and cfg["licenca_provedor"] == "hmac"
    assert cfg["onboarding_ok"] and cfg["genes"] and cfg["versao_config"] == config.VERSAO_CONFIG
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "nao" / "existe" / "c.json")
    config.salvar({"a": 1})
    assert "Não deu pra salvar" in capsys.readouterr().out
    p = tmp_path / "c.json"
    p.write_text("{quebrado", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", p)
    assert config.carregar()["versao_config"] == config.VERSAO_CONFIG


# ---------------- twitch (socket fake, zero rede) ----------------
class SockFake:
    def __init__(self, blocos):
        self.blocos, self.enviado = list(blocos), b""

    def sendall(self, b):
        self.enviado += b

    def recv(self, n):
        return self.blocos.pop(0) if self.blocos else b""

    def close(self):
        pass


def test_twitch_sessao_ping_e_comandos(monkeypatch):
    sock = SockFake([b"PING :tmi.twitch.tv\r\n:ana!a@a PRIVMSG #canal :!pet oi\r\n:bob!b@b PRIVMSG #canal :ol",
                     b"a\r\n:zed!z@z PRIVMSG #canal :!moon\r\n"])
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: object())

    class Ctx:
        def wrap_socket(self, bruto, server_hostname):
            assert server_hostname == twitch.HOST
            return sock

    monkeypatch.setattr(ssl, "create_default_context", lambda: Ctx())
    vistos = []
    leitor = twitch.Leitor("#Canal", {"!pet", "!moon"}, lambda u, c: vistos.append((u, c)))
    with pytest.raises(ConnectionError):
        leitor._sessao()
    assert vistos == [("ana", "!pet"), ("zed", "!moon")]
    assert b"PONG :tmi.twitch.tv" in sock.enviado and b"NICK justinfan" in sock.enviado
    assert b"PRIVMSG" not in sock.enviado  # só leitura, nunca fala no chat


def test_twitch_loop_reconecta_e_para(monkeypatch):
    leitor = twitch.Leitor("canal_ok", {"!pet"}, lambda *a: None)
    n = {"x": 0}

    def sessao():
        n["x"] += 1
        if n["x"] >= 2:
            leitor.parar = True
        raise OSError("caiu")

    monkeypatch.setattr(leitor, "_sessao", sessao)
    monkeypatch.setattr(twitch.time, "sleep", lambda s: None)
    leitor._loop()
    assert n["x"] == 2 and not leitor.conectado
    with pytest.raises(ValueError):
        twitch.Leitor("x", set(), print).iniciar()


# ---------------- console com contexto fake ----------------
class CtxFake:
    def __init__(self):
        self.cfg = {"hardcore": False, "ai_url": "", "ai_key": "", "baleia_btc": 50}
        self.salvou = 0
        self.manchetes = [{"fonte": "X", "titulo": "manchete"}]

    def status(self):
        return {"moeda": "BTC", "preco_fmt": "$1", "variacao_pct": 1.0, "humor": "moon", "nome": "Bit Coin",
                "estagio": "bebe", "nivel": 2, "xp": 10, "xp_pct": .5, "vida": 8.0, "crashes": 0, "conquistas": 1,
                "uptime_min": 3, "btc": {"sats_por_dolar": 1500, "bloco": 840000}, "genes": {"olhos": "laser"},
                "raridade": "raro"}

    def salvar_cfg(self):
        self.salvou += 1

    def panico(self): pass
    def sudo_moon(self): pass
    def alimentar(self): return "nham"
    def carinho(self): return None
    def alternar_sats(self): return "sats on"
    def skins(self): return ["padrao"]
    def trocar_skin(self, s): return None
    def trocar_moeda(self, m): return None
    def carteira(self, a): return ["carteira", str(a)]
    def compartilhar(self): return ["share"]
    def ranking(self, a): return ["rank"]
    def alternar_hardcore(self): return ["hardcore ligado"]


def test_console_comandos_basicos():
    ctx = CtxFake()
    c = console.Console(ctx)
    for linha in ["help", "price", "feed", "pet", "stats", "sats", "skin", "skin gato", "wallet", "wallet bc1q",
                  "wallet eth", "play", "share", "rank", "genes", "petcode", "breed", "breed 1", "stable", "adopt",
                  "battle", "hardcore", "hardcore off", "hardcore on", "rip", "export", "card", "shop", "shop open",
                  "redeem", "redeem X", "paper", "news", "coin", "coin LOL", "coin ETH", "neofetch", "whoami", "ls",
                  "cat seed.txt", "cat x", "ping", "sudo moon", "sudo ls", "git blame", "rm -rf /", "lolwut",
                  "halving", "ai", "ai set ftp://x", "ai off", "ask"]:
        out = c.executar(linha)
        assert isinstance(out, list) and out, linha
        assert not any(str(x).startswith("erro:") for x in out), (linha, out)
    assert c.executar("   ") == []
    assert c.executar("ai set https://api.exemplo/v1 sk-segredo modelo")[0].startswith("IA ligada")
    assert ctx.cfg["ai_modelo"] == "modelo" and "sk-segredo" not in " ".join(c.historico)
    assert ctx.salvou == 2


def test_console_sem_rede_nao_mostra_erro_cru(monkeypatch):
    c = console.Console(CtxFake())

    def boom(*a, **k):
        raise TimeoutError("timeout")

    monkeypatch.setattr(console.onchain, "fees", boom)
    monkeypatch.setattr(console.onchain, "hashrate", boom)
    monkeypatch.setattr(console.onchain, "gas_eth", boom)
    for cmd in ("mempool", "hashrate", "gas"):
        assert "sem rede agora" in c.executar(cmd)[0]


# ---------------- sprites: renderiza TODA combinação (arte + cobertura) ----------------
@pytest.mark.parametrize("moeda", list(sprites.PERSONAGENS))
def test_sprites_todas_combinacoes_renderizam(moeda):
    for est in sprites.ESTAGIOS:
        for linha in sprites.LINHAS:
            img = sprites.desenhar(moeda, "padrao", linha, 0, estagio=est)
            assert img.size == (sprites.W, sprites.W) and img.getbbox(), (moeda, est, linha)
    for sk in sprites.SKINS:
        assert sprites.desenhar(moeda, sk, "garimpando", 1).getbbox()


def test_sprites_contato_e_gifs(tmp_path):
    folhas = [sprites.sheet("BTC", "padrao"), sprites.sheet("ETH", "gato", "bebe")]
    assert sprites.contato(folhas, escala=1).size[0] > 0
    sprites.gif_demo("SOL", "padrao", tmp_path / "d.gif", escala=1)
    sprites.gif_evolucao("DOGE", tmp_path / "e.gif", escala=1)
    assert (tmp_path / "d.gif").stat().st_size > 0 and (tmp_path / "e.gif").stat().st_size > 0


# ---------------- v1.5 passo 4: arte ----------------
def test_formas_finais_unicas():
    from satoshipet import sprites as sp
    for m in ("ETH", "SOL", "DOGE", "PEPE"):
        adulto = sp.desenhar(m, "padrao", "garimpando", 0, estagio="adulto").tobytes()
        assert sp.desenhar(m, "padrao", "garimpando", 0, estagio="whale").tobytes() != adulto
        assert m in sp.FINAIS and sp.NOMES_FINAIS[m]


def test_pacotes_tem_estagios_e_genes_de_forma():
    from satoshipet import loja
    cat = loja.catalogo()
    for pid, m in cat.items():
        for est in ("ovo", "bebe", "whale", "diamond"):
            assert loja.folha(m, "PEPE", est).endswith(f"PEPE_{est}.png"), (pid, est)
        assert loja.folha(m, "PEPE").endswith("PEPE.png")
        g = loja.genes_permitidos(m, {"paleta": "noir", "olhos": "laser", "acessorio": "laco"})
        assert g is None or "paleta" not in g
    assert "olhos" not in (loja.genes_permitidos(cat["neon_nights"], {"olhos": "laser", "acessorio": "laco"}) or {})


def test_chapeu_nao_cobre_olhos_do_sapo():
    from PIL import Image

    from satoshipet import juice, recursos
    sh = Image.open(recursos.ASSETS / "sprites" / "PEPE_padrao.png").convert("RGBA")
    fr = sh.crop((0, 0, 48, 48))
    com = juice.aplicar_chapeu(fr, "halloween")
    olho = [(x, y) for y in range(48) for x in range(48) if fr.getpixel((x, y))[:3] == (244, 244, 244)][:6]
    assert olho and all(com.getpixel(p) == fr.getpixel(p) for p in olho)
