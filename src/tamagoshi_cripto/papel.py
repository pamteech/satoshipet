"""papel.py - paper trading: corretora de MENTIRINHA. Dinheiro 100% fictício, preço 100% real.

Ninguém aqui compra cripto de verdade, não tem corretora, não tem conta, não tem KYC.
O bicho fica feliz com PnL verde e chora com PnL vermelho (igual você, mas sem prejuízo real).
"""
import time
from typing import Any, Dict, Optional, Tuple, Union

SALDO_INICIAL = 10_000.0
AVISO = "DINHEIRO FICTÍCIO"
TAXA = 0.001  # 0,1% de "corretagem" de mentira pra ficar realista


def nova() -> Dict[str, Any]:
    return {"usd": SALDO_INICIAL, "pos": {}, "custo": {}, "hist": [], "criada": int(time.time())}


def _ok(c: Dict[str, Any]) -> Dict[str, Any]:
    if not c or "usd" not in c:
        c.clear()
        c.update(nova())
    return c


def comprar(c: Dict[str, Any], moeda: str, usd: float, preco: Optional[Union[float, int]], agora: Any=None) -> Tuple[bool, str]:
    """Compra `usd` dólares (fictícios) de `moeda`. Retorna (ok, msg)."""
    _ok(c)
    if not preco or preco <= 0:
        return False, "sem preço ainda (espera a API)"
    if usd == "all":
        usd = c["usd"]
    usd = float(usd)
    if usd <= 0:
        return False, "valor tem que ser positivo"
    if usd > c["usd"] + 1e-9:
        return False, f"saldo fictício insuficiente (${c['usd']:,.2f})"
    qtd = usd * (1 - TAXA) / preco
    c["usd"] -= usd
    c["pos"][moeda] = c["pos"].get(moeda, 0) + qtd
    c["custo"][moeda] = c["custo"].get(moeda, 0) + usd
    c["hist"].append({"t": int(agora or time.time()), "lado": "compra", "moeda": moeda, "qtd": qtd,
                      "preco": preco, "usd": round(usd, 2)})
    c["hist"] = c["hist"][-200:]
    return True, f"comprou {qtd:.6g} {moeda} a ${preco:,.2f} ({AVISO})"


def vender(c: Dict[str, Any], moeda: str, qtd: Any, preco: float, agora: Any=None) -> Tuple[bool, str]:
    _ok(c)
    tem = c["pos"].get(moeda, 0)
    if not tem:
        return False, f"você não tem {moeda} (nem de mentira)"
    if not preco or preco <= 0:
        return False, "sem preço ainda"
    qtd = tem if qtd == "all" else min(float(qtd), tem)
    if qtd <= 0:
        return False, "quantidade tem que ser positiva"
    usd = qtd * preco * (1 - TAXA)
    custo = c["custo"].get(moeda, 0) * qtd / tem
    c["pos"][moeda] = tem - qtd
    c["custo"][moeda] = c["custo"].get(moeda, 0) - custo
    if c["pos"][moeda] <= 1e-12:
        c["pos"].pop(moeda)
        c["custo"].pop(moeda, None)
    c["usd"] += usd
    lucro = usd - custo
    c["hist"].append({"t": int(agora or time.time()), "lado": "venda", "moeda": moeda, "qtd": qtd, "preco": preco,
                      "usd": round(usd, 2), "lucro": round(lucro, 2)})
    c["hist"] = c["hist"][-200:]
    return True, f"vendeu {qtd:.6g} {moeda}: {'+' if lucro >= 0 else ''}${lucro:,.2f} ({AVISO})"


def resumo(c: Dict[str, Any], precos: Dict[str, Any]) -> Dict[str, Any]:
    """Patrimônio, PnL total (vs $10k) e PnL aberto por moeda."""
    _ok(c)
    pos = {}
    total = c["usd"]
    for m, q in c["pos"].items():
        p = precos.get(m)
        valor = q * p if p else c["custo"].get(m, 0)
        total += valor
        custo = c["custo"].get(m, 0)
        pos[m] = {"qtd": q, "valor": valor, "pnl": valor - custo, "pnl_pct": (valor / custo - 1) * 100 if custo else 0}
    pnl = total - SALDO_INICIAL
    return {"usd": c["usd"], "total": total, "pnl": pnl, "pnl_pct": pnl / SALDO_INICIAL * 100, "pos": pos,
            "trades": len(c["hist"]), "aviso": AVISO}


def humor(pnl_pct: float) -> Optional[str]:
    """Como o bicho reage ao PnL fictício: 'moon' / 'rekt' / None."""
    if pnl_pct >= 5:
        return "moon"
    if pnl_pct <= -5:
        return "rekt"
    return None
