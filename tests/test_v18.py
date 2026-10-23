"""v1.8: aniversários, festa de ATH e roupinhas de época (lógica pura + arte sem GUI)."""
import datetime as dt
from pathlib import Path

import pytest
from PIL import Image

from satoshipet import cli, config, conquistas, efeitos, i18n, juice, marcos, roupas, sprites

D = marcos.DIA
T0 = 1_700_000_000


# ---------- aniversários ----------
def test_marco_pendente_e_sem_spam():
    assert marcos.pendente(T0, [], T0 + 6 * D) is None
    m = marcos.pendente(T0, [], T0 + 7 * D)
    assert m["dias"] == 7 and m["fx"] == "confete" and m["conquista"] == "aniv_semana"
    m = marcos.pendente(T0, [], T0 + 120 * D)  # atrasado: só o maior, os outros entram como feitos
    assert m["dias"] == 100 and set(m["alcancados"]) == {7, 30, 100}
    assert marcos.pendente(T0, m["alcancados"], T0 + 120 * D) is None
    assert marcos.pendente(T0, [7, 30, 100], T0 + 182 * D)["nome"] == "6 meses"


def test_marcos_anuais_infinitos():
    dias = [m[0] for m in marcos.lista(365 * 5)]
    assert {365, 730, 1095, 1460, 1825} <= set(dias)
    assert marcos.pendente(T0, [], T0 + 3 * 365 * D)["nome"] == "3 anos"
    assert marcos.pendente(0, [], T0) is None


def test_migracao_v18_nascimento_pelo_primeiro_registro():
    cfg = {"versao_config": 4, "nasceu_em": 0, "progresso": {"desbloqueadas": {"a": T0 + 50, "b": T0}}}
    out = config.migrar(cfg)
    assert out["nasceu_em"] == T0 and out["marcos"] == [] and out["versao_config"] == config.VERSAO_CONFIG
    novo = config.migrar({"versao_config": 4, "nasceu_em": 0})
    assert novo["nasceu_em"] > T0
    assert config.migrar({"versao_config": 4, "nasceu_em": 123})["nasceu_em"] == 123


def test_ath_uma_vez_por_ath_novo():
    cfg = {}
    assert marcos.checar_ath(cfg, 100_000, 90_000, T0) is None  # 1ª vez só aprende
    assert cfg["ath_btc"] == 100_000
    assert marcos.checar_ath(cfg, 100_000, 99_000, T0 + 10) is None
    assert marcos.checar_ath(cfg, 100_000, 101_000, T0 + 20) == 101_000
    assert marcos.checar_ath(cfg, 101_000, 102_000, T0 + 30) is None  # rali: sem festa repetida no mesmo dia
    assert cfg["ath_btc"] == 102_000
    assert marcos.checar_ath(cfg, 102_000, 102_000, T0 + 2 * D) is None  # mesmo ATH: nada
    assert marcos.checar_ath(cfg, 110_000, None, T0 + 2 * D) == 110_000
    assert marcos.checar_ath({}, None, None) is None


def test_conquistas_de_aniversario_tem_medalha():
    for cid in ("aniv_semana", "aniv_mes", "aniv_100d", "aniv_ano", "ath_festa"):
        assert cid in conquistas.LISTA and cid in conquistas.BADGES
        cor, arte = conquistas.BADGES[cid]
        assert len(arte) == 8 and all(len(r) == 8 and set(r) <= set(".12") for r in arte)


# ---------- festa (efeito) ----------
class CV:
    def __init__(self):
        self.n = 0

    def create_rectangle(self, *a, **k):
        self.n += 1


@pytest.mark.parametrize("tipo", efeitos.TIPOS_FESTA)
def test_festa_desenha_e_termina(tipo):
    f = efeitos.Festa(tipo, "1 ANO!", semente=1)
    textos = []
    while f.viva:
        cv = CV()
        f.desenhar(cv, 260, 300, 130, 120, 72, 3, lambda *a, **k: textos.append(a[2]))
        f.tick()
    assert f.t == efeitos.Festa.DURACAO and "1 ANO!" in textos


def test_festa_reduzir_movimento_e_economia():
    leve = efeitos.Festa("confete", leve=True, semente=3)
    a = leve.confete(200, 200)
    leve.tick()
    leve.tick()
    assert leve.confete(200, 200) == a  # parado
    eco = efeitos.Festa("fogos", economia=True)
    assert eco.duracao == efeitos.Festa.DURACAO // 2 and len(eco.pecas) < len(efeitos.Festa().pecas)


