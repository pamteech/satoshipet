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
    "menubar_mac": False,
    "unidade": "usd",       # "usd" ou "sats" (moscow time)
    "carteira": "",         # endereço BTC PÚBLICO (watch-only). Nunca chave privada!
    "api": True,            # API local em 127.0.0.1:8737
    "onchain": {},          # blocos comidos (gerenciado pelo app)
    "ranking": False,       # leaderboard é opt-in: só liga com `rank on <apelido>`
    "ranking_url": "",      # ex.: "https://ranking.seu-dominio.com" (servidor em server/)
    "nick": "",
    "device_id": "",        # aleatório (uuid4), gerado só se você ligar o ranking
    "site": "https://OWNER.github.io/tamagoshi-cripto",
    "evolucao": {},
    # v1.3
    "versao_config": 3,
    "nome_pet": "",          # apelido do bicho (onboarding); vazio = nome padrão da moeda
    "onboarding_ok": False,
    "licenca_provedor": "hmac",   # hmac | gumroad | lemonsqueezy | servidor (Hotmart)
    "licenca_produto": "",   # product_id do Gumroad / Lemon Squeezy
    "licenca_url": "",       # servidor de chaves (Hotmart)
    "licenca_cache": {},
    "checar_updates": True,
    "update_ignorado": "",
    "musica": False,         # bgm chiptune (desligada por padrão)
    "volume": 0.35,
    "dia_noite": True,
    "chapeus": True,         # chapéus de época (halloween/natal)
    "alto_contraste": False,
    "juice": True,           # tremidinha e partículas         # xp (gerenciado pelo app)   # ícone na menu bar do Mac (experimental)
}


VERSAO_CONFIG = 3


def migrar(cfg):
    """Leva configs antigas pra versão atual sem perder o bicho. Idempotente."""
    v = int(cfg.get("versao_config") or 1)
    if v < 2:  # v1.0/v1.1 -> v1.2: ranking virou opt-in explícito; nada de nick herdado
        cfg.setdefault("ranking", False)
        if "skin" in cfg and cfg["skin"] == "default":
            cfg["skin"] = "padrao"
    if v < 3:  # v1.2 -> v1.3: quem já usava não precisa ver o onboarding; licença ganha provedor
        if cfg.get("progresso") or cfg.get("evolucao") or cfg.get("licenca"):
            cfg["onboarding_ok"] = True
        if cfg.get("licenca") and not cfg.get("licenca_provedor"):
            cfg["licenca_provedor"] = "hmac"
        try:
            cfg["escala"] = max(1, min(6, int(cfg.get("escala", 3))))
        except (TypeError, ValueError):
            cfg["escala"] = 3
    cfg["versao_config"] = VERSAO_CONFIG
    return cfg


def carregar():
    """Lê o JSON do usuário; se estiver quebrado, recomeça do zero (tipo carteira pós-bear market)."""
    cfg = json.loads(json.dumps(PADRAO))
    try:
        if CONFIG_PATH.exists():
            salvo = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            salvo.setdefault("versao_config", 1)  # sem versão = config de antes da v1.3
            cfg.update(salvo)
    except (OSError, ValueError) as erro:
        print("Config corrompida, resetando:", erro)
    return migrar(cfg)


def salvar(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as erro:
        print("Não deu pra salvar a config:", erro)
