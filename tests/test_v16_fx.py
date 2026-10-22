"""v1.6: transições, evolução, idle, dicas e modo economia (lógica pura + integração headless)."""
import random
from pathlib import Path

from tamagoshi_cripto import efeitos, energia, i18n


def test_transicoes_revelam_ate_o_fim():
    for tipo in efeitos.TIPOS:
        t = efeitos.Transicao(tipo, duracao=6, bloco=12)
        n0 = len(t.cobertos(240, 360))
        assert n0 >= (240 // 12) * (360 // 12) * 0.9, tipo  # começa (quase) tudo coberto
        def area(t=t):
            return sum(s * s for *_, s in t.cobertos(240, 360))
        vistos = [area()]
        while t.viva:
            t.tick()
            vistos.append(area())
        assert vistos[-1] == 0 and vistos == sorted(vistos, reverse=True), tipo  # monotônico e termina limpo
        assert n0 < 700  # barato: poucos retângulos por frame


def test_evolucao_alterna_acelera_e_termina():
    ev = efeitos.Evolucao("velha", "nova", "WHALE")
    seq = []
    while ev.viva:
        seq.append((ev.fase(), ev.imagem("cor")))
        ev.tick()
    fases = [f for f, _ in seq]
    assert fases[0] == "pisca" and "flash" in fases and fases[-1] == "revela"
    piscadas = [i for f, i in seq if f == "pisca"]
    assert "velha" in piscadas and "nova" in piscadas
    assert seq[-1][1] == "cor"  # termina mostrando o sprite colorido novo
    trocas = [i for i in range(1, len(piscadas)) if piscadas[i] != piscadas[i - 1]]
    assert trocas[-1] - trocas[-2] <= trocas[1] - trocas[0]  # acelera


def test_idle_pisca_e_olha_pro_mouse():
    idle = efeitos.Idle(random.Random(1))
    fechou = False
    for _ in range(120):
        idle.tick(0, False)
        fechou |= idle.olhos_fechados()
    assert fechou
    idle.fidget = idle.bocejo = 0
    assert idle.deslocamento(100, 100, 400, 100, 3) == (6, 0)    # olha pra direita (2 px grandes)
    assert idle.deslocamento(100, 100, None, None, 3) == (0, 0)
    idle2 = efeitos.Idle(random.Random(2))
    for _ in range(3000):
        idle2.tick(9999, False)
        if idle2.bocejo:
            break
    assert idle2.bocejo  # parado muito tempo: boceja


def test_dicas_tem_ingles_e_zona():
    i18n.definir("en")
    try:
        for txt in efeitos.DICAS.values():
            assert i18n.t(txt) != txt, txt
    finally:
        i18n.definir("pt")
    assert efeitos.zona(5, 5, {"a": (0, 0, 10, 10)}) == "a" and efeitos.zona(50, 5, {"a": (0, 0, 10, 10)}) is None


def test_energia_modos_e_linux(tmp_path: Path):
    assert energia.modo(True, False, 10, False) == "normal"
    assert energia.modo(True, True, 10, False) == "bateria"
    assert energia.modo(True, False, None, True) == "pausa"
    assert energia.modo(True, True, energia.AUSENTE_S + 1, False) == "pausa"
    assert energia.modo(False, True, 99999, True) == "normal"  # desligado = nunca economiza
    ac = tmp_path / "AC"
    ac.mkdir()
    (ac / "type").write_text("Mains\n")
    (ac / "online").write_text("0\n")
    assert energia.na_bateria("linux", tmp_path)
    (ac / "online").write_text("1\n")
    assert not energia.na_bateria("linux", tmp_path)
    assert not energia.na_bateria("linux", tmp_path / "nada")


def test_energia_mac_parse(monkeypatch):
    monkeypatch.setattr(energia, "_rodar", lambda cmd, timeout=3: "Now drawing from 'Battery Power'\n"
                        if cmd[0] == "pmset" else '    |   "HIDIdleTime" = 5000000000\n')
    assert energia.na_bateria("darwin") and energia.segundos_ocioso("darwin") == 5.0