# ---------- roupinhas ----------
@pytest.mark.parametrize("dia,esperado", [
    ((2026, 10, 31), "whitepaper"), ((2026, 10, 28), "halloween"), ((2026, 11, 2), "halloween"),
    ((2026, 10, 20), None), ((2026, 12, 10), "natal"), ((2026, 12, 31), "ano_novo"), ((2027, 1, 1), "ano_novo"),
    ((2027, 1, 3), "genesis"), ((2027, 5, 22), "pizza"), ((2027, 2, 9), "carnaval"), ((2027, 2, 6), "carnaval"),
    ((2027, 2, 10), "carnaval"), ((2027, 2, 11), None), ((2027, 7, 1), None),
])
def test_roupa_do_dia(dia, esperado):
    assert roupas.roupa_do_dia(dt.date(*dia)) == esperado


def test_halving_vence_tudo_e_data_de_debug(monkeypatch):
    assert roupas.roupa_do_dia(dt.date(2026, 12, 25), altura=1_050_000) == "halving"
    monkeypatch.setenv("SATOSHIPET_DATE", "2027-05-22")
    assert roupas.hoje() == dt.date(2027, 5, 22)
    monkeypatch.setenv("SATOSHIPET_DATE", "lixo")
    assert roupas.hoje() == dt.date.today()


def test_toda_roupa_tem_arte_e_cores():
    for rid in roupas.NOMES:
        assert rid in juice.ARTES and rid in juice.CORES_CHAPEU
        cores = juice.CORES_CHAPEU[rid]
        assert all(set(linha) <= set(cores) | {"."} for linha in juice.ARTES[rid]), rid


FOLHAS = Path(sprites.__file__).parent / "assets" / "sprites"


@pytest.mark.parametrize("estagio", sprites.ESTAGIOS)
def test_roupas_em_todos_os_estagios(estagio):
    folha = Image.open(FOLHAS / sprites.nome_folha("BTC", "padrao", estagio)).convert("RGBA")
    fr = folha.crop((0, 0, 48, 48))
    for rid in roupas.NOMES:
        out = juice.aplicar_chapeu(fr, rid)
        diff = sum(1 for a, b in zip(fr.getdata(), out.getdata()) if a != b)
        assert diff >= 20, (estagio, rid, diff)
        assert out.getchannel("A").crop((0, 30, 48, 48)) == fr.getchannel("A").crop((0, 30, 48, 48))  # não cobre o corpo


def test_cli_outfit(capsys):
    assert cli.main(["--outfit", "2027-01-03"]) == 0
    assert "genesis" in capsys.readouterr().out
    assert cli.main(["--outfit", "2027-07-01"]) == 0
    assert "sem roupinha" in capsys.readouterr().out
    assert cli.main(["--outfit", "31/10"]) == 2


def test_i18n_festa():
    assert i18n.EN["NOVO ATH!"] == "NEW ATH!" and i18n.EN["1 ANO!"] == "1 YEAR!"
    assert i18n.EN["Roupinhas de época"] == "Seasonal outfits"


def test_nada_de_nome_antigo_nas_novidades():
    raiz = Path(roupas.__file__).parent
    for nome in ("roupas.py", "marcos.py"):
        txt = (raiz / nome).read_text(encoding="utf-8").lower()
        assert "tamagoshi" not in txt and "tamagotchi" not in txt


@pytest.fixture
def idioma():
    yield i18n.definir
    i18n.definir("pt")


def test_frases_de_marco_em_en_e_pt(idioma):
    idioma("pt")
    m = marcos.pendente(T0, [], T0 + 30 * D)
    assert m["frase"] == "parabéns pra mim! 1 mês de vida" and m["titulo"] == "1 MÊS!"
    idioma("en")
    m = marcos.pendente(T0, [], T0 + 30 * D)
    assert m["frase"] == "happy birthday to me! 1 month old" and m["titulo"] == "1 MONTH!"
    assert marcos.pendente(T0, [], T0 + 7 * D)["frase"] == "1 week of HODL together!"
    assert marcos.pendente(T0, [], T0 + 3 * 365 * D)["frase"] == "3 years! not even mt. gox took me down"


def test_ath_formatado_por_idioma(idioma):
    idioma("pt")
    assert marcos.texto_ath(126500.4) == "BTC bateu US$ 126.500. WAGMI!"
    assert marcos.dinheiro_usd(1_234_567) == "US$ 1.234.567"
    idioma("en")
    assert marcos.texto_ath(126500.4) == "BTC hit $126,500. WAGMI!"
    assert marcos.dinheiro_usd(999) == "$999"
