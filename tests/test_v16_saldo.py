"""v1.6: saldo watch-only no painel - formato, privacidade, backoff, marcos e NADA vazando."""
import json

from satoshipet import api, cartao, config, console, ranking, saldo


class FakeResp:
    status_code = 200

    def __init__(self, d):
        self.d = d

    def raise_for_status(self):
        pass

    def json(self):
        return self.d


def test_linha_brl_usd_e_oculto():
    p = {"BTC": {"brl": 605700.0, "usd": 81000.0}}
    assert saldo.linhas({"BTC": 0.0123}, p, "brl", False) == [("SALDO 0.0123 BTC ≈ R$ 7.450", "#ffcd75")]
    assert saldo.linhas({"BTC": 0.0123}, p, "usd", False)[0][0] == "SALDO 0.0123 BTC ≈ $996"
    assert saldo.linhas({"BTC": 0.0123}, p, "brl", True)[0][0] == "SALDO •••• BTC"
    assert saldo.linhas({"SOL": 2.5}, {}, "brl", False)[0][0] == "SALDO 2.5000 SOL"   # sem cotação: só a qtd
    assert saldo.fmt_fiat(12.3456, "brl") == "R$ 12,35"


def test_fiat_por_idioma():
    assert saldo.fiat_efetiva("auto", "pt") == "brl" and saldo.fiat_efetiva("auto", "en") == "usd"
    assert saldo.fiat_efetiva("usd", "pt") == "usd"


def test_buscar_fiat(monkeypatch):
    visto = {}

    def get(url, params, timeout, headers):
        visto.update(params)
        return FakeResp({"bitcoin": {"brl": 1.0, "usd": 2.0}})
    monkeypatch.setattr(saldo.requests, "get", get)
    assert saldo.buscar_fiat(["BTC"]) == {"BTC": {"brl": 1.0, "usd": 2.0}}
    assert visto["vs_currencies"] == "brl,usd"


def test_backoff():
    t = [0.0]
    b = saldo.Backoff(base=180, teto=1800, relogio=lambda: t[0])
    assert b.hora()
    b.erro()
    b.erro()
    assert b.intervalo == 720 and not b.hora()
    for _ in range(10):
        b.erro()
    assert b.intervalo == 1800
    b.ok()
    assert b.intervalo == 180


def test_marcos():
    assert saldo.marco_novo("BTC", None, 1) is None          # 1ª leitura não comemora
    assert saldo.marco_novo("BTC", 0.009, 0.011) == 0.01
    assert saldo.marco_novo("BTC", 0.02, 0.03) is None
    assert saldo.marco_novo("ETH", 0.5, 12) == 10.0


def test_padrao_e_nao_persiste():
    assert config.PADRAO["saldo_fiat"] == "auto" and config.PADRAO["saldo_oculto"] is False
    assert not any("saldo" in k and k not in ("saldo_fiat", "saldo_oculto") for k in config.PADRAO)


def test_publico_tira_saldo():
    st = {"carteira": {"endereco": "bc1qxxxxxxxxxxxxxxxxxxxxxx", "saldo_sats": 5}, "carteiras": {"eth": 1.0}}
    p = api.publico(st)
    assert "saldo_sats" not in p["carteira"] and "carteiras" not in p
    assert "saldo_sats" in st["carteira"]  # não mexe no original


def test_card_e_ranking_sem_saldo():
    st = {"nome": "x", "moeda": "BTC", "xp": 1, "nivel": 1, "carteira": {"saldo_sats": 999}, "carteiras": {"eth": 7}}
    assert "999" not in json.dumps(cartao.exportar_stats(st)) and "carteira" not in json.dumps(cartao.exportar_stats(st))
    assert "999" not in json.dumps(ranking.payload({"device_id": "a"}, st))


def test_console_saldo():
    class Ctx:
        def comando_saldo(self, a):
            return ["ok " + " ".join(a)]
    c = console.Console(Ctx())
    assert c.executar("saldo off") == ["ok off"]
    assert any("saldo" in ln for ln in c.executar("help"))
