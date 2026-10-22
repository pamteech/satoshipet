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


def test_sprite_mac_tem_pixels_opacos(monkeypatch):
    """Caminho do macOS (put, sem PNG alfa): o frame tem pixel pintado e o fundo fica transparente."""
    import sys
    import tkinter as tk

    from tamagoshi_cripto import graficos, recursos
    root = tk.Tk()
    try:
        monkeypatch.setattr(sys, "platform", "darwin")
        folha = next((recursos.ASSETS / "sprites").glob("*.png"))
        frames = graficos.carregar_frames(folha, 3)
        img = frames[next(iter(frames))]
        w, h = img.width(), img.height()
        opacos = sum(not img.transparency_get(x, y) for x in range(0, w, 3) for y in range(0, h, 3))
        assert w == 144 and 50 < opacos < (w // 3) * (h // 3)
        assert img.transparency_get(0, 0)
        cv = tk.Canvas(root, width=w, height=h, bg="#010101")
        cv.create_image(w // 2, h // 2, image=img)
        assert cv.find_all()
    finally:
        root.destroy()
