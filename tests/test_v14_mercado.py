"""v1.4 fase 2: paper trading, ETH/SOL watch-only, baleias e RSS (sem rede)."""
import pytest

from satoshipet import baleias, multichain, noticias, papel


def test_paper_compra_vende_e_pnl():
    c = papel.nova()
    ok, msg = papel.comprar(c, "BTC", 1000, 50_000)
    assert ok and "FICTÍCIO" in msg and c["usd"] == 9000
    r = papel.resumo(c, {"BTC": 55_000})
    assert r["pnl"] > 0 and r["aviso"] == "DINHEIRO FICTÍCIO" and papel.humor(r["pnl_pct"]) is None
    ok, msg = papel.vender(c, "BTC", "all", 55_000)
    assert ok and "BTC" not in c["pos"] and c["usd"] > 10_000
    assert c["hist"][-1]["lucro"] > 0
    assert not papel.comprar(c, "BTC", 999_999, 1)[0]      # sem saldo fictício
    assert not papel.vender(c, "ETH", 1, 3000)[0]          # não tem ETH
    assert not papel.comprar(c, "BTC", 10, None)[0]        # sem preço
    assert not papel.comprar(c, "BTC", -5, 10)[0]


def test_paper_humor():
    assert papel.humor(6) == "moon" and papel.humor(-6) == "rekt" and papel.humor(1) is None


def test_paper_venda_parcial_mantem_custo_proporcional():
    c = papel.nova()
    papel.comprar(c, "ETH", 2000, 2000)
    q = c["pos"]["ETH"]
    papel.vender(c, "ETH", q / 2, 2000)
    assert abs(c["custo"]["ETH"] - 1000) < 1e-6


@pytest.mark.parametrize("rede,end", [("eth", "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe"),
                                      ("sol", "vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg")])
def test_enderecos_publicos_ok(rede, end):
    assert multichain.validar(rede, end)[0]


@pytest.mark.parametrize("lixo", [
    "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318",          # chave privada ETH
    "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318",
    "5" + "K" * 87,                                                               # secret key SOL base58
    "[" + ",".join(["12"] * 64) + "]",                                            # keypair.json
    "abandon " * 11 + "about",                                                    # seed
])
def test_chaves_e_seeds_sao_recusadas(lixo):
    for rede in ("eth", "sol"):
        ok, msg = multichain.validar(rede, lixo)
        assert not ok and "CHAVE PRIVADA" in msg


def test_saldos_via_rpc_mockado(monkeypatch):
    chamadas = []

    def falso(urls, metodo, params, timeout=10):
        chamadas.append(metodo)
        return {"getBalance": {"value": 2_500_000_000}, "eth_getBalance": hex(3 * 10 ** 18)}[metodo]
    monkeypatch.setattr(multichain, "_rpc", falso)
    assert multichain.saldo_eth("0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe") == 3
    assert multichain.saldo_sol("vines1vzrYbzLMRdu58ou5XTby4qAqVRLmqo36NKPTg") == 2.5
    with pytest.raises(ValueError):
        multichain.saldo_eth("0x" + "a" * 64)
    assert chamadas == ["eth_getBalance", "getBalance"]


def test_radar_de_baleia():
    r = baleias.Radar(50)
    txs = [{"txid": "a", "value": 10 * 10 ** 8}, {"txid": "b", "value": 120 * 10 ** 8},
           {"txid": "c", "value": 80 * 10 ** 8}]
    novas = r.filtrar(txs)
    assert [b["txid"] for b in novas] == ["b", "c"] and novas[0]["url"].endswith("/tx/b")
    assert r.filtrar(txs) == []  # já vistas
    assert "120" in baleias.frase(novas[0])


RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title><![CDATA[Bitcoin hits <b>new</b> high \xe2\x80\x94 again \xf0\x9f\x9a\x80]]></title>
<link>https://example.com/a</link></item>
<item><title>sem link seguro</title><link>http://example.com/b</link></item>
<item><title>Ether &amp; SOL rally</title><link>https://example.com/c</link></item>
</channel></rss>"""


def test_rss_parse_limpa_titulo():
    itens = noticias.parse(RSS, "Teste")
    assert [i["link"] for i in itens] == ["https://example.com/a", "https://example.com/c"]
    assert itens[0]["titulo"] == "Bitcoin hits new high - again" and itens[1]["titulo"] == "Ether & SOL rally"
    assert all(ord(ch) < 256 for i in itens for ch in i["titulo"])
