"""v1.4 fase 4: loja de skins, códigos de pacote, pacotes de marca e chat da Twitch."""
import datetime as dt
import json
import shutil

from tamagoshi_cripto import loja, recursos, twitch


def test_catalogo_tem_os_4_pacotes_validos():
    c = loja.catalogo()
    assert {"halloween", "natal", "neon_nights", "cafe_satoshi"} <= set(c)
    assert c["cafe_satoshi"]["disclosure"] == "patrocinado"
    assert sum(c["neon_nights"]["revenue_share"].values()) == 100


def test_codigos_de_pacote():
    cod = loja.gerar_codigo("neon_nights", "Fulano@Ex.com")
    assert loja.validar_codigo(cod, "fulano@ex.com") == "neon_nights"
    assert loja.validar_codigo(cod, "outro@ex.com") is None          # preso ao e-mail
    promo = loja.gerar_codigo("neon_nights", "*")
    assert loja.validar_codigo(promo, "") == "neon_nights"            # promocional vale pra todos
    assert loja.validar_codigo(promo[:-1] + "0", "") in (None, "neon_nights") and loja.validar_codigo("lixo") is None
    assert loja.validar_codigo("SKIN-NEON_NIGHTS-000000000000") is None


def test_destrave_por_tier():
    c = loja.catalogo()
    assert loja.destravado(c["cafe_satoshi"], False, [])
    assert not loja.destravado(c["halloween"], False, []) and loja.destravado(c["halloween"], True, [])
    assert not loja.destravado(c["neon_nights"], True, []) and loja.destravado(c["neon_nights"], False, ["neon_nights"])


def test_temporada_e_vigencia():
    c = loja.catalogo()
    assert loja.em_temporada(c["halloween"], dt.date(2026, 10, 22))
    assert not loja.em_temporada(c["halloween"], dt.date(2026, 7, 1))
    assert loja.em_temporada(c["natal"], dt.date(2027, 1, 3))         # vira o ano
    assert not loja.em_temporada(c["natal"], dt.date(2027, 2, 3))
    assert loja.vigente({"vigencia": {"de": "2026-01-01", "ate": "2026-12-31"}}, dt.date(2026, 5, 5))
    assert not loja.vigente({"vigencia": {"de": "2026-01-01", "ate": "2026-01-31"}}, dt.date(2026, 5, 5))


def test_pacote_de_marca_sem_disclosure_e_recusado(tmp_path):
    src = recursos.ASSETS / "loja" / "cafe_satoshi"
    p = tmp_path / "marca_x"
    shutil.copytree(src, p)
    meta = json.loads((p / "pack.json").read_text())
    meta["id"] = "marca_x"
    for falta in ("disclosure", "autorizacao", "vigencia"):
        m = dict(meta)
        m.pop(falta)
        (p / "pack.json").write_text(json.dumps(m))
        assert loja.validar_pack(p)[1], falta
    (p / "pack.json").write_text(json.dumps(meta))
    assert loja.validar_pack(p)[1] is None


def test_twitch_parse_e_canal():
    l = "@badge-info=;color=#FF0000 :fulano!fulano@fulano.tmi.twitch.tv PRIVMSG #canal_x :!moon bora"
    assert twitch.parse_linha(l, {"!moon"}) == ("fulano", "!moon")
    assert twitch.parse_linha(":a!a@a PRIVMSG #c :oi gente", {"!moon"}) is None
    assert twitch.parse_linha("PING :tmi.twitch.tv", {"!moon"}) is None
    assert twitch.canal_valido("#Meu_Canal") and not twitch.canal_valido("x y") and not twitch.canal_valido("ab")
