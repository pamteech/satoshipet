"""baleias.py - alerta de baleia: tx gigante de BTC na mempool (mempool.space, sem chave) = bicho assustado."""
import requests

URL = "https://mempool.space/api/mempool/recent"
UA = {"User-Agent": "TamagoshiCripto/1.4 (+github)"}


def recentes(timeout=10):
    r = requests.get(URL, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.json()


class Radar:
    """Guarda txids já vistos pra não gritar duas vezes pela mesma baleia."""

    def __init__(self, limite_btc=50):
        self.limite = float(limite_btc)
        self.vistos = set()
        self.primeira = True

    def filtrar(self, txs):
        """Retorna baleias novas: [{"txid", "btc", "url"}], maiores primeiro."""
        novas = []
        for tx in txs or []:
            tid, val = tx.get("txid"), tx.get("value", 0)
            if not tid or tid in self.vistos:
                continue
            self.vistos.add(tid)
            if val >= self.limite * 1e8:
                novas.append({"txid": tid, "btc": val / 1e8, "url": f"https://mempool.space/tx/{tid}"})
        if len(self.vistos) > 5000:
            self.vistos = set(list(self.vistos)[-1000:])
        return sorted(novas, key=lambda b: -b["btc"])


def frase(b):
    return f"BALEIA! {b['btc']:,.0f} BTC se mexeu".replace(",", ".")
