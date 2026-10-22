#!/usr/bin/env python3
"""make_packs.py - gera as folhas dos pacotes de exemplo da loja (recolor + acessórios em pixel art).

    python tools/make_packs.py     -> src/satoshipet/assets/loja/<id>/<MOEDA>.png
Artista de verdade? Desenhe as folhas 192x192 à mão e só escreva o pack.json (veja docs/BRAND_SKINS.md).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PIL import Image

from satoshipet import genetica, juice, recursos
from satoshipet.pixel import P, rgb

MOEDAS = ("BTC", "ETH", "SOL", "DOGE", "PEPE")
RECEITAS = {
    "halloween": {"paleta": {"azul": "roxo", "celeste": "vinho", "ciano": "laranja", "verde": "roxo", "lima": "laranja",
                             "branco": "cinza_claro", "marinho": "preto", "petroleo": "roxo", "amarelo": "laranja"},
                  "chapeu": "halloween",
                  "meta": {"nome": "Noites de Bruxa", "tipo": "sazonal", "tier": "pro", "autor": "SatoshiPet",
                           "creditos": "arte: equipe SatoshiPet", "licenca_arte": "MIT",
                           "temporada": {"de": "10-01", "ate": "11-02"}, "preco_sugerido_brl": 0,
                           "descricao": "abóbora, roxo e chapéu de bruxa. incluso no Pro."}},
    "natal": {"paleta": {"laranja": "vinho", "amarelo": "branco", "azul": "verde", "celeste": "lima", "ciano": "branco",
                         "roxo": "petroleo", "marinho": "petroleo"},
              "chapeu": "natal",
              "meta": {"nome": "Natal na Blockchain", "tipo": "sazonal", "tier": "pro", "autor": "SatoshiPet",
                       "creditos": "arte: equipe SatoshiPet", "licenca_arte": "MIT",
                       "temporada": {"de": "12-01", "ate": "01-06"}, "preco_sugerido_brl": 0,
                       "descricao": "gorro de Noel e verde-pinheiro. incluso no Pro."}},
    "neon_nights": {"paleta": {"laranja": "ciano", "amarelo": "branco", "vinho": "roxo", "azul": "roxo",
                               "celeste": "vinho", "verde": "azul", "lima": "ciano", "cinza": "marinho",
                               "cinza_claro": "celeste", "branco": "ciano", "grafite": "marinho"},
                    "genes": {"olhos": "neon", "padrao": "brilho"},
                    "meta": {"nome": "Neon Nights", "tipo": "colab", "tier": "codigo",
                             "autor": "@pixelartista (exemplo)",
                             "creditos": "arte: @pixelartista - collab de exemplo, troque pelo artista real",
                             "licenca_arte": "todos os direitos do artista; uso no app licenciado",
                             "revenue_share": {"artista": 70, "projeto": 30}, "preco_sugerido_brl": 9.9,
                             "descricao": "cyber-neon. 70% da venda vai pro artista."}},
    "cafe_satoshi": {"paleta": {"laranja": "vinho", "amarelo": "laranja", "azul": "vinho", "celeste": "laranja",
                                "ciano": "amarelo", "verde": "vinho", "lima": "laranja", "roxo": "preto"},
                     "genes": {"acessorio": "fone"},
                     "meta": {"nome": "Café do Satoshi", "tipo": "patrocinado", "tier": "free",
                              "autor": "SatoshiPet", "creditos": "arte: equipe SatoshiPet",
                              "licenca_arte": "MIT", "patrocinador": "Café do Satoshi (marca FICTÍCIA de exemplo)",
                              "disclosure": "patrocinado",
                              "autorizacao": "exemplo - num pacote real: nº do contrato/autorização de uso da marca",
                              "vigencia": {"de": "2026-01-01", "ate": "2099-12-31"},
                              "contato": "marcas@exemplo.invalid", "preco_sugerido_brl": 0,
                              "descricao": "exemplo do formato de pacote de marca. grátis pro usuário."}},
}


def recolor(fr, mapa):
    troca = {rgb(P[a]): rgb(P[b]) for a, b in mapa.items()}
    px = fr.load()
    for y in range(fr.height):
        for x in range(fr.width):
            r, g, b, a = px[x, y]
            if a and (r, g, b) in troca:
                px[x, y] = troca[(r, g, b)] + (a,)
    return fr


def main():
    base = recursos.ASSETS / "loja"
    for pid, rec in RECEITAS.items():
        pasta = base / pid
        pasta.mkdir(parents=True, exist_ok=True)
        for m, est in [(m, e) for m in MOEDAS for e in ("adulto", "ovo", "bebe", "whale", "diamond")]:
            sufixo = "" if est == "adulto" else f"_{est}"
            folha = Image.open(recursos.ASSETS / "sprites" / f"{m}_padrao{sufixo}.png").convert("RGBA")
            out = Image.new("RGBA", folha.size, (0, 0, 0, 0))
            for j in range(4):
                for f in range(4):
                    fr = folha.crop((f * 48, j * 48, f * 48 + 48, j * 48 + 48))
                    fr = recolor(fr, rec["paleta"])
                    if rec.get("genes"):
                        fr = genetica.aplicar(fr, rec["genes"])
                    if rec.get("chapeu") and est != "ovo":
                        fr = juice.aplicar_chapeu(fr, rec["chapeu"])
                    out.paste(fr, (f * 48, j * 48))
            out.save(pasta / f"{m}{sufixo}.png", optimize=True)
        meta = dict(rec["meta"], id=pid, **({"genes": rec["genes"]} if rec.get("genes") else {}))
        (pasta / "pack.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("pacote:", pasta)


if __name__ == "__main__":
    main()
