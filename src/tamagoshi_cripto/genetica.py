"""genetica.py - DNA de bicho. Genes, cruzamento, mutação e o "código do pet" pra trocar com amigos.

Sem NFT, sem blockchain, sem promessa de valor: é só um texto que você manda no zap. 🧬
Genes:  paleta (troca de cores Sweetie-16), olhos (cor), acessorio (pixel art na cabeça),
        padrao (pintas/listras/brilho no corpo) e a raridade que sai da soma.
"""
import base64
import hashlib
import json
import random
import zlib
from collections import Counter

from PIL import Image

from .pixel import P, rgb

# opção -> (peso de sorteio, pontos de raridade)
GENES = {
    "paleta": {"original": (50, 0), "gelo": (14, 1), "toxico": (12, 1), "rosa": (10, 1), "noir": (8, 2),
               "ouro": (4, 3), "invertido": (2, 4)},
    "olhos": {"normal": (60, 0), "neon": (18, 1), "laser": (14, 2), "zen": (8, 2)},
    "acessorio": {"nenhum": (45, 0), "laco": (16, 1), "antena": (14, 1), "coroinha": (8, 2), "fone": (12, 1),
                  "aureola": (5, 3)},
    "padrao": {"liso": (55, 0), "pintas": (20, 1), "listras": (15, 1), "brilho": (10, 2)},
}
RARIDADES = [(0, "comum"), (2, "raro"), (4, "épico"), (7, "lendário")]
COR_RARIDADE = {"comum": "#94b0c2", "raro": "#41a6f6", "épico": "#b13e53", "lendário": "#ffcd75"}

PALETAS = {
    "original": {},
    "gelo": {"laranja": "celeste", "amarelo": "ciano", "vinho": "azul", "roxo": "marinho", "verde": "petroleo",
             "lima": "ciano"},
    "toxico": {"laranja": "lima", "amarelo": "branco", "vinho": "verde", "roxo": "petroleo", "azul": "verde",
               "celeste": "lima", "marinho": "petroleo"},
    "rosa": {"laranja": "vinho", "amarelo": "laranja", "azul": "roxo", "celeste": "vinho", "ciano": "amarelo",
             "marinho": "roxo", "verde": "vinho", "lima": "laranja"},
    "noir": {"laranja": "cinza_claro", "amarelo": "branco", "vinho": "cinza", "roxo": "grafite", "verde": "cinza",
             "lima": "cinza_claro", "azul": "cinza", "celeste": "cinza_claro", "ciano": "branco", "marinho": "grafite",
             "petroleo": "grafite"},
    "ouro": {"laranja": "amarelo", "vinho": "laranja", "roxo": "vinho", "azul": "laranja", "celeste": "amarelo",
             "ciano": "branco", "marinho": "vinho", "verde": "laranja", "lima": "amarelo", "cinza": "laranja",
             "cinza_claro": "amarelo", "grafite": "vinho"},
    "invertido": {"laranja": "celeste", "celeste": "laranja", "amarelo": "ciano", "ciano": "amarelo",
                  "vinho": "azul", "azul": "vinho", "roxo": "marinho", "marinho": "roxo", "verde": "roxo",
                  "lima": "laranja"},
}
COR_OLHOS = {"neon": "ciano", "laser": "vinho", "zen": "lima"}
ACESSORIOS = {  # 1 contorno (preto), 2 cor principal, 3 brilho
    "laco": (["11...11", "1211121", "1223221", "1211121", "11...11"], {"2": "vinho", "3": "laranja"}),
    "antena": ([".111.", "12321", ".111.", "..1..", "..1..", "..1.."], {"2": "lima", "3": "branco"}),
    "coroinha": (["1.1.1.1", "1213121", "1222221", "1111111"], {"2": "amarelo", "3": "branco"}),
    "fone": (["..11111..", ".1.....1.", "1.......1", "12.....21", "12.....21", ".1.....1."],
             {"2": "grafite", "3": "cinza"}),
    "aureola": (["..11111..", ".1333331.", "..11111.."], {"3": "amarelo"}),
}


# ---------------- sorteio, raridade e cruzamento ----------------
def _sortear(rnd, gene):
    ops = GENES[gene]
    return rnd.choices(list(ops), weights=[w for w, _ in ops.values()])[0]


def aleatorio(semente=None, moeda="BTC"):
    rnd = random.Random(semente)
    g = {k: _sortear(rnd, k) for k in GENES}
    g.update({"moeda": moeda, "geracao": 1, "id": "%08x" % rnd.getrandbits(32)})
    return g


