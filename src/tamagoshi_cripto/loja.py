"""loja.py - Loja de skins: pacotes sazonais, collabs com artistas e pacotes patrocinados (marcas).

Formato de pacote (pasta):
  loja/<id>/pack.json   {"id", "nome", "tipo": "sazonal"|"colab"|"patrocinado", "tier": "free"|"pro"|"codigo",
                         "autor", "creditos", "licenca_arte", "revenue_share": {"artista": 70, "projeto": 30},
                         "preco_sugerido_brl", "temporada": {"de": "10-01", "ate": "11-02"} (opcional),
                         # só patrocinado:
                         "patrocinador", "disclosure": "patrocinado", "autorizacao", "vigencia": {"de", "ate"}}
  loja/<id>/<MOEDA>.png  folha 192x192 (mesmo formato das skins; pelo menos BTC.png)
Destrave: "free" = todo mundo; "pro" = licença Pro; "codigo" = código SKIN-<ID>-<HMAC> (keygen --pack).
Nada de pagamento aqui dentro: quem vende é o provedor de licença de sempre (Gumroad/Lemon/Hotmart).
"""
import datetime as dt
import hashlib
import hmac
import json
import re
from pathlib import Path

from . import license, recursos

TIPOS = ("sazonal", "colab", "patrocinado")
TIERS = ("free", "pro", "codigo")
RE_ID = re.compile(r"^[a-z0-9_]{3,24}$")
ROTULO_TIPO = {"sazonal": "SAZONAL", "colab": "COLAB", "patrocinado": "PATROCINADO"}


def pastas(extra=None):
    p = [recursos.ASSETS / "loja", Path.home() / ".tamagoshi_cripto" / "loja"]
    return ([Path(extra)] if extra else []) + p


def validar_pack(pasta):
    """(meta, erro). Regras de marca: disclosure 'patrocinado' obrigatório, autorização e vigência."""
    pasta = Path(pasta)
    try:
        meta = json.loads((pasta / "pack.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"pack.json ilegível: {e}"
    for c in ("id", "nome", "tipo", "tier", "autor", "creditos"):
        if not meta.get(c):
            return None, f"campo obrigatório ausente: {c}"
    if not RE_ID.match(meta["id"]) or meta["id"] != pasta.name:
        return None, "id inválido (a-z0-9_, 3-24) ou diferente do nome da pasta"
    if meta["tipo"] not in TIPOS or meta["tier"] not in TIERS:
        return None, "tipo/tier inválido"
    if meta["tipo"] == "patrocinado":
        if meta.get("disclosure") != "patrocinado":
            return None, "pacote de marca precisa de \"disclosure\": \"patrocinado\""
        for c in ("patrocinador", "autorizacao", "vigencia"):
            if not meta.get(c):
                return None, f"pacote de marca sem {c}"
    if meta["tipo"] == "colab":
        rs = meta.get("revenue_share") or {}
        if sum(rs.values()) != 100:
            return None, "revenue_share precisa somar 100"
    folhas = {p.stem.upper(): str(p) for p in pasta.glob("*.png") if p.stem.upper() in
              ("BTC", "ETH", "SOL", "DOGE", "PEPE")}
    if "BTC" not in folhas:
        return None, "falta BTC.png (192x192)"
    for f in folhas.values():
        with open(f, "rb") as fh:
            cab = fh.read(24)
        if cab[:8] != b"\x89PNG\r\n\x1a\n" or (int.from_bytes(cab[16:20], "big"),
                                                   int.from_bytes(cab[20:24], "big")) != (192, 192):
            return None, f"{Path(f).name} precisa ser PNG 192x192"
    meta["_folhas"] = folhas
    return meta, None


def catalogo(extra=None):
    out = {}
    for base in pastas(extra):
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir():
                meta, erro = validar_pack(p)
                if erro:
                    print(f"[loja] pacote {p.name} ignorado: {erro}")
                elif meta["id"] not in out:
                    out[meta["id"]] = meta
    return out


def _md(s, hoje):
    m, d = map(int, s.split("-")[-2:])
    return (m, d) <= (hoje.month, hoje.day)


def em_temporada(meta, hoje=None):
    t = meta.get("temporada")
    if not t:
        return True
    hoje = hoje or dt.date.today()
    de, ate = t["de"], t["ate"]
    if (int(de[:2]), int(de[3:])) <= (int(ate[:2]), int(ate[3:])):
        return _md(de, hoje) and not _md_depois(ate, hoje)
    return _md(de, hoje) or not _md_depois(ate, hoje)  # vira o ano (ex.: dez -> jan)


def _md_depois(s, hoje):
    m, d = map(int, s.split("-")[-2:])
    return (hoje.month, hoje.day) > (m, d)


def vigente(meta, hoje=None):
    """Patrocínio fora da vigência some da loja (a marca não paga pra sempre)."""
    v = meta.get("vigencia")
    if not v:
        return True
    hoje = (hoje or dt.date.today()).isoformat()
    return v.get("de", "0000") <= hoje <= v.get("ate", "9999")


def gerar_codigo(pack_id, email="*"):
    """Código de destrave. email='*' = código promocional (vale pra todo mundo, ex.: prêmio de concurso)."""
    msg = f"pack:{pack_id}:{(email or '*').strip().lower()}".encode()
    return f"SKIN-{pack_id.upper()}-" + hmac.new(license.SEGREDO, msg, hashlib.sha256).hexdigest()[:12].upper()


def validar_codigo(codigo, email=""):
    """Retorna o pack_id se o código for válido (pro e-mail da licença ou promocional)."""
    c = (codigo or "").strip().upper()
    m = re.match(r"^SKIN-([A-Z0-9_]{3,24})-([0-9A-F]{12})$", c)
    if not m:
        return None
    pid = m.group(1).lower()
    for alvo in ({email, "*"} if email else {"*"}):
        if hmac.compare_digest(gerar_codigo(pid, alvo), c):
            return pid
    return None


def destravado(meta, pro, codigos):
    if meta["tier"] == "free":
        return True
    if meta["tier"] == "pro":
        return pro or meta["id"] in codigos
    return meta["id"] in codigos


def folha(meta, moeda):
    return meta["_folhas"].get(moeda) or meta["_folhas"]["BTC"]
