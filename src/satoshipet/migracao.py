"""migracao.py - o bicho mudou de nome (agora é SatoshiPet), mas não mudou de dono.

Na primeira vez que o SatoshiPet abre, a gente COPIA (nunca move, nunca apaga) o que o app antigo deixou:
  ~/.tamagoshi_cripto.json   -> ~/.satoshipet.json       (config + save do pet)
  ~/.tamagoshi_cripto/       -> ~/.satoshipet/           (skins, loja, crash logs, cemitério...)
  ~/.tamagoshi_api_token     -> ~/.satoshipet_api_token  (token da API local, 0600)
Só copia se o destino ainda NÃO existe: depois da 1ª vez, o novo manda. O antigo fica lá de backup.
Também: chave da IA no chaveiro (serviço antigo -> novo) e o "iniciar com o sistema" antigo vira o novo.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional

ANTIGO_CONFIG = ".tamagoshi_cripto.json"
ANTIGA_PASTA = ".tamagoshi_cripto"
ANTIGO_TOKEN = ".tamagoshi_api_token"
NOVO_CONFIG = ".satoshipet.json"
NOVA_PASTA = ".satoshipet"
NOVO_TOKEN = ".satoshipet_api_token"
SERVICO_ANTIGO = "tamagoshi-cripto"   # chaveiro (keyring) da v1.6 pra trás
LABEL_MAC_ANTIGO = "com.tamagoshi.cripto"
NOME_RUN_ANTIGO = "TamagoshiCripto"
_feito = False


def env(nome: str, padrao: Optional[str] = None) -> Optional[str]:
    """SATOSHIPET_X, ou o velho TAMAGOSHI_X (pra script antigo não quebrar)."""
    return os.environ.get(f"SATOSHIPET_{nome}") or os.environ.get(f"TAMAGOSHI_{nome}") or padrao


def _copiar(origem: Path, destino: Path) -> bool:
    if destino.exists() or not origem.exists():
        return False
    try:
        if origem.is_dir():
            shutil.copytree(origem, destino)
        else:
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
        return True
    except OSError as e:  # sem permissão? segue a vida com config nova
        print("Migração do nome antigo falhou:", e)
        return False


def migrar_arquivos(home: Optional[Path] = None, config_destino: Optional[Path] = None) -> List[str]:
    """Copia o que existir do Tamagoshi Cripto antigo. Devolve a lista do que foi copiado."""
    h = Path(home) if home else Path.home()
    feitos = []
    pares = [(h / ANTIGO_CONFIG, Path(config_destino) if config_destino else h / NOVO_CONFIG),
             (h / ANTIGA_PASTA, h / NOVA_PASTA), (h / ANTIGO_TOKEN, h / NOVO_TOKEN)]
    for a, b in pares:
        if _copiar(a, b):
            feitos.append(b.name)
    return feitos


def migrar_chaveiro(kr, novo_servico: str, conta: str) -> Optional[str]:
    """Chave da IA no serviço antigo do chaveiro? Copia pro novo e devolve."""
    try:
        v = kr.get_password(SERVICO_ANTIGO, conta)
        if v:
            kr.set_password(novo_servico, conta, v)
        return v or None
    except Exception:
        return None


def migrar_autostart(ativo_antigo: Callable[[], bool], apagar_antigo: Callable[[], None],
                     ligar_novo: Callable[[], object]) -> bool:
    """Se o app antigo iniciava com o sistema, troca pelo SatoshiPet (sem deixar 2 bichos no login)."""
    try:
        if not ativo_antigo():
            return False
        apagar_antigo()
        ligar_novo()
        return True
    except Exception:
        return False


def rodar_uma_vez(config_destino: Path) -> List[str]:
    """Chamada no carregar() da config. Idempotente e barata (só uns exists())."""
    global _feito
    if _feito:
        return []
    _feito = True
    feitos = migrar_arquivos(config_destino=config_destino)
    try:
        from . import sistema
        if sistema.migrar_autostart_antigo():
            feitos.append("autostart")
    except Exception:
        pass
    return feitos