def raridade(g):
    pontos = sum(GENES[k].get(g.get(k), (0, 0))[1] for k in GENES)
    nome = "comum"
    for minimo, n in RARIDADES:
        if pontos >= minimo:
            nome = n
    return nome, pontos


def cruzar(a, b, semente=None, taxa_mutacao=0.08):
    """Cada gene vem do pai ou da mãe; com taxa_mutacao vira uma opção sorteada (pode sair lendário!)."""
    rnd = random.Random(semente)
    filho, mutou = {}, []
    for k in GENES:
        if rnd.random() < taxa_mutacao:
            filho[k] = _sortear(rnd, k)
            mutou.append(k)
        else:
            filho[k] = (a if rnd.random() < .5 else b).get(k, "original")
    filho.update({"moeda": rnd.choice([a.get("moeda", "BTC"), b.get("moeda", "BTC")]),
                  "geracao": max(a.get("geracao", 1), b.get("geracao", 1)) + 1,
                  "id": "%08x" % rnd.getrandbits(32), "pais": [a.get("id"), b.get("id")]})
    return filho, mutou


# ---------------- código do pet ----------------
PREFIXO = "TAMA1-"


def exportar(pet):
    """pet = {"nome", "genes", "nivel", "xp", "estagio"} -> 'TAMA1-....' (compacto, com checksum)."""
    leve = {"n": pet.get("nome", "")[:12], "g": {k: pet["genes"].get(k) for k in (*GENES, "moeda", "geracao", "id")},
            "lv": int(pet.get("nivel", 1)), "xp": int(pet.get("xp", 0)), "e": pet.get("estagio", "ovo")}
    dados = zlib.compress(json.dumps(leve, separators=(",", ":")).encode())
    soma = hashlib.sha256(dados).hexdigest()[:6]
    return PREFIXO + base64.urlsafe_b64encode(dados).decode().rstrip("=") + "-" + soma


MAX_JSON = 4096


