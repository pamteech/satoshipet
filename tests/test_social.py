"""Rodada social: servidor de ranking, cliente opt-in, card de share, validador de skins e site."""
import json
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "server"))
sys.path.insert(0, str(RAIZ / "tools"))
import ranking as srv_mod

import validate_skin
from satoshipet import console, ranking, share

DEV = "0123456789abcdef0123456789abcdef"


def _stats(**k):
    d = {"device_id": DEV, "nick": "satoshi_fan", "xp": 100, "nivel": 4, "estagio": "BEBE", "blocos": 3,
         "conquistas": 2, "moeda": "BTC"}
    d.update(k)
    return d


# ---------- servidor ----------
@pytest.mark.parametrize("ruim", [
    {"nick": "bc1qxy2kgdygjrsq"}, {"nick": "0xdeadbeef"}, {"nick": "a@b.co"}, {"nick": "x"},
    {"device_id": "123"}, {"xp": -1}, {"xp": 10**12}, {"estagio": "DEUS"}, {"moeda": "LUNA"}, {"xp": "muito"},
])
def test_servidor_recusa_lixo(ruim):
    assert srv_mod.Ranking.limpar(_stats(**ruim))[1]


def test_servidor_lista_branca_sem_dados_pessoais():
    r, erro = srv_mod.Ranking.limpar(_stats(email="a@b.com", carteira="bc1q...", ip="1.2.3.4"))
    assert not erro and set(r) == {"device_id", "nick", "xp", "nivel", "estagio", "blocos", "conquistas", "moeda"}


def test_rate_limit():
    rk = srv_mod.Ranking()
    assert rk.permitido("1.1.1.1", "a" * 32, agora=1000)
    assert not rk.permitido("1.1.1.1", "a" * 32, agora=1005)      # mesmo device, cedo demais
    for i in range(srv_mod.POSTS_POR_MIN_IP - 1):
        assert rk.permitido("1.1.1.1", f"{i:032x}", agora=1010)
    assert not rk.permitido("1.1.1.1", "f" * 32, agora=1011)      # IP estourou
    assert rk.permitido("1.1.1.1", "f" * 32, agora=1100)          # 1 min depois, de boa


def test_top_ordena_e_esconde_device():
    rk = srv_mod.Ranking()
    for i, xp in enumerate([50, 500, 5]):
        rk.salvar(srv_mod.Ranking.limpar(_stats(device_id=f"{i:032x}", nick=f"pet{i}", xp=xp))[0])
    assert rk.salvar(srv_mod.Ranking.limpar(_stats(device_id=f"{0:032x}", nick="pet0", xp=5000))[0]) == 1  # upsert
    top = rk.top()
    assert [j["nick"] for j in top] == ["pet0", "pet1", "pet2"] and all("device_id" not in j for j in top)


