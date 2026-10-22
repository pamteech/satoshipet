"""ui.py - o kit de UI pixel do app: UMA paleta, UM jeito de fazer botão, painel, aba e toast.

Antes cada tela inventava a sua moldura (cada uma com um verde diferente 🙃). Agora:
  - cores e espaçamentos moram aqui (PAD, ALT_BOTAO, ALT_LINHA);
  - `botao`, `painel`, `abas`, `linha_ajuste`, `cabecalho` e `rodape` desenham no canvas do app;
  - quem tem foco de teclado ganha a mesma moldura amarela piscante em qualquer tela.
"""
from __future__ import annotations

from typing import Any

# ---- paleta (Sweetie 16, a mesma dos sprites) ----
TINTA, PAPEL = "#1a1c2c", "#f4f4f4"
CINZA, CINZA_ESC, CINZA_CLARO = "#566c86", "#333c57", "#94b0c2"
VERDE, VERDE_LUZ, VERDE_SOMBRA = "#38b764", "#a7f070", "#257179"
OURO, LARANJA, VINHO, CIANO, AZUL = "#ffcd75", "#ef7d57", "#b13e53", "#73eff7", "#41a6f6"
FUNDO_CENA, FUNDO_CENA_LUZ = "#29213f", "#3e3466"
FOCO = "#ffcd75"

# ---- espaçamento (px lógicos; 8px = 1 caractere da fonte) ----
PAD = 8
ALT_BOTAO = 24
ALT_LINHA = 18
ALT_ABA = 18


def _clarear(cor: str, f: float = 1.35) -> str:
    h = cor.lstrip("#")
    return "#" + "".join(f"{min(255, int(int(h[i:i + 2], 16) * f)):02x}" for i in (0, 2, 4))


def _escurecer(cor: str, f: float = 0.65) -> str:
    h = cor.lstrip("#")
    return "#" + "".join(f"{int(int(h[i:i + 2], 16) * f):02x}" for i in (0, 2, 4))


def anel_foco(app: Any, x0: int, y0: int, x1: int, y1: int) -> None:
    """Moldura de foco: 2px amarelos com 'formiguinhas' (pisca junto com o relógio do app)."""
    c = app.cv
    relogio: int = getattr(getattr(app, "cena", None), "t", None) or getattr(app, "frame", 0) or 0
    cor = FOCO if (relogio // 3) % 2 == 0 else PAPEL
    for d in (0, 1):
        c.create_rectangle(x0 - 2 - d, y0 - 2 - d, x1 + 2 + d, y1 + 2 + d, outline=cor if d == 0 else TINTA, width=1)


def botao(app: Any, x0: int, y0: int, x1: int, y1: int, texto: str, fundo: str = VERDE, ativo: bool = True,
          foco: bool = False, tags: tuple = ()) -> None:
    app._moldura(x0, y0, x1, y1, fundo if ativo else CINZA, luz=_clarear(fundo) if ativo else None,
                 sombra=_escurecer(fundo) if ativo else None, tags=tags)
    app._txt((x0 + x1) // 2, (y0 + y1) // 2 + 1, texto, TINTA if ativo else CINZA_ESC, tags=tags)
    if foco:
        anel_foco(app, x0, y0, x1, y1)


def painel(app: Any, x0: int, y0: int, x1: int, y1: int, fundo: str = FUNDO_CENA) -> None:
    app._moldura(x0, y0, x1, y1, fundo, borda=TINTA, luz=_clarear(fundo, 1.25), sombra=TINTA)


def cabecalho(app: Any, titulo: str, cor: str = OURO) -> None:
    """Fundo de cena + título: toda tela cheia começa igual."""
    L, H = app.LARG, app.ALT
    app.cv.delete("all")
    painel(app, 2, 2, L - 2, H - 2)
    app._txt(L // 2, 16, titulo, cor, sombra=TINTA)


def rodape(app: Any, dica: str) -> None:
    app._txt(app.LARG // 2, app.ALT - 8, dica, CINZA, max_chars=(app.LARG - 8) // 8)


def abas(app: Any, alvos: list, y: int, nomes: list, ativa: int, foco: int | None = None) -> None:
    L = app.LARG
    w = (L - 8) // len(nomes)
    for i, n in enumerate(nomes):
        x0 = 4 + i * w
        sel = i == ativa
        app._moldura(x0, y, x0 + w - 2, y + ALT_ABA, OURO if sel else CINZA_ESC,
                     luz=_clarear(OURO) if sel else None, tags=())
        app._txt(x0 + (w - 2) // 2, y + ALT_ABA // 2 + 1, n, TINTA if sel else CINZA_CLARO)
        if foco == i:
            anel_foco(app, x0, y, x0 + w - 2, y + ALT_ABA)
        alvos.append((x0, y, x0 + w - 2, y + ALT_ABA, f"aba:{i}"))


def linha_ajuste(app: Any, y: int, rotulo: str, valor: str, foco: bool, ativo: bool = True,
                 cor_valor: str = PAPEL, editando: bool = False) -> None:
    """Uma linha 'rótulo ........ valor' da tela de ajustes."""
    L, c = app.LARG, app.cv
    if foco:
        c.create_rectangle(PAD, y, L - PAD, y + ALT_LINHA - 2, fill=CINZA_ESC, width=0)
        anel_foco(app, PAD, y, L - PAD, y + ALT_LINHA - 2)
    app._txt(PAD + 4, y + 4, rotulo, PAPEL if ativo else CINZA, anchor="nw")
    if editando:
        c.create_rectangle(L // 2, y + 1, L - PAD - 2, y + ALT_LINHA - 3, fill=TINTA, outline=OURO)
    app._txt(L - PAD - 4, y + 4, valor, cor_valor if ativo else CINZA, anchor="ne")
