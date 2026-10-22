"""v1.4 fase 3: card de perfil, IA BYO e extensão do VS Code."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from satoshipet import ai, cartao, genetica

RAIZ = Path(__file__).resolve().parents[1]
STATUS = {"nome": "Satoshinho", "moeda": "ETH", "nivel": 7, "xp": 640, "estagio": "ADULTO", "humor": "moon",
          "variacao_pct": 3.1, "genes": {"paleta": "rosa", "olhos": "neon", "acessorio": "laco", "padrao": "liso"},
          "raridade": "raro", "carteira": {"endereco": "bc1qsegredo", "saldo_sats": 123}, "btc": {"comidos": 9},
          "batalhas": {"vitorias": 2, "derrotas": 1}}


def test_export_so_campos_publicos():
    s = cartao.exportar_stats(STATUS, "1.4.0")
    texto = json.dumps(s)
    assert "bc1qsegredo" not in texto and "carteira" not in s and "saldo" not in texto
    assert s["btc_comidos"] == 9 and s["versao"] == "1.4.0"


def test_svg_animado_com_4_frames():
    svg = cartao.svg(cartao.exportar_stats(STATUS))
    assert svg.startswith("<svg") and svg.count('class="f') == 4 and "@keyframes f3" in svg
    assert "<script" not in svg and "http" not in svg.replace("http://www.w3.org/2000/svg", "")


def test_card_png_e_petcode():
    pet = {"nome": "Bia", "genes": genetica.aleatorio(4, "SOL"), "nivel": 3, "xp": 99, "estagio": "bebe"}
    s = cartao.de_petcode(genetica.exportar(pet))
    img = cartao.png(s)
    assert img.size == (cartao.W * cartao.ESC, cartao.H * cartao.ESC)
    with pytest.raises(ValueError):
        cartao.de_petcode("lixo")


def test_tool_profile_card(tmp_path):
    st = tmp_path / "stats.json"
    st.write_text(json.dumps(cartao.exportar_stats(STATUS)))
    out = tmp_path / "card.svg"
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "profile_card.py"), "--stats", str(st), "-o", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.read_text().startswith("<svg")


def test_ia_desligada_por_padrao_responde_enlatado():
    assert not ai.ligado({})
    assert ai.perguntar("o que é halving?", {}) in ai.ENLATADAS
    assert "NUNCA" in ai.perguntar("qual minha seed?", {})
    assert "conselho" in ai.perguntar("devo comprar doge?", {})


def test_ia_byo_manda_so_o_minimo(monkeypatch):
    visto = {}

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "HODL, fren."}}]}

    def post(url, json=None, headers=None, timeout=None):
        visto.update(url=url, corpo=json, headers=headers)
        return R()
    monkeypatch.setattr(ai.requests, "post", post)
    cfg = {"ai_url": "https://api.exemplo.com/v1", "ai_key": "sk-teste", "ai_modelo": "m"}
    assert ai.perguntar("e aí?", cfg, {"moeda": "BTC", "humor": "moon", "nivel": 3}) == "HODL, fren."
    assert visto["url"] == "https://api.exemplo.com/v1/chat/completions"
    assert visto["headers"]["Authorization"] == "Bearer sk-teste" and visto["corpo"]["model"] == "m"
    assert "bc1" not in str(visto["corpo"])


def test_ia_erro_de_rede_vira_piada(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("x")
    monkeypatch.setattr(ai.requests, "post", boom)
    assert "fora do ar" in ai.perguntar("oi", {"ai_url": "https://x"})


@pytest.mark.skipif(not shutil.which("node"), reason="precisa de node")
def test_extensao_vscode_smoke():
    pkg = json.loads((RAIZ / "vscode" / "package.json").read_text())
    assert pkg["main"] == "./extension.js" and pkg["version"] == __import__("satoshipet").__version__
    for m in ("BTC", "ETH", "SOL", "DOGE", "PEPE"):
        assert (RAIZ / "vscode" / "media" / f"{m}_padrao.png").exists()
    r = subprocess.run(["node", str(RAIZ / "vscode" / "test" / "smoke.js")], capture_output=True, text=True)
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr
