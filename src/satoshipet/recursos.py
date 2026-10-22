"""recursos.py - acha os assets (no pacote, no .exe/.app do PyInstaller ou no pipx)."""
import sys
from pathlib import Path

_BASE = Path(getattr(sys, "_MEIPASS", "")) / "satoshipet" if hasattr(sys, "_MEIPASS") else Path(__file__).parent
ASSETS = _BASE / "assets"


def sheet_path(moeda, skin):
    return ASSETS / "sprites" / f"{moeda}_{skin}.png"
