"""batalha.py - batalha por turnos entre pets. Stats saem do nível, estágio, genes e da variação 24h da moeda.

Lógica 100% determinística dada a semente (pra dar pra testar e pra repetir replay). Sem aposta, sem prêmio
em dinheiro: o vencedor ganha XP e moral.
"""
import random
from typing import Any, Dict, Optional, Tuple

from . import genetica

BONUS_ESTAGIO = {"ovo": 0, "bebe": 5, "adulto": 12, "whale": 22, "diamond": 20}
GOLPES = {
    "PUMP": "ataque básico",
    "HODL": "defende (metade do dano) e cura um pouco",
    "FUD": "espalha FUD: ataque do rival -25% por 2 turnos",
    "LASER EYES": "especial (olhos laser): 1.7x, recarga 3",
    "TO THE MOON": "especial: 1.6x, 30% de errar, recarga 3",
}


def stats(pet: Dict[str, Any], var24h: float=0.0) -> Dict[str, Any]:
    """pet = {"nome", "nivel", "estagio", "genes"}; var24h em % (positivo = moeda subindo = mais força)."""
    lv = max(1, int(pet.get("nivel", 1)))
    g = pet.get("genes") or {}
    _, pts = genetica.raridade(g)
    v = max(-10.0, min(10.0, float(var24h or 0)))
    est = BONUS_ESTAGIO.get(pet.get("estagio", "adulto"), 10)
    s: Dict[str, Any] = {"hp": 30 + lv * 2 + est + pts * 2,
         "atk": 8 + lv * 0.8 + est * 0.3 + pts + v * 0.5 + (3 if g.get("olhos") == "laser" else 0),
         "def": 6 + lv * 0.6 + est * 0.3 + (4 if pet.get("estagio") == "diamond" else 0)
                + (2 if g.get("paleta") == "noir" else 0),
         "spd": 5 + lv * 0.3 + v * 0.3 + (2 if g.get("acessorio") == "antena" else 0)}
    s["max_hp"] = s["hp"] = int(s["hp"])
    s["especial"] = "LASER EYES" if g.get("olhos") == "laser" else "TO THE MOON"
    return s


class Lutador:
    def __init__(self, pet: Dict[str, Any], var24h: float=0.0):
        self.pet, self.nome = pet, pet.get("nome", "anon")[:12]
        self.s = stats(pet, var24h)
        self.hp, self.recarga, self.fud, self.defendendo = self.s["hp"], 0, 0, False

    @property
    def vivo(self) -> bool:
        return self.hp > 0


def escolher_ia(eu: Lutador, rival: Lutador, rnd: random.Random) -> str:
    if eu.recarga == 0 and rnd.random() < .6:
        return eu.s["especial"]
    if eu.hp < eu.s["max_hp"] * .3 and rnd.random() < .5:
        return "HODL"
    if rival.fud == 0 and rnd.random() < .25:
        return "FUD"
    return "PUMP"


def _golpe(at: Lutador, df: Lutador, golpe: str, rnd: random.Random) -> Tuple[int, str]:
    """Aplica o golpe. Retorna (dano, texto)."""
    if at.recarga:
        at.recarga -= 1
    if golpe == "HODL":
        at.defendendo = True
        cura = max(1, at.s["max_hp"] // 12)
        at.hp = min(at.s["max_hp"], at.hp + cura)
        return 0, f"{at.nome}: HODL! +{cura} HP"
    if golpe == "FUD":
        df.fud = 2
        return 0, f"{at.nome} espalhou FUD! -25% atk"
    mult = 1.0
    if golpe in ("LASER EYES", "TO THE MOON"):
        if at.recarga:
            golpe, mult = "PUMP", 1.0
        else:
            at.recarga = 3
            mult = 1.7 if golpe == "LASER EYES" else 1.6
            if golpe == "TO THE MOON" and rnd.random() < .3:
                return 0, f"{at.nome} errou o MOON (rug!)"
    atk = at.s["atk"] * (0.75 if at.fud else 1)
    critico = rnd.random() < .1
    dano = max(1, int((atk * rnd.uniform(.85, 1.15) * mult - df.s["def"] * .45) * (1.5 if critico else 1)))
    if df.defendendo:
        dano = max(1, dano // 2)
    df.hp = max(0, df.hp - dano)
    return dano, f"{at.nome}: {golpe} -{dano}" + (" CRIT!" if critico else "")


def simular(pet_a: Dict[str, Any], pet_b: Dict[str, Any], var_a: float = 0.0, var_b: float = 0.0,
            semente: Optional[int] = None, escolher_a: Any = None, max_turnos: int = 40) -> Dict[str, Any]:
    """Roda a luta inteira. escolher_a(eu, rival, rnd) -> golpe (None = IA). Retorna dict com log e vencedor."""
    rnd = random.Random(semente)
    a, b = Lutador(pet_a, var_a), Lutador(pet_b, var_b)
    ordem = [a, b] if (a.s["spd"], rnd.random()) >= (b.s["spd"], rnd.random()) else [b, a]
    log = []
    for turno in range(1, max_turnos + 1):
        for at in ordem:
            df = b if at is a else a
            if not (at.vivo and df.vivo):
                break
            at.defendendo = False
            escolha = (escolher_a or escolher_ia)(at, df, rnd) if at is a else escolher_ia(at, df, rnd)
            dano, txt = _golpe(at, df, escolha, rnd)
            if at.fud and escolha not in ("FUD",):
                at.fud = max(0, at.fud - 1)
            log.append({"turno": turno, "quem": "a" if at is a else "b", "golpe": escolha, "dano": dano,
                        "texto": txt, "hp_a": a.hp, "hp_b": b.hp})
        if not (a.vivo and b.vivo):
            break
    venc = "a" if a.hp > b.hp else "b" if b.hp > a.hp else "empate"
    return {"log": log, "vencedor": venc, "a": a, "b": b,
            "xp": 40 if venc == "a" else 10, "max_hp": (a.s["max_hp"], b.s["max_hp"])}


def rival_ia(nivel: int, semente: Optional[int]=None, moeda: str="BTC") -> Dict[str, Any]:
    rnd = random.Random(semente)
    nomes = ["Bot Bear", "Rug Puller", "Paper Hand", "Shitcoin Sam", "Gas Goblin", "FUD Bot", "Exit Liquidity"]
    lv = max(1, nivel + rnd.randint(-2, 2))
    est = "bebe" if lv < 4 else "adulto" if lv < 15 else rnd.choice(["whale", "diamond"])
    return {"nome": rnd.choice(nomes), "nivel": lv, "estagio": est, "genes": genetica.aleatorio(rnd.random(), moeda)}
