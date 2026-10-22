"""acessibilidade.py - v1.7: reduzir movimento, fonte grande e anúncios por voz (opt-in).

Voz: macOS `say`, Windows SAPI (PowerShell, sem janela), Linux `spd-say` se existir; senão nada.
Fala só textos curtos gerados pelo app (humor, preço, alertas) com limite de 1 fala a cada 10 s.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from typing import Callable, List, Optional


def reduzir_movimento_sistema(plataforma: Optional[str] = None) -> bool:
    plataforma = plataforma or sys.platform
    try:
        if plataforma == "darwin":
            r = subprocess.run(["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                               capture_output=True, text=True, timeout=2)
            return r.stdout.strip() == "1"
        if plataforma == "win32":
            import ctypes
            v = ctypes.c_int(1)
            # SPI_GETCLIENTAREAANIMATION = 0x1042: 0 = usuário desligou animações
            if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(v), 0):  # type: ignore[attr-defined]
                return v.value == 0
    except Exception:
        pass
    return False


def comando_voz(texto: str, plataforma: Optional[str] = None) -> Optional[List[str]]:
    plataforma = plataforma or sys.platform
    t = "".join(ch for ch in texto if ch.isalnum() or ch in " .,!?%:+-$")[:140]
    if not t.strip():
        return None
    if plataforma == "darwin":
        return ["say", t]
    if plataforma == "win32":
        seguro = t.replace("'", "")
        return ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command",
                f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{seguro}')"]
    if shutil.which("spd-say"):
        return ["spd-say", t]
    return None


class Locutor:
    def __init__(self, agora: Callable = time.time, intervalo: float = 10,
                 rodar: Callable = lambda cmd: subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)):
        self.agora, self.intervalo, self.rodar = agora, intervalo, rodar
        self.ultimo = -1e9
        self.ultimo_texto = ""

    def falar(self, texto: str, ligado: bool) -> bool:
        if not ligado or not texto or texto == self.ultimo_texto:
            return False
        if self.agora() - self.ultimo < self.intervalo:
            return False
        cmd = comando_voz(texto)
        if not cmd:
            return False
        try:
            self.rodar(cmd)
        except Exception:
            return False
        self.ultimo, self.ultimo_texto = self.agora(), texto
        return True
