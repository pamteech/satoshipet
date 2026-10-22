"""v1.4 fase 1: genes, código do pet, cruzamento, batalha e hardcore (lógica pura)."""
import time

from PIL import Image

from tamagoshi_cripto import batalha, genetica, hardcore, recursos
from tamagoshi_cripto.pixel import P, rgb

PALETA = {rgb(v) for v in P.values()}


def _frame(moeda="BTC"):
    return Image.open(recursos.ASSETS / "sprites" / f"{moeda}_padrao.png").convert("RGBA").crop((0, 0, 48, 48))


def test_genes_aleatorios_validos_e_deterministicos():
    a, b = genetica.aleatorio(7), genetica.aleatorio(7)
    assert a == b
    for k, ops in genetica.GENES.items():
        assert a[k] in ops
    assert genetica.raridade({k: "original" for k in genetica.GENES})[0] == "comum"
    lend = {"paleta": "invertido", "olhos": "laser", "acessorio": "aureola", "padrao": "brilho"}
    assert genetica.raridade(lend)[0] == "lendário"


def test_aplicar_genes_so_usa_cores_da_paleta():
    for semente in range(25):
        g = genetica.aleatorio(semente)
        for m in ("BTC", "ETH", "SOL", "DOGE", "PEPE"):
            fr = genetica.aplicar(_frame(m), g)
            cores = {px[:3] for px in fr.getdata() if px[3]}
            assert cores <= PALETA, (m, g)
    assert genetica.aplicar(_frame(), {}).tobytes() == _frame().tobytes()


def test_fantasma_tem_silhueta():
    f = genetica.fantasma(_frame())
    assert f.getbbox() and {px[:3] for px in f.getdata() if px[3]} <= PALETA


def test_codigo_do_pet_ida_e_volta_e_rejeita_lixo():
    pet = {"nome": "Bia", "genes": genetica.aleatorio(3, "SOL"), "nivel": 9, "xp": 1200, "estagio": "adulto"}
    cod = genetica.exportar(pet)
    assert cod.startswith("TAMA1-") and len(cod) < 260
    volta, erro = genetica.importar(cod)
    assert erro is None and volta["nome"] == "Bia" and volta["genes"]["paleta"] == pet["genes"]["paleta"]
    assert genetica.importar(cod[:-1] + ("0" if cod[-1] != "0" else "1"))[1]  # checksum
    assert genetica.importar("oi")[1]
    assert genetica.importar("TAMA1-xxx-yyy")[1]


def test_cruzar_herda_dos_pais_e_muta():
    a = {k: next(iter(v)) for k, v in genetica.GENES.items()}
    b = {k: list(v)[-1] for k, v in genetica.GENES.items()}
    filho, mutou = genetica.cruzar(dict(a, geracao=1), dict(b, geracao=3), semente=1, taxa_mutacao=0)
    assert not mutou and filho["geracao"] == 4
    for k in genetica.GENES:
        assert filho[k] in (a[k], b[k])
    _, mutou = genetica.cruzar(a, b, semente=1, taxa_mutacao=1)
    assert len(mutou) == len(genetica.GENES)


def test_batalha_deterministica_e_termina():
    eu = {"nome": "Eu", "nivel": 10, "estagio": "adulto", "genes": genetica.aleatorio(1)}
    r1 = batalha.simular(eu, batalha.rival_ia(10, 2), semente=5)
    r2 = batalha.simular(eu, batalha.rival_ia(10, 2), semente=5)
    assert [l["texto"] for l in r1["log"]] == [l["texto"] for l in r2["log"]]
    assert r1["vencedor"] in ("a", "b", "empate") and r1["log"]


def test_variacao_24h_deixa_mais_forte():
    pet = {"nome": "x", "nivel": 5, "estagio": "adulto", "genes": genetica.aleatorio(2)}
    assert batalha.stats(pet, 8)["atk"] > batalha.stats(pet, -8)["atk"]
    assert batalha.stats(pet, 999)["atk"] == batalha.stats(pet, 10)["atk"]  # limitado


def test_whale_vence_ovo_na_maioria():
    forte = {"nome": "W", "nivel": 30, "estagio": "whale", "genes": genetica.aleatorio(1)}
    fraco = {"nome": "O", "nivel": 1, "estagio": "bebe", "genes": genetica.aleatorio(2)}
    vitorias = sum(batalha.simular(forte, fraco, semente=s)["vencedor"] == "a" for s in range(20))
    assert vitorias >= 18


def test_hardcore_so_mata_com_abandono_prolongado():
    agora = 1_000_000.0
    cfg = {"hardcore": False}
    assert not hardcore.checar(cfg, 0, agora)  # desligado: imortal
    cfg = {"hardcore": True, "ultima_interacao": agora - 5 * 3600}
    assert not hardcore.checar(cfg, 0, agora)  # começou a contar agora
    assert not hardcore.checar(cfg, 0, agora + 29 * 60)
    assert hardcore.checar(cfg, 0, agora + 31 * 60)
    cfg = {"hardcore": True, "ultima_interacao": agora}  # zerou mas tem gente cuidando
    hardcore.checar(cfg, 0, agora)
    assert not hardcore.checar(cfg, 0, agora + 3600)
    cfg = {"hardcore": True, "ultima_interacao": agora - 9e9, "zero_desde": agora - 9e9}
    assert not hardcore.checar(cfg, 3, agora) and "zero_desde" not in cfg  # vida voltou: zera relógio


def test_lapide_e_enterro():
    cfg = {"hardcore": True, "nasceu_em": time.time() - 86400 * 3}
    st = {"nivel": 4, "xp": 300, "estagio": "BEBE", "moeda": "BTC", "btc": {"comidos": 7}, "crashes": 1}
    reg = hardcore.lapide(cfg, "Zé", st, semente=1)
    assert reg["epitafio"] in hardcore.EPITAFIOS and reg["dias"] >= 2.9 and reg["blocos"] == 7
    hardcore.enterrar(cfg, reg)
    assert cfg["fantasma"] and cfg["cemiterio"][-1]["nome"] == "Zé"
