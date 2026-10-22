"""plugins.py - criaturas da comunidade: uma pasta com sheet.png + skin.json.

Formato (veja CONTRIBUTING.md):
  skins/<id>/skin.json   {"id", "nome", "autor", "descricao", "moedas": ["BTC", ...] (opcional),
                          "frases": {"garimpando": [...], "moon": [...], "rekt": [...]} (opcional)}
  skins/<id>/sheet.png   192x192 RGBA: 4 linhas (garimpando, moon, rekt, pulo) x 4 frames de 48x48,
                          fundo 100% transparente.
"""
import json
from pathlib import Path

from . import recursos

TAM_FOLHA = (192, 192)


def pastas_busca(extra=None):
    pastas = [recursos.ASSETS / "skins", Path.home() / ".satoshipet" / "skins"]
    if extra:
        pastas.insert(0, Path(extra))
    return pastas


def validar(pasta):
    """Retorna (meta, erro). erro=None se a skin estiver ok."""
    meta_p, folha_p = Path(pasta) / "skin.json", Path(pasta) / "sheet.png"
    if not meta_p.exists() or not folha_p.exists():
        return None, "faltando skin.json ou sheet.png"
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, f"skin.json inválido: {e}"
    for campo in ("id", "nome", "autor"):
        if not meta.get(campo):
            return None, f"campo obrigatório ausente: {campo}"
    with open(folha_p, "rb") as fh:  # lê o tamanho direto do cabeçalho PNG (sem Pillow)
        cab = fh.read(24)
    if cab[:8] != b"\x89PNG\r\n\x1a\n":
        return None, "sheet.png não é PNG"
    w, h = int.from_bytes(cab[16:20], "big"), int.from_bytes(cab[20:24], "big")
    if (w, h) != TAM_FOLHA:
        return None, f"sheet.png deve ter {TAM_FOLHA[0]}x{TAM_FOLHA[1]} (tem {w}x{h})"
    meta["_folha"] = str(folha_p)
    return meta, None


def descobrir(extra=None):
    """{id: meta} de todas as skins válidas. Inválidas são ignoradas com aviso."""
    achadas = {}
    for base in pastas_busca(extra):
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir():
                meta, erro = validar(p)
                if erro:
                    print(f"[skins] ignorando {p.name}: {erro}")
                else:
                    achadas.setdefault("plugin:" + meta["id"], meta)
    return achadas
