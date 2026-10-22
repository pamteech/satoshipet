"""v1.7: clima, calendário cripto, conquistas de mercado, LAN e acessibilidade (lógica pura)."""
import datetime as dt
import json

from tamagoshi_cripto import acessibilidade, calendario, clima, conquistas, i18n, lan


class R:
    status_code = 200

    def __init__(self, d):
        self.d = d

    def raise_for_status(self):
        pass

    def json(self):
        return self.d


def test_clima_codigos_e_busca(monkeypatch):
    assert [clima.tipo_por_codigo(c) for c in (0, 3, 45, 61, 75, 95)] == \
        ["sol", "nublado", "neblina", "chuva", "neve", "tempestade"]
    visto = {}

    def get(url, params=None, timeout=None, headers=None):
        visto.update(params or {})
        return R({"current": {"weather_code": 63, "is_day": 0, "temperature_2m": 18.5}})
    monkeypatch.setattr(clima.requests, "get", get)
    d = clima.buscar(-23.5505, -46.6333)
    assert d["tipo"] == "chuva" and d["dia"] is False and d["temp"] == 18.5
    assert visto["latitude"] == -23.55 and visto["longitude"] == -46.63  # arredondado (~1 km)


def test_clima_cidade_latlon_e_cache(monkeypatch):
    monkeypatch.setattr(clima.requests, "get", lambda *a, **k: R({"results": [
        {"name": "São Paulo", "latitude": -23.5475, "longitude": -46.63611}]}))
    assert clima.geocodificar("sao paulo") == ("São Paulo", -23.55, -46.64)
    assert clima.parse_latlon("-23.5, -46.6") == (-23.5, -46.6) and clima.parse_latlon("91,0") is None
    assert clima.parse_latlon("abc") is None
    t = [0.0]
    c = clima.Cache(relogio=lambda: t[0])
    c.erro()
    assert not c.hora() and c.prox == 120
    c.ok({"tipo": "sol"})
    assert c.prox == clima.INTERVALO and c.dado["tipo"] == "sol"
    assert clima.efetivo(None, 22) == {"tipo": None, "dia": False, "temp": None}


def test_calendario():
    assert calendario.evento_do_dia(dt.date(2027, 5, 22)) == "pizza"
    assert calendario.evento_do_dia(dt.date(2026, 10, 31)) == "whitepaper"
    assert calendario.evento_do_dia(dt.date(2027, 1, 3)) == "genesis"
    assert calendario.evento_do_dia(dt.date(2026, 12, 25)) == "natal"
    assert calendario.carnaval(2027) == dt.date(2027, 2, 9)  # terça de carnaval 2027
    assert calendario.evento_do_dia(dt.date(2027, 2, 6)) == "carnaval"
    assert calendario.evento_do_dia(dt.date(2027, 3, 1)) is None
    h = calendario.halving(1_049_000)
    assert h["proximo"] == 1_050_000 and h["faltam"] == 1000 and h["numero"] == 5
    assert "1000 blocos" in calendario.contagem(h) and calendario.contagem(calendario.halving(900_000)) is None
    assert calendario.contagem(calendario.halving(1_049_900)) == "HALVING EM 100 BLOCOS!"
    assert calendario.ativo(dt.date(2027, 3, 1), 1_050_000)["id"] == "halving"
    for ev in calendario.EVENTOS.values():
        assert ev["frases"] and ev["nome"]


def test_conquistas_mercado():
    t = [1000.0]
    m = conquistas.Mercado(agora=lambda: t[0])
    assert m.preco("BTC", 100.0) == []
    t[0] += 3600
    assert "crash_10" in m.preco("BTC", 89.0)
    m.ath["BTC"] = 120.0
    t[0] += 60
    assert "ath_vivo" in m.preco("BTC", 121.0) and m.ath["BTC"] == 121.0
    assert m.fng(15) == ["medo_extremo"] and m.fng(50) == []
    assert m.bloco(1_050_000) == ["bloco_halving"] and m.bloco(1_050_001) == []
    assert m.hodl(t[0] - 31 * 86400) == ["hodl_30d"] and m.hodl(t[0] - 86400) == []
    assert m.baleia() == []  # mais de 10 min depois de abrir
    for cid in ("crash_10", "ath_vivo", "hodl_30d", "baleia_cedo", "bloco_halving", "medo_extremo"):
        assert cid in conquistas.LISTA and cid in conquistas.BADGES
        cor, arte = conquistas.BADGES[cid]
        assert len(arte) == 8 and all(len(r) == 8 for r in arte)
    i18n.definir("en")
    try:
        assert i18n.t("Medo Extremo") == "Extreme Fear"
    finally:
        i18n.definir("pt")


