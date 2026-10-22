"""v1.5 - segurança: API local (host, token, CORS, máscara) e chave da IA no chaveiro."""
import json
import urllib.error
import urllib.request

import pytest

from satoshipet import api, segredos


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "TOKEN_PATH", tmp_path / "tok")
    feitos = []
    st = {"moeda": "BTC", "carteira": {"endereco": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"}, "email": "x@y.z",
          "emoji": "", "preco_fmt": "$1", "variacao_pct": 0.0, "nivel": 1}
    s = api.iniciar(lambda: st, porta=0, acoes={"pet": lambda: feitos.append("pet") or "ok"})
    yield s, feitos
    s.shutdown()


def _req(s, caminho, metodo="GET", host=None, token=None):
    url = f"http://127.0.0.1:{s.server_address[1]}{caminho}"
    r = urllib.request.Request(url, method=metodo, data=b"" if metodo == "POST" else None)
    if host:
        r.add_header("Host", host)
    if token:
        r.add_header("Authorization", "Bearer " + token)
    return urllib.request.urlopen(r, timeout=3)


def test_status_mascara_e_sem_cors(srv):
    s, _ = srv
    r = _req(s, "/status")
    assert r.headers.get("Access-Control-Allow-Origin") is None
    st = json.loads(r.read())
    assert st["carteira"]["endereco"] == "bc1qxy…0wlh" and "email" not in st
    assert s.server_address[0] == "127.0.0.1"


def test_host_estranho_recusado(srv):
    s, _ = srv
    with pytest.raises(urllib.error.HTTPError) as e:
        _req(s, "/status", host="evil.example:8737")
    assert e.value.code == 403


def test_escrita_exige_token(srv):
    s, feitos = srv
    with pytest.raises(urllib.error.HTTPError) as e:
        _req(s, "/pet", "POST")
    assert e.value.code == 401
    with pytest.raises(urllib.error.HTTPError):
        _req(s, "/pet", "POST", token="chute")
    tok = api.TOKEN_PATH.read_text().strip()
    assert (api.TOKEN_PATH.stat().st_mode & 0o777) == 0o600 and len(tok) >= 32
    assert json.loads(_req(s, "/pet", "POST", token=tok).read())["ok"] and feitos == ["pet"]
    with pytest.raises(urllib.error.HTTPError) as e:
        _req(s, "/apagar_tudo", "POST", token=tok)
    assert e.value.code == 404


class KRFake:
    def __init__(self):
        self.d = {}

    def get_password(self, s, c):
        return self.d.get((s, c))

    def set_password(self, s, c, v):
        self.d[(s, c)] = v

    def delete_password(self, s, c):
        self.d.pop((s, c), None)


def test_chave_ia_vai_pro_chaveiro(monkeypatch):
    kr = KRFake()
    monkeypatch.setattr(segredos, "_kr", lambda: kr)
    cfg = {"ai_key": "sk-antiga"}
    assert segredos.migrar(cfg) and cfg["ai_key"] == "" and segredos.ler(cfg) == "sk-antiga"
    segredos.gravar(cfg, "")
    assert segredos.ler(cfg) == ""


def test_chave_ia_fallback_sem_chaveiro(monkeypatch):
    monkeypatch.setattr(segredos, "_kr", lambda: None)
    monkeypatch.delenv("SATOSHIPET_AI_KEY", raising=False)
    cfg = {}
    assert segredos.gravar(cfg, "sk-x") == "config local" and segredos.ler(cfg) == "sk-x"
    assert not segredos.migrar(cfg)
