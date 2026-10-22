"""energia.py - v1.6: modo economia. Na bateria: menos FPS e rede mais devagar.
Tela bloqueada/dormindo (ou ninguém mexe há muito tempo): pausa animação e quase toda a rede.

Sem dependência nova: macOS = `pmset -g batt` + `ioreg` (HIDIdleTime / tela travada),
Windows = GetSystemPowerStatus + GetLastInputInfo (ctypes), Linux = /sys/class/power_supply.
Qualquer erro = "na tomada, acordado" (melhor gastar um pouco que congelar o bicho).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

AUSENTE_S = 15 * 60  # sem mexer no mouse/teclado por 15 min = tela provavelmente apagada


def _rodar(cmd: list, timeout: float = 3) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def na_bateria(plataforma: str = sys.platform, raiz: Path = Path("/sys/class/power_supply")) -> bool:
    if plataforma == "darwin":
        return "Battery Power" in _rodar(["pmset", "-g", "batt"])
    if plataforma == "win32":
        try:
            import ctypes

            class SPS(ctypes.Structure):
                _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                            ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                            ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
            s = SPS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):  # type: ignore[attr-defined]
                return s.ACLineStatus == 0
        except Exception:
            pass
        return False
    try:
        ac = [p for p in raiz.iterdir() if (p / "type").read_text().strip() == "Mains"]
        if ac:
            return not any((p / "online").read_text().strip() == "1" for p in ac)
        bats = [p for p in raiz.iterdir() if (p / "type").read_text().strip() == "Battery"]
        return any((p / "status").read_text().strip() == "Discharging" for p in bats)
    except OSError:
        return False


def segundos_ocioso(plataforma: str = sys.platform) -> Optional[float]:
    if plataforma == "darwin":
        for ln in _rodar(["ioreg", "-c", "IOHIDSystem", "-d", "4"]).splitlines():
            if '"HIDIdleTime"' in ln:
                try:
                    return int(ln.split("=")[-1].strip()) / 1e9
                except ValueError:
                    return None
        return None
    if plataforma == "win32":
        try:
            import ctypes

            class LII(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            li = LII()
            li.cbSize = ctypes.sizeof(LII)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):  # type: ignore[attr-defined]
                return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000  # type: ignore[attr-defined]
        except Exception:
            pass
        return None
    return None  # Linux: sem jeito universal (X/Wayland); fica só a bateria


def tela_travada(plataforma: str = sys.platform) -> bool:
    if plataforma == "darwin":  # sessão travada aparece no IORegistry
        return "CGSSessionScreenIsLocked" in _rodar(["ioreg", "-n", "Root", "-d1", "-a"])
    return False


def modo(ligado: bool, bateria: bool, ocioso: Optional[float], travada: bool) -> str:
    """'normal' | 'bateria' | 'pausa'."""
    if not ligado:
        return "normal"
    if travada or (ocioso is not None and ocioso >= AUSENTE_S):
        return "pausa"
    return "bateria" if bateria else "normal"


# quanto multiplicar: (intervalo de frame, intervalo de rede)
FATORES = {"normal": (1, 1), "bateria": (2, 2), "pausa": (8, 10)}


def medir(ligado: bool = True) -> str:
    if not ligado:
        return "normal"
    return modo(True, na_bateria(), segundos_ocioso(), tela_travada())