def _int(v, lo, hi, padrao):
    """int limitado; aceita só int/float finitos de verdade (bool e texto viram o padrão)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        return padrao
    return max(lo, min(hi, int(v)))


def importar(codigo):
    """Retorna (pet, erro). Valida checksum e genes (código de amigo é dado NÃO confiável:
    o checksum só pega erro de cópia, qualquer um consegue forjar um)."""
    try:
        c = (codigo or "").strip()
        if not c.startswith(PREFIXO):
            return None, "código de pet começa com TAMA1-"
        if len(c) > 4096:
            return None, "código grande demais"
        corpo, soma = c[len(PREFIXO):].rsplit("-", 1)
        dados = base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4))
        if hashlib.sha256(dados).hexdigest()[:6] != soma:
            return None, "código corrompido (checksum não bate). copiou inteiro?"
        z = zlib.decompressobj()
        bruto = z.decompress(dados, MAX_JSON + 1)  # anti zip-bomb: nunca descomprime mais que 4 KB
        if len(bruto) > MAX_JSON or z.unconsumed_tail:
            return None, "código grande demais"
        leve = json.loads(bruto)
    except Exception:
        return None, "código de pet inválido"
    if not isinstance(leve, dict) or not isinstance(leve.get("g"), dict):
        return None, "código de pet inválido"
    g = leve["g"]
    for k in GENES:
        if not isinstance(g.get(k), str) or g.get(k) not in GENES[k]:
            return None, f"gene inválido: {k}"
    if not isinstance(g.get("moeda"), str) or g.get("moeda") not in ("BTC", "ETH", "SOL", "DOGE", "PEPE"):
        return None, "moeda inválida"
    genes = {k: g[k] for k in GENES}
    genes.update(moeda=g["moeda"], geracao=_int(g.get("geracao"), 1, 999, 1),
                 id=g["id"][:16] if isinstance(g.get("id"), str) else "%08x" % (hash(corpo) & 0xFFFFFFFF))
    e = leve.get("e")
    est = e if isinstance(e, str) and e in ("ovo", "bebe", "adulto", "whale", "diamond") else "ovo"
    nome = leve.get("n")
    nome = "".join(ch for ch in nome if ch.isprintable())[:12] if isinstance(nome, str) else ""
    return {"nome": nome or "anon", "genes": genes, "nivel": _int(leve.get("lv"), 1, 99, 1),
            "xp": _int(leve.get("xp"), 0, 10_000_000, 0), "estagio": est}, None


# ---------------- aplicar no sprite (48x48, antes de ampliar) ----------------
_HEX = {k: rgb(v) for k, v in P.items()}
_POR_RGB = {v: k for k, v in _HEX.items()}


def _cor_corpo(fr):
    cont = Counter(px[:3] for px in fr.getdata() if px[3] and px[:3] != _HEX["preto"])
    return cont.most_common(1)[0][0] if cont else None


def aplicar(fr, g):
    """Devolve cópia do frame RGBA 48x48 com os genes aplicados (pixel exato, só cores da paleta)."""
    if not g:
        return fr
    out = fr.copy()
    px = out.load()
    troca = {_HEX[a]: _HEX[b] for a, b in PALETAS.get(g.get("paleta"), {}).items()}
    corpo = _cor_corpo(fr)
    caixa = fr.getchannel("A").getbbox() or (0, 0, 48, 48)
    meio_y = (caixa[1] + caixa[3]) // 2
    for y in range(48):
        for x in range(48):
            r, gg, b, a = px[x, y]
            if not a:
                continue
            c = (r, gg, b)
            # olhos: pixels pretos internos (cercados de cor) na metade de cima
            if g.get("olhos") in COR_OLHOS and c == _HEX["preto"] and y < meio_y and 0 < x < 47 and 0 < y < 47:
                viz = [fr.getpixel((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                if all(v[3] for v in viz) and sum(v[:3] != _HEX["preto"] for v in viz) >= 3:
                    px[x, y] = _HEX[COR_OLHOS[g["olhos"]]] + (255,)
                    continue
            if c == corpo and g.get("padrao") in ("pintas", "listras"):
                if (g["padrao"] == "pintas" and (x * 7 + y * 13) % 11 == 0) or \
                        (g["padrao"] == "listras" and y % 4 == 0):
                    px[x, y] = _escurecer(troca.get(c, c)) + (255,)
                    continue
            if c in troca:
                px[x, y] = troca[c] + (255,)
    if g.get("padrao") == "brilho":
        for i, (dx, dy) in enumerate(((-2, 4), (caixa[2] - caixa[0] + 1, 10), (-1, 22))):
            X, Y = caixa[0] + dx, caixa[1] + dy
            if 0 <= X < 48 and 0 <= Y < 48 and not px[X, Y][3]:
                px[X, Y] = _HEX["branco" if i % 2 else "ciano"] + (255,)
    ac = ACESSORIOS.get(g.get("acessorio"))
    if ac:
        from .juice import _topo_cabeca
        arte, cores = ac
        cx, topo = _topo_cabeca(fr)
        w, h = len(arte[0]), len(arte)
        if g["acessorio"] == "laco":
            x0, y0 = cx + 3, topo - 2
        elif g["acessorio"] == "fone":
            x0, y0 = cx - w // 2, topo - 1
        elif g["acessorio"] == "aureola":
            x0, y0 = cx - w // 2, topo - h - 1
        else:
            x0, y0 = cx - w // 2, topo - h + 1
        for j, linha in enumerate(arte):
            for i, ch in enumerate(linha):
                X, Y = x0 + i, y0 + j
                if ch != "." and 0 <= X < 48 and 0 <= Y < 48:
                    px[X, Y] = (_HEX["preto"] if ch == "1" else _HEX[cores[ch]]) + (255,)
    return out


_ESCURO = {"amarelo": "laranja", "laranja": "vinho", "vinho": "roxo", "lima": "verde", "verde": "petroleo",
           "ciano": "celeste", "celeste": "azul", "azul": "marinho", "branco": "cinza_claro",
           "cinza_claro": "cinza", "cinza": "grafite"}


def _escurecer(c):
    nome = _POR_RGB.get(c)
    return _HEX[_ESCURO[nome]] if nome in _ESCURO else c


def fantasma(fr):
    """Versão fantasminha: silhueta ciano/branca com barra 'ondulada' e olhos vazados."""
    out = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    a = fr.getchannel("A")
    caixa = a.getbbox() or (0, 0, 48, 48)
    po, pi = out.load(), fr.load()
    for y in range(48):
        for x in range(48):
            if not pi[x, y][3]:
                continue
            borda = any(not (0 <= x + dx < 48 and 0 <= y + dy < 48) or not pi[x + dx, y + dy][3]
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if y > caixa[3] - 5 and (x // 3) % 2 == (y - caixa[3]) % 2:  # barrinha ondulada
                continue
            c = pi[x, y][:3]
            if borda:
                po[x, y] = _HEX["celeste"] + (255,)
            elif c == _HEX["preto"]:
                po[x, y] = _HEX["marinho"] + (255,)
            else:
                po[x, y] = (_HEX["branco"] if (x + y) % 5 else _HEX["ciano"]) + (255,)
    return out
