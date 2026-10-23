"""marcos.py - v1.8: aniversários do bicho e festa de ATH do BTC (lógica pura, fácil de testar)."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

DIA = 86400
# (dias, nome curto, efeito)
MARCOS: List[Tuple[int, str, str]] = [
    (7, "1 semana", "confete"),
    (30, "1 mês", "bolo"),
    (100, "100 dias", "fogos"),
    (182, "6 meses", "bolo"),
    (365, "1 ano", "fogos"),
    (500, "500 dias", "confete"),
    (1000, "1000 dias", "fogos"),
]
CONQ_MARCO = {7: "aniv_semana", 30: "aniv_mes", 100: "aniv_100d", 365: "aniv_ano"}
FRASES = {
    "confete": "{n} de HODL juntos!",
    "bolo": "parabéns pra mim! {n} de vida",
    "fogos": "{n}! nem o mt. gox me derrubou",
}


def lista(ate_dias: int) -> List[Tuple[int, str, str]]:
    """MARCOS + todo aniversário de ano (2 anos, 3 anos...) até `ate_dias`."""
    out = list(MARCOS)
    anos = 2
    while anos * 365 <= ate_dias:
        out.append((anos * 365, f"{anos} anos", "fogos"))
        anos += 1
    return sorted(out)


def idade_dias(nasceu_em: float, agora: Optional[float] = None) -> int:
    if not nasceu_em:
        return 0
    return max(0, int(((agora or time.time()) - float(nasceu_em)) // DIA))


def pendente(nasceu_em: float, feitos: List[int], agora: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """O MAIOR marco já alcançado e ainda não comemorado (atrasado não vira spam de 5 bolos)."""
    dias = idade_dias(nasceu_em, agora)
    alc = [m for m in lista(dias) if m[0] <= dias and m[0] not in set(feitos)]
    if not alc:
        return None
    d, nome, fx = alc[-1]
    return {"dias": d, "nome": nome, "fx": fx, "alcancados": [m[0] for m in lista(dias) if m[0] <= dias],
            "frase": FRASES[fx].format(n=nome), "conquista": CONQ_MARCO.get(d)}


def checar_ath(cfg: Dict[str, Any], ath_api: Optional[float], preco: Optional[float],
               agora: Optional[float] = None) -> Optional[float]:
    """Novo ATH do BTC? Devolve o valor (e grava em cfg) só UMA vez por ATH novo.
    1ª vez (sem ATH guardado) só aprende, não comemora. Rali batendo ATH a cada minuto = 1 festa a cada 20 h."""
    agora = agora or time.time()
    cand = max([v for v in (ath_api, preco) if v] or [0.0])
    if cand <= 0:
        return None
    conhecido = float(cfg.get("ath_btc") or 0)
    if conhecido <= 0:
        cfg["ath_btc"] = cand
        return None
    if cand <= conhecido * 1.0001:
        return None
    cfg["ath_btc"] = cand
    if agora - float(cfg.get("ath_btc_festa") or 0) < 20 * 3600:
        return None
    cfg["ath_btc_festa"] = agora
    return cand
