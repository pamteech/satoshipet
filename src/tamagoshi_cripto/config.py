# config.py - a memória do bicho (porque trader esquece tudo depois do primeiro dump)
import json
import os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get("TAMAGOSHI_CONFIG", Path.home() / ".tamagoshi_cripto.json"))

API_URL = "https://api.coingecko.com/api/v3/simple/price"
INTERVALO = 30  # segundos: CoinGecko grátis odeia quem fica dando F5
LINK_AFILIADO = "https://SEU-LINK-DE-AFILIADO-AQUI"  # o seu ganha-pão mora aqui

# símbolo -> id do CoinGecko
MOEDAS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "PEPE": "pepe",
}

PADRAO = {
    "moeda": "BTC",
    "skin": "padrao",
    "limite_alta": 2.0,     # acima disso: TO THE MOON
    "limite_queda": -2.0,   # abaixo disso: REKT
    "preco_referencia": {}, # {"BTC": 65000.0}; vazio = usa o primeiro preço visto
    "alertas": {},          # {"BTC": {"acima": 70000, "abaixo": 60000}}
    "email": "",
    "licenca": "",
    "posicao": [100, 100],
    "escala": 3,            # 48px x 3 = 144px de bicho
    "crt": False,           # scanlines estilo tubo
    "mudo": False,
    "segredos": [],         # easter eggs destravados (ex.: "satoshi")
    "menubar_mac": False,   # ícone na menu bar do Mac (experimental)
}


def carregar():
    """Lê o JSON do usuário; se estiver quebrado, recomeça do zero (tipo carteira pós-bear market)."""
    cfg = json.loads(json.dumps(PADRAO))
    try:
        if CONFIG_PATH.exists():
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError) as erro:
        print("Config corrompida, resetando:", erro)
    return cfg


def salvar(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as erro:
        print("Não deu pra salvar a config:", erro)