def test_lan_pacote_e_validacao():
    p = lan.montar("0a1b2c3d", "Satoshinho", "BTC", "padrao", "moon", "gm")
    d = json.loads(p)
    assert set(d) == {"t", "v", "id", "nome", "moeda", "skin", "humor", "emote"}  # nada pessoal
    assert lan.ler(p)["nome"] == "Satoshinho"
    assert json.loads(lan.montar("0a1b2c3d", "x", "BTC", "loja:neon", "moon"))["skin"] == "padrao"
    ruins = [b"", b"x" * 600, b"\xff\xfe", b"[]", b'{"t":"tama","v":2}',
             json.dumps({"t": "tama", "v": 1, "id": "zz", "nome": "a", "moeda": "BTC", "skin": "padrao",
                         "humor": "moon"}).encode(),
             json.dumps({"t": "tama", "v": 1, "id": "0a1b2c3d", "nome": "<script>", "moeda": "BTC",
                         "skin": "padrao", "humor": "moon"}).encode(),
             json.dumps({"t": "tama", "v": 1, "id": "0a1b2c3d", "nome": "a", "moeda": "XRP", "skin": "padrao",
                         "humor": "moon"}).encode()]
    for r in ruins:
        assert lan.ler(r) is None, r
    extra = json.loads(p)
    extra["carteira"] = "bc1q..."
    assert "carteira" not in lan.ler(json.dumps(extra).encode())


def test_lan_vizinhos_rate_limit_e_visita():
    t = [0.0]
    v = lan.Vizinhos("ffffffff", agora=lambda: t[0], maximo=2)
    assert v.receber(lan.montar("ffffffff", "eu", "BTC", "padrao", "moon")) is None  # eu mesmo
    assert v.receber(lan.montar("00000001", "a", "BTC", "padrao", "moon"))
    assert v.receber(lan.montar("00000001", "a", "BTC", "padrao", "rekt")) is None  # rate limit
    t[0] = 25
    assert v.receber(lan.montar("00000001", "a", "BTC", "padrao", "rekt"))["humor"] == "rekt"
    assert v.receber(lan.montar("00000002", "b", "ETH", "padrao", "moon"))
    assert v.receber(lan.montar("00000003", "c", "SOL", "padrao", "moon")) is None  # limite de amigos
    t[0] = 1000
    assert v.lista() == []  # sumiram há > 5 min
    vis = lan.Visita({"nome": "a", "emote": "wagmi"}, 272, lado=1, emote_meu="gm")
    xs, ems = [], []
    while vis.viva:
        xs.append(vis.x(136, 60))
        ems.append(vis.emote())
        vis.tick()
    assert xs[0] > 272 and xs[15] == 196 and xs[-1] > xs[30]  # entra, para do lado, sai
    assert ("amigo", "wagmi") in ems and ("eu", "gm") in ems


def test_acessibilidade(monkeypatch):
    assert acessibilidade.comando_voz("BTC MOON +3%", "darwin") == ["say", "BTC MOON +3%"]
    cmd = acessibilidade.comando_voz("it's 'ok'; rm -rf", "win32")
    assert "'" not in cmd[-1].split("Speak(")[1][1:-2] and ";" not in cmd[-1].split("Speak(")[1]
    t = [0.0]
    falas = []
    loc = acessibilidade.Locutor(agora=lambda: t[0], rodar=falas.append)
    monkeypatch.setattr(acessibilidade.sys, "platform", "darwin")
    assert not loc.falar("oi", False)           # desligado = mudo
    assert loc.falar("BTC moon", True)
    assert not loc.falar("BTC rekt", True)      # 10 s de intervalo
    t[0] = 11
    assert not loc.falar("BTC moon", True)      # mesmo texto não repete
    assert loc.falar("BTC rekt", True) and len(falas) == 2

    class P:
        stdout = "1\n"
    monkeypatch.setattr(acessibilidade.subprocess, "run", lambda *a, **k: P())
    assert acessibilidade.reduzir_movimento_sistema("darwin")
    assert not acessibilidade.reduzir_movimento_sistema("linux")
