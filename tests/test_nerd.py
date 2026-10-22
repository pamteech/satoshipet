"""Testes da rodada nerd: on-chain, evolução, console, API, conquistas e sprites por estágio."""
import json
import socket
import urllib.request
from pathlib import Path

import pytest

from tamagoshi_cripto import api, conquistas, console, evolucao, onchain, sprites

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True, scope="module")
def _onchain_de_verdade():
    """O test_gui troca os fetchers por mocks no mesmo processo; aqui queremos os originais."""
    import importlib
    global onchain
    onchain = importlib.reload(onchain)


# ---------- on-chain ----------
def test_estomago_calibra_e_come():
    e = onchain.Estomago()
    assert e.novo_tip(900_000, 1) == []          # 1º tip: só calibra
    assert e.novo_tip(900_001, 2) == [900_001]
    assert e.novo_tip(900_001, 2) == []          # mesmo bloco não conta 2x
    assert e.novo_tip(900_020, 3) == list(range(900_015, 900_021))  # no máx. 6
    assert e.comidos == 7


def test_estomago_dorme_depois_de_30_min():
    e = onchain.Estomago({"ts_bloco": 1000})
    assert not e.dormindo(agora=1000 + 29 * 60)
    assert e.dormindo(agora=1000 + 31 * 60)
    assert not onchain.Estomago().dormindo()


@pytest.mark.parametrize("texto", [
    "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi",
    "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ",
    "KwDiBf89QgGbjEhKnhXJuH7LrciVrZi3qYjgd9M7rFU73sVHnoWn",
    " ".join(["abandon"] * 11 + ["about"]),
])
def test_carteira_recusa_chave_privada_e_seed(texto):
    ok, msg = onchain.validar_endereco(texto)
    assert not ok and "PRIVADA" in msg


def test_carteira_aceita_enderecos_publicos():
    for e in ["bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
              "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"]:
        assert onchain.validar_endereco(e)[0], e
    assert not onchain.validar_endereco("xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz")[0]
    assert not onchain.validar_endereco("oi")[0]


