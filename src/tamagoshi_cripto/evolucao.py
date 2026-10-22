"""evolucao.py - XP, níveis e estágios: ovo -> bebê -> adulto -> Whale ou Diamond Hands."""
import math

XP = {"bloco": 25, "minuto": 1, "crash": 50, "carinho": 2, "jogo": 1}
ESTAGIOS = [("ovo", 0), ("bebe", 100), ("adulto", 500), ("final", 2000)]
NOMES = {"ovo": "OVO", "bebe": "BEBE", "adulto": "ADULTO", "whale": "WHALE", "diamond": "DIAMOND HANDS"}


def nivel(xp):
    return int(math.sqrt(max(0, xp) / 10)) + 1


def xp_do_nivel(n):
    return (n - 1) ** 2 * 10


def progresso_nivel(xp):
    """0..1 dentro do nível atual."""
    n = nivel(xp)
    a, b = xp_do_nivel(n), xp_do_nivel(n + 1)
    return (xp - a) / (b - a)


def estagio(xp, crashes=0):
    """Forma final: 3+ crashes sobrevividos = Diamond Hands; senão, Whale."""
    atual = "ovo"
    for nome, minimo in ESTAGIOS:
        if xp >= minimo:
            atual = nome
    if atual == "final":
        return "diamond" if crashes >= 3 else "whale"
    return atual


def proximo_estagio(xp):
    for nome, minimo in ESTAGIOS:
        if xp < minimo:
            return nome, minimo
    return None, None


class Evolucao:
    def __init__(self, dados=None):
        self.d = {"xp": 0, "minutos_frac": 0.0}
        self.d.update(dados or {})

    def ganhar(self, motivo, qtd=1):
        """Soma XP. Retorna (subiu_nivel, novo_estagio_ou_None, crashes não usado)."""
        antes_n = nivel(self.d["xp"])
        self.d["xp"] += XP[motivo] * qtd
        return nivel(self.d["xp"]) > antes_n

    def tick_minutos(self, segundos):
        self.d["minutos_frac"] += segundos / 60
        inteiros = int(self.d["minutos_frac"])
        self.d["minutos_frac"] -= inteiros
        return self.ganhar("minuto", inteiros) if inteiros else False

    @property
    def xp(self):
        return self.d["xp"]
