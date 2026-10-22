"""hardcore.py - modo hardcore (opt-in): REKT prolongado + abandono = o bicho morre de verdade.

Vira fantasminha, a lápide vai pro Cemitério de Honra com epitáfio e stats, e a vida recomeça do ovo.
Regras (todas precisam valer ao mesmo tempo):
  - modo hardcore ligado (cfg["hardcore"], desligado por padrão)
  - vida zerada há pelo menos MORTE_MIN minutos
  - nenhum carinho/jogo há pelo menos ABANDONO_H horas
"""
import random
import time
from typing import Any, Dict, Optional

MORTE_MIN = 30
ABANDONO_H = 4
EPITAFIOS = [
    "HODLou até o fim.", "Comprou o topo, vendeu o fundo, viveu intensamente.", "Not your keys, not your pet.",
    "Foi buscar liquidez no céu.", "Morreu como viveu: alavancado.", "Aqui jaz um diamond hand de papel.",
    "Few understood.", "Era só uma correção, disseram.", "gm do outro lado, fren.", "Liquidado, mas nunca esquecido.",
]


def tocar(cfg: Dict[str, Any], agora: Optional[float]=None) -> None:
    """Chame em todo carinho / jogo: o bicho não está abandonado."""
    cfg["ultima_interacao"] = agora or time.time()


def checar(cfg: Dict[str, Any], vida: float, agora: Optional[float]=None) -> bool:
    """Atualiza o relógio da morte. Retorna True se o bicho acabou de morrer."""
    agora = agora or time.time()
    if not cfg.get("hardcore") or cfg.get("fantasma"):
        cfg.pop("zero_desde", None)
        return False
    if vida > 0:
        cfg.pop("zero_desde", None)
        return False
    cfg.setdefault("zero_desde", agora)
    abandono = agora - cfg.get("ultima_interacao", agora) >= ABANDONO_H * 3600
    return abandono and agora - cfg["zero_desde"] >= MORTE_MIN * 60


def risco(cfg: Dict[str, Any], vida: float, agora: Optional[float]=None) -> Optional[str]:
    """Texto de aviso (ou None) pra mostrar antes da tragédia."""
    if not cfg.get("hardcore") or cfg.get("fantasma") or vida > 2:
        return None
    if cfg.get("zero_desde"):
        falta = MORTE_MIN - int(((agora or time.time()) - cfg["zero_desde"]) / 60)
        return f"HARDCORE: morre em ~{max(0, falta)} min sem carinho!"
    return "HARDCORE: vida baixa! faz carinho (ou joga)"


def lapide(cfg: Dict[str, Any], nome: str, st: Dict[str, Any], agora: Any=None, semente: Optional[int]=None) -> Dict[str, Any]:
    """Monta o registro do Cemitério de Honra a partir do status() do app."""
    agora = agora or time.time()
    rnd = random.Random(semente)
    nasceu = cfg.get("nasceu_em") or agora
    return {"nome": nome, "epitafio": rnd.choice(EPITAFIOS), "nasceu": int(nasceu), "morreu": int(agora),
            "dias": round((agora - nasceu) / 86400, 1), "nivel": st.get("nivel", 1), "xp": st.get("xp", 0),
            "estagio": st.get("estagio", "OVO"), "moeda": st.get("moeda", "BTC"),
            "blocos": (st.get("btc") or {}).get("comidos", 0), "crashes": st.get("crashes", 0),
            "genes": cfg.get("genes") or {}}


def enterrar(cfg: Dict[str, Any], registro: Dict[str, Any]) -> None:
    cfg.setdefault("cemiterio", []).append(registro)
    cfg["cemiterio"] = cfg["cemiterio"][-50:]
    cfg["fantasma"] = True
    cfg.pop("zero_desde", None)
