"""segredos.py - onde mora a chave da IA BYO: no chaveiro do sistema (Keychain/Credential Manager/Secret Service).

Sem `keyring` instalado (ou num Linux sem chaveiro), cai pro config local como antes, avisando no console.
A chave NUNCA vai pro /status, pro card, pro log de erro nem pro histórico do console.
"""
from __future__ import annotations

import os
from typing import Any

SERVICO = "satoshipet"
CONTA = "ai_key"


def _kr() -> Any:
    try:
        import keyring
        from keyring.errors import KeyringError  # noqa: F401
        if "fail" in type(keyring.get_keyring()).__name__.lower():  # backend "fail" = sem chaveiro de verdade
            return None
        return keyring
    except Exception:
        return None


def onde() -> str:
    return "chaveiro do sistema" if _kr() else "config local (instale 'keyring' pra usar o chaveiro)"


def ler(cfg: dict) -> str:
    kr = _kr()
    if kr:
        try:
            v = kr.get_password(SERVICO, CONTA)
            if v:
                return v
            from . import migracao  # chave salva no chaveiro com o nome antigo? traz pro novo
            v = migracao.migrar_chaveiro(kr, SERVICO, CONTA)
            if v:
                return v
        except Exception:
            pass
    return cfg.get("ai_key") or os.environ.get("SATOSHIPET_AI_KEY") or os.environ.get("TAMAGOSHI_AI_KEY", "")


def gravar(cfg: dict, chave: str) -> str:
    """Guarda (ou apaga, se vazio). Devolve onde ficou."""
    kr = _kr()
    if kr:
        try:
            if chave:
                kr.set_password(SERVICO, CONTA, chave)
            else:
                try:
                    kr.delete_password(SERVICO, CONTA)
                except Exception:
                    pass
            cfg["ai_key"] = ""
            return "chaveiro do sistema"
        except Exception:
            pass
    cfg["ai_key"] = chave
    return "config local"


def migrar(cfg: dict) -> bool:
    """Chave antiga no JSON? Muda pro chaveiro (se der). True = migrou."""
    if cfg.get("ai_key") and _kr():
        chave = cfg["ai_key"]
        return gravar(cfg, chave) == "chaveiro do sistema"
    return False