@pytest.fixture()
def servidor():
    srv = srv_mod.criar_servidor("127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_http_e_cliente_ponta_a_ponta(servidor):
    cfg = {"ranking": False, "ranking_url": servidor, "nick": "", "device_id": ""}
    st = {"xp": 777, "nivel": 9, "estagio": "ADULTO", "conquistas": "5/19", "moeda": "BTC", "btc": {"comidos": 12}}
    assert not ranking.ligado(cfg)                                   # opt-in
    assert "opt-in" in " ".join(ranking.comando(cfg, st, []))
    assert "uso" in ranking.comando(cfg, st, ["on", "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"])[0]
    linhas = ranking.comando(cfg, st, ["on", "pam_hodl"])
    assert ranking.ligado(cfg) and re.fullmatch(r"[0-9a-f]{32}", cfg["device_id"])
    assert any("#1" in l for l in linhas) and any("pam_hodl" in l for l in linhas)
    assert set(ranking.payload(cfg, st)) == {"device_id", "nick", "xp", "nivel", "estagio", "blocos", "conquistas", "moeda"}
    top = json.loads(urllib.request.urlopen(servidor + "/api/top").read())["top"]
    assert top[0] == {"pos": 1, "nick": "pam_hodl", "xp": 777, "nivel": 9, "estagio": "ADULTO", "blocos": 12,
                      "conquistas": 5, "moeda": "BTC"}
    with pytest.raises(urllib.error.HTTPError) as e:                 # rate limit do device
        urllib.request.urlopen(urllib.request.Request(servidor + "/api/stats", json.dumps(ranking.payload(cfg, st)).encode()))
    assert e.value.code == 429
    assert "desligado" in ranking.comando(cfg, st, ["off"])[0] and not ranking.ligado(cfg)


def test_cliente_offline_degrada():
    cfg = {"ranking": True, "ranking_url": "http://127.0.0.1:9", "nick": "anon", "device_id": DEV}
    assert "offline" in ranking.comando(cfg, {"xp": 1}, [])[-1]


# ---------- share ----------
ST = {"nome": "Satoshinho", "moeda": "BTC", "estagio": "WHALE", "nivel": 15, "xp": 2015, "xp_pct": 0.6,
      "preco_fmt": "$100.00", "variacao_pct": 3.0, "humor": "moon", "skin": "padrao", "btc": {"comidos": 42},
      "carteira": {"endereco": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"}}


@pytest.mark.parametrize("est", ["OVO", "BEBE", "ADULTO", "WHALE", "DIAMOND HANDS"])
def test_card_1200x675_todos_estagios(est):
    img = share.gerar(dict(ST, estagio=est), ["genesis", "whale_alert"])
    assert img.size == (1200, 675)
    assert len(img.convert("RGB").getcolors(1 << 16)) <= 64      # pixel art de verdade, sem blur


def test_card_salva_e_url_x(tmp_path):
    p = share.salvar(ST, ["genesis"], pasta=tmp_path)
    assert p.exists() and Image.open(p).size == (1200, 675)
    url = share.url_x(ST, "https://exemplo.dev")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert url.startswith("https://x.com/intent/post?") and q["url"] == ["https://exemplo.dev"]
    assert "LV15" in q["text"][0] and "bc1q" not in url             # nunca vaza a carteira


def test_console_share_e_rank():
    class Ctx:
        def compartilhar(self):
            return ["card salvo"]

        def ranking(self, a):
            return [f"rank {a}"]
    c = console.Console(Ctx())
    assert c.executar("share") == ["card salvo"] and c.executar("rank on pam") == ["rank ['on', 'pam']"]
    assert "share" in " ".join(c.executar("help")) and "rank" in " ".join(c.executar("help"))


# ---------- skins ----------
def test_validador_aceita_slime_e_recusa_ruim(tmp_path):
    erros, _, img = validate_skin.validar(RAIZ / "src/satoshipet/assets/skins/slime")
    assert not erros and img.size == (192, 192)
    ruim = tmp_path / "ruim"
    ruim.mkdir()
    Image.new("RGBA", (192, 192), (255, 0, 0, 128)).save(ruim / "sheet.png")
    (ruim / "skin.json").write_text('{"id": "Ruim!", "nome": "x"}')
    erros, _, _ = validate_skin.validar(ruim)
    assert len(erros) >= 4
    assert validate_skin.main([str(ruim)]) == 1
    assert validate_skin.main(["--all", "--preview", str(tmp_path / "prev")]) == 0
    assert (tmp_path / "prev" / "slime.png").exists() and (tmp_path / "prev" / "slime.gif").exists()


# ---------- site ----------
def test_site_estatico_completo():
    site = RAIZ / "site"
    html = (site / "index.html").read_text(encoding="utf-8")
    for meta in ('property="og:image"', 'name="twitter:card"', 'property="og:title"'):
        assert meta in html
    assert Image.open(site / "assets" / "og.png").size == (1200, 630)
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', html):
        assert (site / ref).exists(), ref
    js = (site / "app.js").read_text(encoding="utf-8")
    chaves_pt = set(re.findall(r'data-i18n="(\w+)"', html))
    chaves_en = set(re.findall(r"(\w+): \"", js.split("const EN = {")[1].split("};")[0]))
    assert chaves_pt <= chaves_en, chaves_pt - chaves_en                # EN cobre tudo
    cfg = (site / "config.js").read_text(encoding="utf-8")
    assert "pamteech" in cfg and "gumroad" in cfg and "releases" in cfg
    for nome in re.findall(r'data-sheet="(\w+)"', html):
        assert (site / "assets" / "sprites" / f"{nome}.png").exists()
