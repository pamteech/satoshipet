"""v1.3: licenças (HTTP mockado), servidor Hotmart, updates, crash log, migração, sons, juice."""
import datetime as dt
import json
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "server"))
import licencas as srv_lic  # noqa: E402

from tamagoshi_cripto import config, crashlog, juice, license, licencas, recursos, sons, updates  # noqa: E402


class Resp:
    def __init__(self, cod=200, js=None):
        self.status_code, self._js = cod, js
        self.content = b"x" if js is not None else b""

    def json(self):
        if self._js is None:
            raise ValueError
        return self._js


class HTTP:
    """Finge ser o requests: responde por URL e anota as chamadas."""
    def __init__(self, rotas=None, erro=None):
        self.rotas, self.erro, self.chamadas = rotas or {}, erro, []

    def _r(self, url, dados):
        self.chamadas.append((url, dados))
        if self.erro:
            raise self.erro
        for pedaco, resp in self.rotas.items():
            if pedaco in url:
                return resp(dados) if callable(resp) else resp
        return Resp(404, {})

    def post(self, url, data=None, **k):
        return self._r(url, data)

    def get(self, url, params=None, **k):
        return self._r(url, params)


# ---------------- licenças ----------------
def test_hmac_offline_padrao():
    cfg = {}
    ch = license.gerar_chave("a@b.com")
    assert licencas.verificar(cfg, "a@b.com", ch).ok
    r = licencas.verificar(cfg, "a@b.com", "AAAA-BBBB-CCCC-DDDD")
    assert not r.ok and "inválida" in r.msg


def test_gumroad_ok_reembolso_e_produto():
    cfg = {"licenca_provedor": "gumroad", "licenca_produto": "prod123"}
    ok = Resp(200, {"success": True, "purchase": {"email": "a@b.com", "refunded": False}})
    http = HTTP({"gumroad": ok})
    r = licencas.verificar(cfg, "a@b.com", "K-1", http=http, agora=1000)
    assert r.ok and http.chamadas[0][1]["product_id"] == "prod123"
    assert http.chamadas[0][1]["increment_uses_count"] == "false"
    assert cfg["licenca_cache"]["validado_em"] == 1000
    # cache: não bate na rede de novo dentro de 24h
    assert licencas.verificar(cfg, "a@b.com", "K-1", http=HTTP(erro=AssertionError("rede!")), agora=2000).fonte == "cache"
    reemb = HTTP({"gumroad": Resp(200, {"success": True, "purchase": {"refunded": True}})})
    r = licencas.verificar(cfg, "a@b.com", "K-1", http=reemb, forcar=True)
    assert not r.ok and "reembolsada" in r.msg and cfg["licenca_cache"] == {}
    nao = HTTP({"gumroad": Resp(404, {"success": False, "message": "That license does not exist"})})
    assert "não encontrada" in licencas.verificar(cfg, "a@b.com", "K-2", http=nao).msg
    assert "product_id" in licencas.verificar({"licenca_provedor": "gumroad"}, "a", "K", http=http).msg


def test_graca_offline_e_expirada():
    cfg = {"licenca_provedor": "gumroad", "licenca_produto": "p"}
    licencas.verificar(cfg, "a@b.com", "K", http=HTTP({"gumroad": Resp(200, {"success": True, "purchase": {}})}), agora=0)
    off = HTTP(erro=ConnectionError("sem rede"))
    dia = 86400
    r = licencas.verificar(cfg, "a@b.com", "K", http=off, agora=3 * dia)
    assert r.ok and r.fonte == "graca" and "11 dia" in r.msg
    r = licencas.verificar(cfg, "a@b.com", "K", http=off, agora=15 * dia)
    assert not r.ok and "internet" in r.msg
    assert licencas.verificar(cfg, "a@b.com", "K", http=HTTP({"gumroad": Resp(503, {})}), agora=20 * dia).fonte == "offline"