def test_saldo_endereco_e_vigia(monkeypatch):
    monkeypatch.setattr(onchain, "_get", lambda c, t=10: {
        "chain_stats": {"funded_txo_sum": 10_000, "spent_txo_sum": 2_000, "tx_count": 3},
        "mempool_stats": {"funded_txo_sum": 500, "spent_txo_sum": 0, "tx_count": 1}})
    s = onchain.saldo_endereco("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
    assert s == {"confirmado": 8000, "pendente": 500, "total": 8500, "txs": 4}
    v = onchain.Vigia()
    assert v.atualizar(8500) == 0 and v.atualizar(9000) == 500 and v.atualizar(100) == -8900


def test_fome_sats_hashrate():
    niveis = [onchain.fome_por_fee(f) for f in (1, 10, 40, 300)]
    assert len({str(n) for n in niveis}) == 4
    assert onchain.sats_por_dolar(100_000) == 1000 and onchain.sats_por_dolar(None) is None
    assert "EH/s" in onchain.formatar_hashrate(1.03e21)


def test_offline_nao_explode(monkeypatch):
    def caiu(*a, **k):
        raise OSError("sem internet")
    monkeypatch.setattr(onchain.requests, "post", caiu)
    monkeypatch.setattr(onchain.requests, "get", caiu)
    for fn in (onchain.gas_eth, onchain.ultimo_bloco, onchain.fees):
        with pytest.raises(Exception):  # quem chama (loop_onchain) engole e mostra "?"
            fn(timeout=1)


# ---------- evolução ----------
def test_estagios_e_nivel():
    assert evolucao.estagio(0) == "ovo"
    assert evolucao.estagio(100) == "bebe"
    assert evolucao.estagio(500) == "adulto"
    assert evolucao.estagio(2000) == "whale"
    assert evolucao.estagio(2000, crashes=3) == "diamond"
    assert evolucao.nivel(0) == 1 and evolucao.nivel(10) == 2
    assert 0 <= evolucao.progresso_nivel(55) < 1


def test_evolucao_ganha_xp():
    ev = evolucao.Evolucao()
    assert ev.ganhar("bloco")            # 25 XP já sobe de nível
    ev.tick_minutos(90); ev.tick_minutos(30)
    assert ev.xp == 25 + 2


# ---------- console ----------
class Ctx:
    def __init__(self):
        self.log = []

    def status(self):
        return {"nome": "Satoshinho", "moeda": "BTC", "preco_fmt": "$100.00", "preco": 100.0,
                "variacao_pct": 1.0, "humor": "moon", "emoji": "🚀", "nivel": 3, "xp": 42, "estagio": "ovo",
                "vida": 5, "uptime_min": 1, "skin": "padrao", "pro": False, "unidade": "usd",
                "btc": {"bloco": 921_337, "fee_sat_vb": 3, "fome": "SACIADO", "comidos": 1,
                        "hashrate": "1.03 EH/s", "dormindo": False, "mempool_tx": 10},
                "eth": {"gas_gwei": 0.4}, "fng": None, "carteira": None, "conquistas": 2}

    def __getattr__(self, nome):
        return lambda *a, **k: self.log.append(nome) or None

    def skins(self):
        return ["padrao", "gato"]


def _txt(linhas):
    return " ".join(l for l in linhas if isinstance(l, str)).lower()


def test_console_comandos_basicos():
    ctx = Ctx()
    c = console.Console(ctx)
    assert "comandos" in _txt(c.executar("help"))
    blame = _txt(c.executar("git blame"))
    assert "money_printer" in blame and "satoshi" in blame
    c.executar("rm -rf /"); c.executar("sudo moon")
    assert "panico" in ctx.log and "sudo_moon" in ctx.log
    assert "não encontrado" in _txt(c.executar("hackear_nasa"))
    assert "shitcoin" in _txt(c.executar("coin XYZ"))
    assert "skins" in _txt(c.executar("skin"))
    assert console.SPRITE in c.executar("neofetch")


def test_console_cat_chave_privada_e_troll():
    assert "not your keys" in _txt(console.Console(Ctx()).executar("cat wallet.dat"))


# ---------- API local ----------
def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_api_status():
    st = Ctx().status()
    porta = _porta_livre()
    srv = api.iniciar(lambda: st, porta)
    try:
        url = f"http://127.0.0.1:{porta}"
        r = urllib.request.urlopen(url + "/status", timeout=3)
        assert r.headers["Access-Control-Allow-Origin"] == "*"
        assert json.loads(r.read())["btc"]["bloco"] == 921_337
        assert "LV3" in urllib.request.urlopen(url + "/status.txt", timeout=3).read().decode()
        assert srv.server_address[0] == "127.0.0.1"   # nunca 0.0.0.0
        assert api.iniciar(lambda: st, porta) is None  # porta ocupada = degrada
    finally:
        srv.shutdown()


# ---------- conquistas e sprites ----------
def test_conquistas_nerd():
    ids = set(conquistas.LISTA)
    assert {"genesis", "pow_100", "not_your_keys", "whale_alert", "diamond_hands", "sudo", "rm_rf", "moscow"} <= ids


def test_sheets_de_todos_estagios_existem():
    pasta = Path(sprites.__file__).parent / "assets" / "sprites"
    faltando = []
    for moeda in ("BTC", "ETH", "SOL", "DOGE", "PEPE"):
        for skin in sprites.SKINS:
            for est in sprites.ESTAGIOS:
                nome = f"{moeda}_{skin}.png" if est == "adulto" else f"{moeda}_{skin}_{est}.png"
                if not (pasta / nome).exists():
                    faltando.append(nome)
    assert not faltando, faltando[:5]
