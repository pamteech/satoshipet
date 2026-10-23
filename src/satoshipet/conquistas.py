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
    # v1.7: conquistas de mercado
    "crash_10": ("Survivor -10%", "Sobreviveu a uma queda de 10% em 24h"),
    "ath_vivo": ("ATH ao vivo", "Viu um All-Time High acontecer com o app aberto"),
    "hodl_30d": ("HODL 30 dias", "30 dias com o mesmo bicho"),
    "baleia_cedo": ("Acordou com baleia", "Alerta de baleia nos 10 min depois de abrir o app"),
    "bloco_halving": ("Bloco do Halving", "Comeu o bloco do halving"),
    "medo_extremo": ("Medo Extremo", "Viu o Fear & Greed em medo extremo (<= 20)"),
    # v1.8: aniversários
    "aniv_semana": ("Primeira Semana", "O bicho fez 1 semana"),
    "aniv_mes": ("Mesversário", "O bicho fez 1 mês"),
    "aniv_100d": ("100 Blocos de Dias", "O bicho fez 100 dias"),
    "aniv_ano": ("1 Ano de HODL", "O bicho fez 1 ano"),
    "ath_festa": ("Festa do ATH", "Comemorou um novo All-Time High do BTC"),
}

# v1.7: medalhas 8x8 (pixel). "1" = cor da medalha, "2" = brilho
BADGES = {
    "crash_10": ("#b13e53", ["...11...", "..1221..", ".122221.", "11222211", "...22...", "...22...", "..2222..", "...22..."]),
    "ath_vivo": ("#38b764", ["...11...", "..1111..", ".111111.", "11122111", "...22...", "...22...", "...22...", "...22..."]),
    "hodl_30d": ("#73eff7", ["11111111", "12222221", "11111111", "12121211", "11212121", "12121211", "11111111", "........"]),
    "baleia_cedo": ("#41a6f6", ["........", "...1...1", "..11..11", ".1111111", "11211111", "11111111", ".111111.", "........"]),
    "bloco_halving": ("#ef7d57",
                      [".111111.", "11222211", "12211221", "12122121", "12211221", "12222221", "11222211", ".111111."]),
    "medo_extremo": ("#5d275d", [".111111.", "11111111", "11211211", "11111111", "11122111", "11211211", "11111111", ".1.11.1."]),
}
_BOLO8 = ["...22...", "...1....", ".111111.", ".122221.", ".111111.", ".122221.", "11111111", "........"]
BADGES["aniv_semana"] = ("#41a6f6", _BOLO8)
BADGES["aniv_mes"] = ("#ef7d57", _BOLO8)
BADGES["aniv_100d"] = ("#a7f070", _BOLO8)
BADGES["aniv_ano"] = ("#ffcd75", _BOLO8)
BADGES["ath_festa"] = ("#ffcd75",
                       ["1..1..1.", ".1.1.1..", "..111...", "1111111.", "..111...", ".1.1.1..", "1..1..1.", "........"])
BADGE_PADRAO = ("#ffcd75", ["..1111..", ".122221.", "12211221", "12122121", "12211221", ".122221.", "..1111..", ".11..11."])


class Mercado:
    """Rastreador PURO das conquistas de mercado (amostras de preço ficam só na memória)."""

    JANELA = 24 * 3600

    def __init__(self, agora: Callable = time.time):
        self.agora = agora
        self.amostras: Dict[str, list] = {}   # moeda -> [(t, preço)]
        self.ath: Dict[str, float] = {}       # moeda -> ATH conhecido (CoinGecko)
        self.inicio = agora()

    def preco(self, moeda: str, p: float) -> list:
        t = self.agora()
        a = self.amostras.setdefault(moeda, [])
        if not a or t - a[-1][0] >= 60:
            a.append((t, p))
        while a and t - a[0][0] > self.JANELA:
            a.pop(0)
        novas = []
        topo = max(x for _, x in a)
        if topo > 0 and p <= topo * 0.9:
            novas.append("crash_10")
        ath = self.ath.get(moeda)
        if ath and p > ath:
            novas.append("ath_vivo")
            self.ath[moeda] = p
        return novas

    def baleia(self) -> list:
        return ["baleia_cedo"] if self.agora() - self.inicio <= 600 else []

    @staticmethod
    def bloco(altura: int) -> list:
        return ["bloco_halving"] if altura and altura % 210_000 == 0 else []

    @staticmethod
    def fng(valor: Optional[int]) -> list:
        return ["medo_extremo"] if valor is not None and valor <= 20 else []

    def hodl(self, nasceu_em: float) -> list:
        return ["hodl_30d"] if nasceu_em and self.agora() - nasceu_em >= 30 * 86400 else []

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