def test_lemonsqueezy_ativa_depois_valida():
    cfg = {"licenca_provedor": "lemonsqueezy", "licenca_produto": "42", "nome_pet": "Satoshi Jr"}
    ativ = Resp(200, {"activated": True, "instance": {"id": "inst-1"}, "license_key": {"status": "active"},
                      "meta": {"product_id": 42, "customer_email": "a@b.com"}})
    http = HTTP({"/activate": ativ})
    assert licencas.verificar(cfg, "a@b.com", "LS-KEY", http=http, agora=0).ok
    assert http.chamadas[0][1]["instance_name"] == "Satoshi Jr" and cfg["licenca_cache"]["instance_id"] == "inst-1"
    val = HTTP({"/validate": Resp(200, {"valid": True, "license_key": {"status": "active"}, "meta": {"product_id": 42}})})
    assert licencas.verificar(cfg, "a@b.com", "LS-KEY", http=val, forcar=True).ok
    assert val.chamadas[0][1] == {"license_key": "LS-KEY", "instance_id": "inst-1"}
    limite = HTTP({"/activate": Resp(400, {"activated": False, "error": "This license key has reached the activation limit."})})
    assert "limite de ativações" in licencas.verificar({"licenca_provedor": "lemonsqueezy"}, "", "X", http=limite).msg
    outro = HTTP({"/activate": Resp(200, {"activated": True, "instance": {"id": "i"}, "license_key": {"status": "active"},
                                          "meta": {"product_id": 7}})})
    assert "outro produto" in licencas.verificar({"licenca_provedor": "lemonsqueezy", "licenca_produto": "42"}, "", "Y", http=outro).msg
    exp = HTTP({"/validate": Resp(200, {"valid": False, "license_key": {"status": "expired"}})})
    assert "expirada" in licencas.verificar(cfg, "a@b.com", "LS-KEY", http=exp, forcar=True).msg


def test_provedor_desconhecido_e_chave_vazia():
    assert "desconhecido" in licencas.verificar({"licenca_provedor": "paypal"}, "a", "b").msg
    assert "Cola a chave" in licencas.verificar({}, "a", "  ").msg


