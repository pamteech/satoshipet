"""v1.5 - i18n e kit de UI (sem display: só a lógica)."""
from tamagoshi_cripto import i18n, ui


def test_i18n_detecta_e_traduz(monkeypatch):
    for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("LANG", "pt_BR.UTF-8")
    assert i18n.detectar() == "pt" and i18n.definir("auto") == "pt"
    assert i18n.t("AJUSTES") == "AJUSTES"
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n.definir("auto") == "en"
    assert i18n.t("AJUSTES") == "SETTINGS"
    assert i18n.t("recorde: 3V 1D") == "record: 3V 1D"   # prefixo + número
    assert i18n.t("palavra sem tradução") == "palavra sem tradução"  # fallback: pt, nunca crash
    assert i18n.t("") == ""
    assert i18n.definir("pt") == "pt" and i18n.atual() == "pt"
    assert i18n.definir("xx") == "pt"


def test_i18n_rotulos_cabem_na_tela():
    """Abas têm ~52px = 6 caracteres; rótulos de ajuste até 18 (o valor fica do lado)."""
    from tamagoshi_cripto.ajustes import Ajustes
    for aba in Ajustes.ABAS:
        assert len(aba) <= 6 and len(i18n.EN[aba]) <= 6, aba
    for pt, en in i18n.EN.items():
        assert "\n" in pt or len(en) <= max(len(pt) + 12, 40), (pt, en)


def test_ui_cores():
    assert ui._clarear("#808080") == "#acacac" and ui._escurecer("#808080") == "#535353"
    assert ui._clarear("#ffffff") == "#ffffff"


def test_idioma_mac_sem_lang(monkeypatch):
    import subprocess
    import sys

    from tamagoshi_cripto import i18n
    for v in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(i18n.locale, "getlocale", lambda: (None, None))
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, '(\n    "pt-BR",\n    "en-US"\n)\n', ""))
    assert i18n.detectar() == "pt"


def test_janela_sem_borda_mac_e_outros(monkeypatch):
    from tamagoshi_cripto import sistema
    class R:
        def __init__(s): s.chamadas = []; s._w = "."; s.tk = s
        def call(s, *a): s.chamadas.append(a)
        def overrideredirect(s, v): s.chamadas.append(("override", v))
        def after(s, ms, f): s.chamadas.append(("after", ms)); f()
        def lift(s): s.chamadas.append(("lift",))
        def focus_force(s): s.chamadas.append(("focus_force",))
        def focus_set(s): s.chamadas.append(("focus_set",))
    monkeypatch.setattr(sistema, "MAC", True)
    r = R()
    assert sistema.janela_sem_borda(r) == "mac-plain" and ("override", True) not in r.chamadas
    sistema.focar_teclado(r)
    assert ("after", 80) in r.chamadas and ("focus_set",) in r.chamadas
    monkeypatch.setattr(sistema, "MAC", False)
    r = R()
    assert sistema.janela_sem_borda(r) == "override" and r.chamadas == [("override", True)]
