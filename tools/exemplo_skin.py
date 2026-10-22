"""Gera a criatura de exemplo da comunidade: "Slime da Liquidez".
Use como modelo pra criar a sua (veja CONTRIBUTING.md). Rode: python tools/exemplo_skin.py
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from satoshipet import sprites as S
from satoshipet.pixel import W


def slime(s, e, f, k):
    S.sombra(s, 24, 12)
    alt = {"garimpando": 9, "moon": 11, "rekt": 5}[e]
    s.esfera(24, 44 - alt, 14, alt + 1, "azul" if e != "rekt" else "pedra", clip=lambda x, y: y < 44)
    s.ret(14, 44 - alt - 2, 3, 2, "branco", "azul")  # brilho gelatinoso
    if e == "moon":
        S.olhos(s, 18, 44 - alt + 1, 9, "oculos")
        S.faiscas(s, [(6, 10 + f), (41, 8 - f), (44, 20)], ("ciano", "branco"))
    elif e == "rekt":
        S.olhos(s, 18, 44 - alt + 1, 9, "x")
        for i in range(3):  # derretendo em poça
            s.efeito(8 + i * 14 + f, 44, "celeste")
    else:
        S.olhos(s, 18, 44 - alt + 1, 9, "pisca" if f == 3 else "normal")
        for i in range(3):  # bolhas de liquidez subindo
            s.efeito(20 + i * 5, 30 - alt - ((f + i) % 4) * 2, "ciano")
    s.marcar_ancora(24, 44 - alt * 2, 10)


if __name__ == "__main__":
    pasta = RAIZ / "src" / "satoshipet" / "assets" / "skins" / "slime"
    pasta.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    folha = Image.new("RGBA", (W * 4, W * 4), (0, 0, 0, 0))
    for j, linha in enumerate(S.LINHAS):
        for fr in range(4):
            folha.paste(S.desenhar("BTC", "padrao", linha, fr, extra=slime), (fr * W, j * W))
    folha.save(pasta / "sheet.png")
    (pasta / "skin.json").write_text(json.dumps({
        "id": "slime", "nome": "Slime da Liquidez", "autor": "satoshipet",
        "descricao": "Criatura de exemplo da comunidade: uma pool de liquidez com sentimentos.",
        "frases": {"garimpando": ["provendo liquidez...", "impermanent loss? nunca ouvi"],
                   "moon": ["APY de 9000%!", "TVL nas alturas!"],
                   "rekt": ["fui drenado...", "rug pull na minha alma"]},
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("ok:", pasta)
