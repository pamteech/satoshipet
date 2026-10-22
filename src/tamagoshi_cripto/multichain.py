"""multichain.py - carteiras watch-only de ETH e SOL via RPC público SEM CHAVE (só leitura).

Mesmas regras de sempre: endereço PÚBLICO e pronto. Se você colar chave privada, seed,
ou aquele array de bytes do keypair do Solana, o app recusa e dá bronca. Nada é salvo.
"""
import re
from typing import Any, Tuple

import requests

ETH_RPCS = ["https://ethereum-rpc.publicnode.com", "https://cloudflare-eth.com"]
SOL_RPCS = ["https://api.mainnet-beta.solana.com", "https://solana-rpc.publicnode.com"]
UA = {"User-Agent": "TamagoshiCripto/1.4 (+github)"}

RE_ETH = re.compile(r"^0x[0-9a-fA-F]{40}$")
RE_SOL = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
RE_HEX64 = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")          # chave privada ETH
RE_B58_LONGO = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{80,90}$")  # secret key Solana (64 bytes)
BRONCA = "ISSO PARECE CHAVE PRIVADA/SEED! Nunca cole isso em lugar nenhum. Só endereço público."


def _perigo(t: str) -> Any:
    return (RE_HEX64.match(t) or RE_B58_LONGO.match(t) or len(t.split()) >= 12
            or (t.startswith("[") and t.count(",") >= 31))  # keypair.json do solana-keygen


def validar(rede: str, texto: str) -> Tuple[bool, str]:
    """(ok, msg). rede = 'eth' ou 'sol'."""
    t = (texto or "").strip()
    if _perigo(t):
        return False, BRONCA
    if rede == "eth":
        if t.lower().endswith(".eth"):
            return False, "ENS ainda não: cole o endereço 0x... (público)"
        return (True, "ok") if RE_ETH.match(t) else (False, "Endereço ETH inválido (0x + 40 hex)")
    if rede == "sol":
        return (True, "ok") if RE_SOL.match(t) else (False, "Endereço SOL inválido (base58, 32-44 chars)")
    return False, "rede desconhecida"


def _rpc(urls: Any, metodo: str, params: Any, timeout: float = 10) -> Any:
    erro = None
    for url in urls:
        try:
            r = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": metodo, "params": params},
                              timeout=timeout, headers=UA)
            j = r.json()
            if "result" in j:
                return j["result"]
            erro = j.get("error")
        except Exception as e:
            erro = e
    raise RuntimeError(f"nenhum RPC respondeu: {erro}")


def saldo_eth(endereco: str, timeout: int=10) -> float:
    ok, msg = validar("eth", endereco)
    if not ok:
        raise ValueError(msg)
    return int(_rpc(ETH_RPCS, "eth_getBalance", [endereco, "latest"], timeout), 16) / 1e18


def saldo_sol(endereco: str, timeout: int=10) -> float:
    ok, msg = validar("sol", endereco)
    if not ok:
        raise ValueError(msg)
    res = _rpc(SOL_RPCS, "getBalance", [endereco], timeout)
    return (res["value"] if isinstance(res, dict) else res) / 1e9
