# conquistas.py - vida do bicho e conquistas (lógica pura, sem GUI, fácil de testar)
import time
from typing import Any, Callable, Dict, Optional

VIDA_MAX = 10.0  # 10 meios-corações = 5 corações na tela

# id -> (título, descrição)
LISTA = {
    "primeiro_moon": ("To the Moon", "Viu o bicho ir pra lua pela 1ª vez"),
    "sobreviveu_1": ("Flash Crash", "Sobreviveu ao 1º crash"),
    "sobreviveu_3": ("Byzantine General", "Sobreviveu a 3 crashes sem trair o HODL"),
    "hodl_1h": ("Proof of Patience", "1 hora de HODL com o app aberto"),
    "hodl_24h": ("Timechain", "24 horas acumuladas de HODL"),
    "carinho_10": ("Pet Lover", "Fez 10 carinhos no bicho"),
    "coracao_cheio": ("Full Node", "Vida no máximo"),
    "quase_morreu": ("Orphan Block", "Vida chegou a zero (e ele voltou!)"),
    "konami": ("Satoshi Revelado", "Digitou o código secreto"),
    "halving_nerd": ("Halvening", "Descobriu a contagem do halving"),
    "genesis": ("Genesis", "Comeu o primeiro bloco"),
    "pow_100": ("Proof of Work", "Comeu 100 blocos"),
    "not_your_keys": ("Not Your Keys", "Configurou uma carteira watch-only (sem chaves!)"),
    "whale_alert": ("Whale Alert", "Evoluiu pra forma Whale"),
    "diamond_hands": ("Diamond Hands", "Evoluiu pra forma Diamond Hands"),
    "sudo": ("sudo make me a lambo", "Usou sudo no console"),
    "rm_rf": ("rm -rf / Survivor", "Tentou apagar a blockchain"),
    "lv21": ("21 Million", "Chegou ao nível 21"),
    "moscow": ("Moscow Time", "Passou a contar em sats"),
    "stacker": ("Stacking Sats", "Pegou 25 sats no mini-game"),
}

# quanto a vida muda por minuto em cada humor
TAXA_MIN = {"moon": +0.5, "garimpando": +0.1, "rekt": -0.3}


def novo_estado() -> Dict[str, Any]:
    return {"vida": 6.0, "crashes": 0, "segundos": 0.0, "carinhos": 0,
            "ultimo_estado": None, "desbloqueadas": {}}


class Conquistas:
    """Guarda o progresso dentro do dicionário de config (cfg["progresso"])."""

    def __init__(self, dados: Optional[Dict[str, Any]]=None, agora: Callable=time.time):
        self.d = novo_estado()
        self.d.update(dados or {})
        self.agora = agora

    def _desbloquear(self, cid: str) -> Any:
        if cid not in self.d["desbloqueadas"]:
            self.d["desbloqueadas"][cid] = int(self.agora())
            return [cid]
        return []

    def especial(self, cid: str) -> Any:
        """Conquistas disparadas por easter eggs."""
        return self._desbloquear(cid)

    def tick(self, estado: str, segundos: int, bonus_min: float=0.0) -> Any:
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

    def carinho(self) -> Any:
        self.d["carinhos"] += 1
        self.d["vida"] = min(VIDA_MAX, self.d["vida"] + 0.2)
        novas = self._desbloquear("carinho_10") if self.d["carinhos"] >= 10 else []
        if self.d["vida"] >= VIDA_MAX:
            novas += self._desbloquear("coracao_cheio")
        return novas

    @property
    def vida(self) -> float:
        return self.d["vida"]

    def resumo(self) -> str:
        linhas = []
        for cid, (tit, desc) in LISTA.items():
            ok = cid in self.d["desbloqueadas"]
            linhas.append(f"{'[X]' if ok else '[ ]'} {tit} - {desc}")
        n = len(self.d["desbloqueadas"])
        return f"{n}/{len(LISTA)} desbloqueadas\n\n" + "\n".join(linhas)
