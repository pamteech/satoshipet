"""Testes da lógica (sem GUI). Rode: pytest  (OFFLINE=1 pula os testes de rede)."""
import json
import os
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from satoshipet import arts, cli, config, conquistas, license, logic, lore, plugins, recursos, sistema, sons
from satoshipet import sprites as S

OFFLINE = bool(os.environ.get("OFFLINE"))


def test_estados():
    f = logic.estado_do_bicho
    assert f(0) == f(2) == f(-2) == "garimpando"
    assert f(2.01) == "moon" and f(-2.01) == "rekt" and f(4, 5, -5) == "garimpando"


def test_licenca():
    k = license.gerar_chave("Cliente@Email.com ")
    assert license.validar("cliente@email.com", k.lower())
    assert not license.validar("outro@email.com", k)
    assert not license.validar("", "")


def test_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "c.json")
    c = config.carregar(); c["moeda"] = "ETH"; config.salvar(c)
    assert config.carregar()["moeda"] == "ETH"
    config.CONFIG_PATH.write_text("{lixo")
    assert config.carregar()["moeda"] == "BTC"


@pytest.mark.parametrize("moeda", list(config.MOEDAS))
def test_folhas_de_sprite(moeda):
    from PIL import Image
    for sk in S.SKINS:
        im = Image.open(recursos.sheet_path(moeda, sk))
        assert im.size == (192, 192)
        for j in range(4):
            frames = [im.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48)) for f in range(4)]
            for fr in frames:
                assert fr.getbbox(), f"{moeda}/{sk} linha {j} frame vazio"
                hist = fr.getchannel("A").histogram()
                assert hist[0] > 48 * 48 * 0.3  # fundo majoritariamente transparente
                # só alpha 0 ou 255 (Tk -transparentcolor não lida com meio-termo)
                assert sum(hist[1:255]) == 0
            assert len({f.tobytes() for f in frames}) > 1, f"{moeda}/{sk} linha {j} não anima"


def test_paleta_padrao_limitada():
    """Skin padrão usa só a paleta Sweetie 16 (efeitos inclusos)."""
    from PIL import Image

    from satoshipet.pixel import P, rgb
    pal = {rgb(c) for c in P.values()}
    for m in config.MOEDAS:
        im = Image.open(recursos.sheet_path(m, "padrao")).convert("RGBA")
        cores = {c[1][:3] for c in im.getcolors(1 << 16) if c[1][3]}
        assert cores <= pal, f"{m}: cores fora da paleta {cores - pal}"


def test_folhas_commitadas_batem_com_o_gerador():
    """Se falhar: rode `python -m satoshipet.sprites` e commite as folhas."""
    from PIL import Image
    for m in ("BTC", "PEPE"):
        for sk in ("padrao", "cyberpunk"):
            gerado = S.sheet(m, sk)
            salvo = Image.open(recursos.sheet_path(m, sk)).convert("RGBA")
            assert gerado.tobytes() == salvo.tobytes(), f"{m}_{sk}.png desatualizada"


def test_sprite_determinista():
    a = S.desenhar("BTC", "padrao", "moon", 1).tobytes()
    assert a == S.desenhar("BTC", "padrao", "moon", 1).tobytes()


def test_frases():
    for e in arts.ESTADOS:
        for m in config.MOEDAS:
            assert arts.frase(e, m)
        assert arts.frase(e, "BTC", {e: ["frase do plugin"]})
        assert arts.reacao(e)


def test_alerta_e_formato():
    assert logic.checar_alerta(10, {"acima": 9})
    assert logic.checar_alerta(10, {"acima": 11, "abaixo": 5}) is None
    assert logic.formatar_preco(65000) == "$65,000.00"
    assert logic.formatar_preco(0.00000448).startswith("$0.0000044")


