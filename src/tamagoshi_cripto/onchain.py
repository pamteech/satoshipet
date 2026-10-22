"""onchain.py - o bicho vive na blockchain: come blocos, sente fome de fee, dorme sem bloco.

Fontes (todas grátis e SEM chave):
  - mempool.space: blocos, fees, mempool, hashrate, endereços (watch-only)
  - ethereum-rpc.publicnode.com (fallback cloudflare-eth.com): eth_gasPrice via JSON-RPC público
Tudo aqui é só leitura. Offline? As funções levantam exceção e o app segue sem os dados.
"""
import re
import time

import requests

MEMPOOL = "https://mempool.space/api"
ETH_RPCS = ["https://ethereum-rpc.publicnode.com", "https://cloudflare-eth.com"]
SONO_SEG = 30 * 60   # 30 min sem bloco = hora da soneca
UA = {"User-Agent": "TamagoshiCripto/1.1 (+github)"}


def _get(caminho, timeout=10):
    r = requests.get(MEMPOOL + caminho, timeout=timeout, headers=UA)
    r.raise_for_status()
    return r.json()


def ultimo_bloco(timeout=10):
    """(altura, timestamp unix) do bloco mais recente."""
    b = _get("/v1/blocks", timeout)[0]
    return int(b["height"]), int(b["timestamp"])


def fees(timeout=10):
    """{'fastestFee', 'halfHourFee', 'hourFee', 'economyFee', 'minimumFee'} em sat/vB."""
    return _get("/v1/fees/recommended", timeout)


def mempool(timeout=10):
    d = _get("/mempool", timeout)
    return {"count": d["count"], "vsize": d["vsize"]}


def hashrate(timeout=10):
    """Hashrate atual da rede em H/s."""
    return float(_get("/v1/mining/hashrate/3d", timeout)["currentHashrate"])


def formatar_hashrate(hs):
    for unidade, div in (("ZH/s", 1e21), ("EH/s", 1e18), ("PH/s", 1e15), ("TH/s", 1e12)):
        if hs >= div:
            return f"{hs / div:.1f} {unidade}" if unidade != "ZH/s" else f"{hs / 1e18:,.0f} EH/s"
    return f"{hs:.0f} H/s"


def gas_eth(timeout=8):
    """Gas price em gwei via RPC público. Tenta cada RPC até um responder."""
    erro = None
    for url in ETH_RPCS:
        try:
            r = requests.post(url, json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
                              timeout=timeout, headers=UA)
            res = r.json().get("result")
            if res:
                return int(res, 16) / 1e9
        except Exception as e:  # próximo RPC
            erro = e
    raise RuntimeError(f"nenhum RPC respondeu: {erro}")


# ---------------- fome & sono (lógica pura) ----------------
def fome_por_fee(sat_vb):
    """(nível 0..3, rótulo). Fee alta = rede congestionada = bicho faminto e suando."""
    if sat_vb is None:
        return 0, "?"
    if sat_vb <= 5:
        return 0, "SACIADO"
    if sat_vb <= 20:
        return 1, "BELISCANDO"
    if sat_vb <= 60:
        return 2, "FAMINTO"
    return 3, "MORRENDO DE FOME"


def humor_gas(gwei):
    if gwei is None:
        return None
    if gwei < 5:
        return "gas baratinho, bora mintar"
    if gwei < 30:
        return f"gas a {gwei:.0f} gwei, tolerável"
    return f"gas a {gwei:.0f} gwei: chapéu derretendo"


class Estomago:
    """Conta blocos comidos. Primeiro tip visto só calibra (ninguém come bloco velho)."""

    def __init__(self, dados=None):
        self.d = {"altura": None, "comidos": 0, "ts_bloco": None}
        self.d.update(dados or {})

    def novo_tip(self, altura, ts_bloco):
        """Retorna a lista de alturas comidas agora (no máx. 6 de uma vez)."""
        ant = self.d["altura"]
        self.d["ts_bloco"] = ts_bloco
        if ant is None or altura <= ant:
            self.d["altura"] = max(altura, ant or 0)
            return []
        comidos = list(range(max(ant + 1, altura - 5), altura + 1))
        self.d["altura"] = altura
        self.d["comidos"] += len(comidos)
        return comidos

    def dormindo(self, agora=None):
        ts = self.d.get("ts_bloco")
        return bool(ts) and (agora or time.time()) - ts > SONO_SEG

    @property
    def comidos(self):
        return self.d["comidos"]


# ---------------- carteira watch-only ----------------
RE_ENDERECO = re.compile(r"^(bc1[02-9ac-hj-np-z]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")
RE_PERIGO = re.compile(r"^([xyzt]prv|[5KLc][1-9A-HJ-NP-Za-km-z]{50,51}$)")


def validar_endereco(texto):
    """(ok, mensagem). Recusa (e grita) se parecer chave privada."""
    t = (texto or "").strip()
    if RE_PERIGO.match(t) or len(t.split()) >= 12:
        return False, "ISSO PARECE CHAVE PRIVADA/SEED! Nunca cole isso em lugar nenhum. Só endereço público."
    if t.lower().startswith(("xpub", "ypub", "zpub")):
        return False, "xpub não é suportado (ainda). Cole um endereço bc1/1/3."
    if not RE_ENDERECO.match(t if not t.lower().startswith("bc1") else t.lower()):
        return False, "Endereço BTC inválido (aceito bc1..., 1..., 3...)."
    return True, "ok"


def saldo_endereco(endereco, timeout=10):
    """Saldo em sats (confirmado + mempool) e nº de tx, só leitura."""
    d = _get(f"/address/{endereco}", timeout)
    c, m = d["chain_stats"], d["mempool_stats"]
    conf = c["funded_txo_sum"] - c["spent_txo_sum"]
    pend = m["funded_txo_sum"] - m["spent_txo_sum"]
    return {"confirmado": conf, "pendente": pend, "total": conf + pend,
            "txs": c["tx_count"] + m["tx_count"]}


class Vigia:
    """Detecta variação de saldo entre consultas."""

    def __init__(self):
        self.ultimo = None

    def atualizar(self, saldo_total):
        """Retorna delta em sats (0 na primeira leitura ou sem mudança)."""
        if self.ultimo is None:
            self.ultimo = saldo_total
            return 0
        delta = saldo_total - self.ultimo
        self.ultimo = saldo_total
        return delta


def sats_por_dolar(preco_btc):
    """Moscow time: quantos sats 1 dólar compra."""
    return round(1e8 / preco_btc) if preco_btc else None
