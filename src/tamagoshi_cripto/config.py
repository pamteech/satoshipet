# config.py - a memória do bicho (porque trader esquece tudo depois do primeiro dump)
import json
import os
from pathlib import Path
from typing import Any, Dict

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
    "site": "https://pamteech.github.io/tamagoshi-cripto",
    "evolucao": {},
    # v1.3
    "versao_config": 4,
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
    "juice": True,           # tremidinha e partículas
    "api_escrita": False,    # v1.5: POST /pet e /feed (com token). Desligado por padrão
    "idioma": "auto",        # v1.5: auto (segue o sistema) | pt | en
    # v1.4
    "hardcore": False,       # opt-in: o bicho pode MORRER de abandono (vai pro Cemitério de Honra)
    "fantasma": False,
    "cemiterio": [],
    "ultima_interacao": 0,
    "nasceu_em": 0,
    "genes": {},             # DNA do bicho atual (genetica.py)
    "estabulo": [],          # pets guardados / importados de amigos (código TAMA1-...)
    "batalhas": {"vitorias": 0, "derrotas": 0},
    "papel": {},             # paper trading: dinheiro FICTÍCIO
    "carteira_eth": "",      # endereço PÚBLICO (watch-only)
    "carteira_sol": "",      # endereço PÚBLICO (watch-only)
    "saldo_fiat": "auto",    # v1.6: auto (R$ em pt, US$ no resto) | brl | usd
    "economia": True,        # v1.6: bateria = menos FPS; tela travada = pausa
    "clima": "off",          # v1.7: off | cidade | auto (auto = geolocalização por IP, só se você escolher)
    "clima_cidade": "",
    "clima_lat": None,       # arredondado em 2 casas (~1 km)
    "clima_lon": None,
    "amigos_lan": False,     # v1.7: opt-in. Só nome/espécie/skin/humor do bicho na rede local
    "reduzir_movimento": False,
    "fonte_grande": False,
    "voz": False,            # v1.7: anúncios por voz (say / SAPI / spd-say)
    "saldo_oculto": False,   # v1.6: True = mostra •••• (modo gravação). O SALDO em si nunca vai pro disco.
    "baleias": True,         # alerta de baleia (mempool.space, sem chave)
    "baleia_btc": 50,        # tx acima de X BTC = susto
    "noticias": True,        # manchete RSS de vez em quando no balão
    "ai_url": "",            # BYO: endpoint OpenAI-compatível (vazio = desligado, respostas enlatadas)
    "ai_key": "",
    "ai_modelo": "gpt-4o-mini",
    "loja_codigos": [],      # códigos de pacotes de skin resgatados
    "twitch_canal": "",      # overlay: lê o chat anônimo (vazio = desligado)
}


VERSAO_CONFIG = 4


def migrar(cfg: Dict[str, Any]) -> Dict[str, Any]:
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
    if v < 4:  # v1.3 -> v1.4: todo bicho ganha DNA (quem já existe nasce "hoje" pro cemitério)
        if not cfg.get("genes"):
            from . import genetica
            cfg["genes"] = genetica.aleatorio(moeda=cfg.get("moeda", "BTC"))
        if not cfg.get("nasceu_em"):
            import time
            cfg["nasceu_em"] = int(time.time())
    cfg["versao_config"] = VERSAO_CONFIG
    return cfg


def carregar() -> Dict[str, Any]:
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


def salvar(cfg: Dict[str, Any]) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as erro:
        print("Não deu pra salvar a config:", erro)