def test_conquistas():
    c = conquistas.Conquistas()
    assert c.tick("moon", 60) == ["primeiro_moon"]
    for _ in range(3):
        c.tick("rekt", 10); c.tick("garimpando", 10)
    assert "sobreviveu_3" in c.d["desbloqueadas"] and c.d["crashes"] == 3
    c.tick("garimpando", 86400)
    assert "hodl_24h" in c.d["desbloqueadas"]
    assert c.tick("garimpando", 10) == []
    v = c.vida; c.tick("rekt", 600); assert c.vida < v
    c.tick("rekt", 999999); assert c.vida == 0 and "quase_morreu" in c.d["desbloqueadas"]
    for _ in range(10):
        c.carinho()
    assert "carinho_10" in c.d["desbloqueadas"]
    assert c.especial("konami") == ["konami"] and c.especial("konami") == []
    assert "[X] Pet Lover" in c.resumo()
    # bônus do Fear & Greed
    a, b = conquistas.Conquistas(), conquistas.Conquistas()
    a.tick("garimpando", 60, 0.1); b.tick("garimpando", 60, 0.0)
    assert a.vida > b.vida


def test_sons():
    arqs = sons.preparar()
    for nome in sons.MELODIAS:
        with wave.open(str(arqs[nome])) as w:
            assert w.getnframes() > 1000
    assert not sons.Som(mudo=True).tocar("clique")


def test_historico():
    h = logic.Historico(maximo=100)
    for i in range(250):
        h.adicionar("BTC", float(i), t=i)
    assert len(h.dados["BTC"]) == 100
    s = h.serie("BTC", 10)
    assert len(s) == 10 and s[0] < s[-1]


def test_lore_halving_e_konami():
    assert lore.halving(840_000) == (210_000, 210_000 * 10 / 1440, 5)
    assert lore.halving(1_049_999)[0] == 1
    k = lore.Konami()
    seq = ["Up", "Up", "Down", "Down", "Left", "Right", "Left", "Right", "B", "A"]
    assert [k.alimentar(t) for t in seq][-1] is True
    assert not any(k.alimentar(t) for t in ["Up", "Down", "a"])
    assert lore.ajuste_vida_fng(80) > 0 > lore.ajuste_vida_fng(10)
    assert lore.ajuste_vida_fng(None) == 0


def test_plugins(tmp_path):
    achadas = plugins.descobrir()
    assert "plugin:slime" in achadas  # exemplo embutido
    ruim = tmp_path / "ruim"; ruim.mkdir()
    (ruim / "skin.json").write_text(json.dumps({"id": "x", "nome": "X", "autor": "eu"}))
    (ruim / "sheet.png").write_bytes(b"nao sou png")
    assert plugins.validar(ruim)[1] == "sheet.png não é PNG"
    boa = tmp_path / "boa"; boa.mkdir()
    import shutil
    shutil.copy(achadas["plugin:slime"]["_folha"], boa / "sheet.png")
    (boa / "skin.json").write_text(json.dumps({"id": "boa", "nome": "Boa", "autor": "eu"}))
    assert "plugin:boa" in plugins.descobrir(tmp_path)


def test_fonte_bitmap():
    dados = json.loads((recursos.ASSETS / "fonts" / "pixel8.json").read_text(encoding="utf-8"))
    for ch in "ABCxyz0123456789!?$%ãéçÕ":
        assert ch in dados["glifos"] and len(dados["glifos"][ch]) == 8


def test_sistema_degrada():
    if sys.platform.startswith("linux"):
        assert not sistema.tray_disponivel()
        assert not sistema.definir_autostart(True)
        assert not sistema.autostart_ativo()
    plist = sistema.plist_mac()
    assert plist["RunAtLoad"] and plist["ProgramArguments"]


def test_cli_ajuda_e_lista(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert cli.main(["--list-skins"]) == 0
    assert "slime" in capsys.readouterr().out


def test_tui_renderiza(monkeypatch, capsys):
    from satoshipet import tui
    monkeypatch.setattr(logic, "buscar_precos", lambda s, timeout=10: {m: 1.0 for m in s})
    assert tui.rodar({"moeda": "PEPE"}, frames=2) == 0
    out = capsys.readouterr().out
    assert "▀" in out and "Sapo Degen" in out


@pytest.mark.skipif(OFFLINE, reason="offline")
def test_api_ao_vivo():
    p = logic.buscar_precos(list(config.MOEDAS))
    assert "BTC" in p and p["BTC"] > 0
