# conquistas.py - vida do bicho e conquistas (lógica pura, sem GUI, fácil de testar)
import time

VIDA_MAX = 10.0  # 10 meios-corações = 5 corações na tela

# id -> (título, descrição)
LISTA = {
    "primeiro_moon": ("Primeiro Moon", "Viu o bicho ir pra lua pela 1ª vez"),
    "sobreviveu_1": ("Batismo de Fogo", "Sobreviveu ao 1º crash"),
    "sobreviveu_3": ("Mão de Diamante", "Sobreviveu a 3 crashes"),
    "hodl_1h": ("Paciência de Monge", "1 hora de HODL com o app aberto"),
    "hodl_24h": ("HODL 24h", "24 horas acumuladas de HODL"),
    "carinho_10": ("Pet Lover", "Fez 10 carinhos no bicho"),
    "coracao_cheio": ("Coração Cheio", "Vida no máximo"),
    "quase_morreu": ("Quase Morreu", "Vida chegou a zero (e ele voltou!)"),
    "konami": ("Satoshi Revelado", "Digitou o código secreto"),
    "halving_nerd": ("Nerd do Halving", "Descobriu a contagem do halving"),
}

# quanto a vida muda por minuto em cada humor
TAXA_MIN = {"moon": +0.5, "garimpando": +0.1, "rekt": -0.3}


def novo_estado():
    return {"vida": 6.0, "crashes": 0, "segundos": 0.0, "carinhos": 0,
            "ultimo_estado": None, "desbloqueadas": {}}


class Conquistas:
    """Guarda o progresso dentro do dicionário de config (cfg["progresso"])."""

    def __init__(self, dados=None, agora=time.time):
        self.d = novo_estado()
        self.d.update(dados or {})
        self.agora = agora

    def _desbloquear(self, cid):
        if cid not in self.d["desbloqueadas"]:
            self.d["desbloqueadas"][cid] = int(self.agora())
            return [cid]
        return []

    def especial(self, cid):
        """Conquistas disparadas por easter eggs."""
        return self._desbloquear(cid)

    def tick(self, estado, segundos, bonus_min=0.0):
        """Chame periodicamente com o humor atual. Retorna conquistas novas."""
        novas = []
        ant = self.d["ultimo_estado"]
        if estado == "rekt" and ant not in (None, "rekt"):
            self.d["crashes"] += 1
        if estado == "moon":
            novas += self._desbloquear("primeiro_moon")
        self.d["ultimo_estado"] = estado
        self.d["segundos"] += segundos
        self.d["vida"] = max(0.0, min(VIDA_MAX, self.d["vida"] + (TAXA_MIN[estado] + bonus_min) * segundos / 60))
        # sobreviveu = saiu do rekt depois de ter caído
        if ant == "rekt" and estado != "rekt":
            if self.d["crashes"] >= 1:
                novas += self._desbloquear("sobreviveu_1")
            if self.d["crashes"] >= 3:
                novas += self._desbloquear("sobreviveu_3")
        if self.d["segundos"] >= 3600:
            novas += self._desbloquear("hodl_1h")
        if self.d["segundos"] >= 86400:
            novas += self._desbloquear("hodl_24h")
        if self.d["vida"] >= VIDA_MAX:
            novas += self._desbloquear("coracao_cheio")
        if self.d["vida"] <= 0:
            novas += self._desbloquear("quase_morreu")
        return novas

    def carinho(self):
        self.d["carinhos"] += 1
        self.d["vida"] = min(VIDA_MAX, self.d["vida"] + 0.2)
        novas = self._desbloquear("carinho_10") if self.d["carinhos"] >= 10 else []
        if self.d["vida"] >= VIDA_MAX:
            novas += self._desbloquear("coracao_cheio")
        return novas

    @property
    def vida(self):
        return self.d["vida"]

    def resumo(self):
        linhas = []
        for cid, (tit, desc) in LISTA.items():
            ok = cid in self.d["desbloqueadas"]
            linhas.append(f"{'[X]' if ok else '[ ]'} {tit} - {desc}")
        n = len(self.d["desbloqueadas"])
        return f"{n}/{len(LISTA)} desbloqueadas\n\n" + "\n".join(linhas)