# ---------------- servidor de chaves (Hotmart) ----------------
@pytest.fixture()
def srv():
    enviados = []
    s = srv_lic.criar_servidor("127.0.0.1", 0, hottok="tok123", segredo=b"seg", admin="adm",
                               mailer=lambda e, c: enviados.append((e, c)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    s.enviados = enviados
    s.url = f"http://127.0.0.1:{s.server_address[1]}"
    yield s
    s.shutdown()


def _webhook(s, ev, email, tok="tok123"):
    corpo = json.dumps({"event": ev, "data": {"buyer": {"email": email}, "purchase": {"transaction": "HP1"}}}).encode()
    req = urllib.request.Request(s.url + "/hotmart/webhook", corpo, {"X-HOTMART-HOTTOK": tok,
                                                                    "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as e:
        return e.code


def test_hotmart_fluxo_completo_com_app(srv):
    import requests
    assert _webhook(srv, "PURCHASE_APPROVED", "Pam@Ex.com", tok="errado") == 401
    assert _webhook(srv, "PURCHASE_APPROVED", "Pam@Ex.com") == 200
    email, chave = srv.enviados[0]
    assert email == "pam@ex.com" and chave == srv_lic.gerar_chave(b"seg", "pam@ex.com")
    cfg = {"licenca_provedor": "servidor", "licenca_url": srv.url}
    assert licencas.verificar(cfg, "pam@ex.com", chave, http=requests).ok           # HTTP de verdade
    assert "outro e-mail" in licencas.verificar(cfg, "x@y.com", chave, http=requests, forcar=True).msg
    assert _webhook(srv, "PURCHASE_REFUNDED", "pam@ex.com") == 200
    r = licencas.verificar(cfg, "pam@ex.com", chave, http=requests, forcar=True)
    assert not r.ok and "reembolsada" in r.msg
    adm = urllib.request.Request(srv.url + "/admin/chaves", headers={"Authorization": "Bearer adm"})
    assert json.loads(urllib.request.urlopen(adm).read())["licencas"][0]["status"] == "revogada"


# ---------------- updates ----------------
def test_updates():
    assert updates.mais_nova("v1.4.0", "1.3.0") and not updates.mais_nova("1.3.0", "1.3.0")
    assert updates.mais_nova("2.0", "1.9.9") and not updates.mais_nova("v1.2.9", "1.3.0")
    rel = Resp(200, {"tag_name": "v9.0.0", "html_url": "https://github.com/x/y/releases/tag/v9.0.0", "body": "novidades"})
    info = updates.checar("x/y", "1.3.0", http=HTTP({"releases/latest": rel}))
    assert info == {"versao": "9.0.0", "url": "https://github.com/x/y/releases/tag/v9.0.0", "notas": ["novidades"]}
    assert updates.checar("x/y", "9.0.0", http=HTTP({"releases/latest": rel})) is None
    assert updates.checar("OWNER/tamagoshi-cripto", http=HTTP(erro=AssertionError("não chama!"))) is None
    pre = Resp(200, {"tag_name": "v10.0.0", "prerelease": True})
    assert updates.checar("x/y", "1.0", http=HTTP({"latest": pre})) is None
    assert updates.checar("x/y", "1.0", http=HTTP(erro=OSError())) is None


# ---------------- crash log ----------------
def test_crashlog(tmp_path, monkeypatch):
    monkeypatch.setattr(crashlog, "ARQUIVO", tmp_path / "crash.log")
    monkeypatch.setattr(crashlog, "PASTA", tmp_path)
    try:
        raise ValueError(f"boom em {Path.home()}/segredo")
    except ValueError:
        crashlog.registrar(*sys.exc_info(), contexto="teste")
    assert "ValueError" in crashlog.ultimo()
    url = crashlog.url_issue("x/y")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert url.startswith("https://github.com/x/y/issues/new?") and "ValueError" in q["body"][0]
    assert str(Path.home()) not in q["body"][0]                      # não vaza o usuário


# ---------------- migração de config ----------------
def test_migracao(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    monkeypatch.setattr(config, "CONFIG_PATH", p)
    assert config.carregar()["onboarding_ok"] is False              # instalação nova vê a intro
    p.write_text(json.dumps({"moeda": "ETH", "evolucao": {"xp": 300}, "escala": "9", "skin": "default"}))
    c = config.carregar()
    assert c["versao_config"] == config.VERSAO_CONFIG and c["onboarding_ok"] is True
    assert c["escala"] == 6 and c["skin"] == "padrao" and c["moeda"] == "ETH" and c["evolucao"] == {"xp": 300}
    assert c["licenca_provedor"] == "hmac" and c["musica"] is False
    assert config.migrar(dict(c)) == c                              # idempotente


# ---------------- sons ----------------
def test_sons_chiptune(tmp_path):
    assert sons.hz("A4") == 440.0 and round(sons.hz("C5")) == 523 and sons.hz("-") == 0
    for nome, m in sons.MUSICAS.items():
        a = sons.renderizar(m)
        assert a and max(abs(x) for x in a) <= 1.0, nome
    import wave
    sons.gerar_wav(sons.BGM, tmp_path / "bgm.wav", .1)
    with wave.open(str(tmp_path / "bgm.wav")) as w:
        assert 4 < w.getnframes() / w.getframerate() < 15             # loop curtinho
    s = sons.Som(mudo=True)
    assert not s.musica(True) and not s.tocar("moon")


# ---------------- juice ----------------
def test_chapeus_e_periodos():
    assert juice.chapeu_do_dia(dt.date(2026, 10, 22)) == "halloween"
    assert juice.chapeu_do_dia(dt.date(2026, 12, 20)) == "natal"
    assert juice.chapeu_do_dia(dt.date(2026, 7, 1)) is None
    fr = Image.open(recursos.ASSETS / "sprites" / "BTC_padrao.png").convert("RGBA").crop((0, 0, 48, 48))
    for t in ("halloween", "natal"):
        c = juice.aplicar_chapeu(fr, t)
        assert c.size == (48, 48) and c.tobytes() != fr.tobytes()
        assert set(c.getchannel("A").getdata()) <= {0, 255}          # pixel art: nada de alfa pela metade
    assert juice.aplicar_chapeu(fr, None) is fr
    assert [juice.periodo(h) for h in (3, 9, 15, 21)] == ["madrugada", "manha", "tarde", "noite"]


def test_particulas():
    p = juice.Particulas(semente=1)
    p.emitir("rekt", 100, 100)
    assert p.ativo and p.tremor == 9 and p.deslocamento() != (None, None)
    for _ in range(40):
        p.tick()
    assert not p.ativo
    for _ in range(10):
        p.emitir("moon", 0, 0)
    assert len(p.p) <= juice.Particulas.MAX
