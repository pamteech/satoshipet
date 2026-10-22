"""validate_skin.py - juiz do Concurso de Skins. Valida pastas de skin e gera preview.

    python tools/validate_skin.py src/tamagoshi_cripto/assets/skins/slime [outra/pasta ...] [--preview DIR]
    python tools/validate_skin.py --all --preview previews/

Regras (falha = exit 1):
  - skin.json com id/nome/autor; id em [a-z0-9_-]{2,24} e igual ao nome da pasta
  - sheet.png 192x192 RGBA, 4 linhas x 4 frames de 48x48
  - fundo transparente: cantos 100% alfa 0; alfa só 0 ou 255 (pixel art sem semi-transparência)
  - nenhum frame vazio; no máximo 32 cores (paleta de pixel art, não foto)
  - frases (opcional) são listas de strings curtas (<= 60 chars)
Avisos (não falham): bicho encostando na borda, cor única demais, arquivo > 64 KB.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
PASTA_SKINS = RAIZ / "src" / "tamagoshi_cripto" / "assets" / "skins"
LINHAS = ["garimpando", "moon", "rekt", "pulo"]
FUNDO = (26, 28, 44, 255)


def validar(pasta):
    pasta = Path(pasta)
    erros, avisos = [], []
    meta_p, folha_p = pasta / "skin.json", pasta / "sheet.png"
    if not meta_p.exists() or not folha_p.exists():
        return ["faltando skin.json ou sheet.png"], avisos, None
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"skin.json inválido: {e}"], avisos, None
    for c in ("id", "nome", "autor"):
        if not str(meta.get(c, "")).strip():
            erros.append(f"skin.json: campo obrigatório '{c}'")
    sid = str(meta.get("id", ""))
    if sid and not re.fullmatch(r"[a-z0-9_\-]{2,24}", sid):
        erros.append("id deve ser [a-z0-9_-], 2 a 24 chars")
    if sid and sid != pasta.name:
        erros.append(f"id '{sid}' deve ser igual ao nome da pasta '{pasta.name}'")
    for humor, frases in (meta.get("frases") or {}).items():
        if humor not in ("garimpando", "moon", "rekt"):
            erros.append(f"frases: humor desconhecido '{humor}'")
        if not isinstance(frases, list) or not all(isinstance(f, str) and len(f) <= 60 for f in frases):
            erros.append(f"frases.{humor}: lista de strings de até 60 chars")
    img = Image.open(folha_p)
    if img.size != (192, 192):
        return erros + [f"sheet.png deve ser 192x192 (é {img.size[0]}x{img.size[1]})"], avisos, None
    if img.mode != "RGBA":
        avisos.append(f"sheet.png em modo {img.mode}; convertendo pra RGBA")
    img = img.convert("RGBA")
    alfa = img.getchannel("A")
    if any(alfa.getpixel(p) for p in [(0, 0), (191, 0), (0, 191), (191, 191)]):
        erros.append("fundo precisa ser transparente (cantos com alfa 0)")
    semi = sum(alfa.histogram()[1:255])
    if semi:
        erros.append(f"{semi} pixels semi-transparentes: use só alfa 0 ou 255")
    cores = {c[:3] for _, c in (img.getcolors(192 * 192) or []) if c[3]}
    if len(cores) > 32:
        erros.append(f"{len(cores)} cores: máximo 32 (pixel art, não foto)")
    for j, nome in enumerate(LINHAS):
        for f in range(4):
            fr = img.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48))
            caixa = fr.getchannel("A").getbbox()
            if not caixa:
                erros.append(f"frame vazio: linha {nome}, frame {f}")
            elif caixa[0] == 0 or caixa[1] == 0 or caixa[2] == 48 or caixa[3] == 48:
                avisos.append(f"{nome}/{f}: encostando na borda do frame (pode cortar no squash)")
    if folha_p.stat().st_size > 64 * 1024:
        avisos.append("sheet.png > 64 KB (otimize com oxipng/pngcrush)")
    return erros, avisos, img


def preview(img, meta_nome, destino, escala=4):
    """PNG de contato (4x4 ampliado em fundo escuro) + GIF animado de cada linha."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    W = 48 * escala
    folha = Image.new("RGBA", (W * 4 + 50, W * 4 + 50), FUNDO)
    for j in range(4):
        for f in range(4):
            fr = img.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48)).resize((W, W), Image.NEAREST)
            folha.alpha_composite(fr, (10 + f * (W + 10), 10 + j * (W + 10)))
    folha.convert("RGB").save(destino.with_suffix(".png"))
    frames = []
    for j in range(4):
        for f in range(4):
            fundo = Image.new("RGBA", (W, W), FUNDO)
            fundo.alpha_composite(img.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48)).resize((W, W), Image.NEAREST))
            frames += [fundo.convert("RGB")] * 2
    frames[0].save(destino.with_suffix(".gif"), save_all=True, append_images=frames[1:], duration=90, loop=0)
    return destino.with_suffix(".png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pastas", nargs="*")
    ap.add_argument("--all", action="store_true", help="valida todas em assets/skins")
    ap.add_argument("--preview", help="pasta pra salvar previews PNG/GIF")
    a = ap.parse_args(argv)
    pastas = [Path(p) for p in a.pastas] + (sorted(p for p in PASTA_SKINS.iterdir() if p.is_dir()) if a.all else [])
    if not pastas:
        ap.error("passe pelo menos uma pasta (ou --all)")
    falhou = False
    relatorio = ["| skin | resultado | avisos |", "|---|---|---|"]
    for p in pastas:
        erros, avisos, img = validar(p)
        status = "✅ ok" if not erros else "❌ " + "; ".join(erros)
        print(f"[{p.name}] {'OK' if not erros else 'FALHOU'}")
        for e in erros:
            print("   erro:", e)
        for w in avisos:
            print("   aviso:", w)
        relatorio.append(f"| `{p.name}` | {status} | {'; '.join(avisos) or '—'} |")
        falhou |= bool(erros)
        if a.preview and img is not None:
            print("   preview:", preview(img, p.name, Path(a.preview) / p.name))
    if a.preview:
        Path(a.preview).mkdir(parents=True, exist_ok=True)
        (Path(a.preview) / "RELATORIO.md").write_text("\n".join(relatorio) + "\n", encoding="utf-8")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
