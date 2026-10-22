"""Fuzz dos parsers que recebem texto de fora: código de pet, códigos da loja, RSS, Twitch, endereços."""
import base64
import hashlib
import json
import random
import string
import zlib

import pytest

from satoshipet import genetica, loja, multichain, noticias, onchain, twitch

ALFABETO = string.printable + "áéíóúãõç€🚀\x00\u202e"


def _forjar(obj):
    """Código TAMA1 com checksum VÁLIDO para um JSON qualquer (o checksum não é segredo)."""
    dados = zlib.compress(json.dumps(obj).encode())
    return genetica.PREFIXO + base64.urlsafe_b64encode(dados).decode().rstrip("=") + "-" + \
        hashlib.sha256(dados).hexdigest()[:6]


def _checar_pet(r):
    pet, erro = r
    assert (pet is None) != (erro is None)
    if pet:
        assert isinstance(pet["nome"], str) and len(pet["nome"]) <= 12
        assert isinstance(pet["nivel"], int) and 1 <= pet["nivel"] <= 99
        assert isinstance(pet["xp"], int) and pet["xp"] >= 0
        for k, ops in genetica.GENES.items():
            assert pet["genes"][k] in ops


@pytest.mark.parametrize("semente", range(40))
def test_fuzz_petcode_lixo(semente):
    rnd = random.Random(semente)
    valido = genetica.exportar({"nome": "Bia", "genes": genetica.aleatorio(semente), "nivel": 5, "xp": 10,
                                "estagio": "adulto"})
    for _ in range(50):
        c = list(valido)
        for _ in range(rnd.randint(1, 5)):
            c[rnd.randrange(len(c))] = rnd.choice(ALFABETO)
        _checar_pet(genetica.importar("".join(c)))
        _checar_pet(genetica.importar("".join(rnd.choice(ALFABETO) for _ in range(rnd.randint(0, 300)))))
        _checar_pet(genetica.importar(genetica.PREFIXO + "".join(rnd.choice(ALFABETO) for _ in range(80))))


g_ok = {k: next(iter(v)) for k, v in genetica.GENES.items()} | {"moeda": "BTC"}
FORJADOS = [
    [], "texto", 42, None, {"g": []}, {"g": "x"}, {"g": g_ok, "lv": "abc"}, {"g": g_ok, "lv": 1e300},
    {"g": g_ok, "lv": -5, "xp": -1}, {"g": g_ok, "n": 123}, {"g": g_ok, "n": ["a"]}, {"g": g_ok, "xp": "1e9"},
    {"g": g_ok, "e": ["ovo"]}, {"g": dict(g_ok, moeda=["BTC"])}, {"g": dict(g_ok, paleta={"x": 1})},
    {"g": g_ok, "lv": float("nan")} if False else {"g": g_ok, "lv": None}, {"g": g_ok, "n": "x" * 5000},
    {"g": g_ok, "lv": True}, {"g": dict(g_ok, geracao="99999999999999999999"), "lv": 3},
]


@pytest.mark.parametrize("obj", FORJADOS, ids=range(len(FORJADOS)))
def test_petcode_forjado_com_checksum_valido(obj):
    _checar_pet(genetica.importar(_forjar(obj)))


def test_petcode_bomba_de_zlib():
    dados = zlib.compress(b'{"g":' + b" " * 10_000_000 + b"}", 9)
    cod = genetica.PREFIXO + base64.urlsafe_b64encode(dados).decode().rstrip("=") + "-" + \
        hashlib.sha256(dados).hexdigest()[:6]
    _checar_pet(genetica.importar(cod))


def test_petcode_importado_cruza_e_luta():
    from satoshipet import batalha
    pet, erro = genetica.importar(_forjar({"g": dict(g_ok, geracao="lixo", id=["x"]), "lv": 3, "e": "whale"}))
    assert erro is None
    filho, _ = genetica.cruzar(genetica.aleatorio(1), pet["genes"], semente=1)
    assert isinstance(filho["geracao"], int)
    batalha.simular({"nome": "a", "nivel": 3, "estagio": "adulto", "genes": genetica.aleatorio(1)}, pet, semente=1)


@pytest.mark.parametrize("semente", range(10))
def test_fuzz_codigos_loja_enderecos_twitch(semente):
    rnd = random.Random(semente)
    for _ in range(300):
        s = "".join(rnd.choice(ALFABETO) for _ in range(rnd.randint(0, 120)))
        assert loja.validar_codigo(s, "a@b.c") is None
        assert loja.validar_codigo("SKIN-" + s) is None
        for rede in ("eth", "sol"):
            ok, msg = multichain.validar(rede, s)
            assert isinstance(msg, str)
        onchain.validar_endereco(s)
        assert twitch.parse_linha(s, {"!pet"}) in (None,) or twitch.parse_linha(s, {"!pet"})[1] == "!pet"
        twitch.canal_valido(s)


@pytest.mark.parametrize("xml", [b"", b"<rss>", b"<rss><channel><item></item></channel></rss>",
                                 b"<?xml version='1.0'?><!DOCTYPE x [<!ENTITY a 'aaaaaaaaaa'>]><rss>&a;</rss>",
                                 b"<rss><channel><item><title>x</title><link>javascript:alert(1)</link></item></channel></rss>",
                                 "<rss><channel><item><title>\u202eevil</title><link>https://ok</link></item></channel></rss>".encode()])
def test_rss_malicioso(xml):
    try:
        itens = noticias.parse(xml, "x")
    except Exception as e:  # XML quebrado pode falhar, mas só com ParseError (buscar() já trata)
        assert type(e).__name__ == "ParseError", e
        return
    for i in itens:
        assert i["link"].startswith("https://") and all(ord(c) < 256 for c in i["titulo"])
