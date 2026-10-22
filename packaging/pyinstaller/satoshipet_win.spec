# -*- mode: python -*-
# PyInstaller spec do Windows:  pyinstaller packaging\pyinstaller\satoshipet_win.spec
# Gera dist\SatoshiPet.exe (onefile, sem console). Não assinado: o SmartScreen vai reclamar na 1ª vez.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))  # noqa: F821
from _comum import ASSETS, EXCLUIR, RAIZ, SRC  # noqa: E402

from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

extra = ["pystray._win32", "keyring.backends.Windows"] if sys.platform == "win32" else []
a = Analysis([str(RAIZ / "tools" / "run_app.py")], pathex=[str(SRC)], datas=[ASSETS],  # noqa: F821
             hiddenimports=collect_submodules("satoshipet") + extra, excludes=EXCLUIR)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="SatoshiPet", console=False,  # noqa: F821
          icon=str(SRC / "satoshipet" / "assets" / "icone.ico"), upx=False, strip=False,
          version=None)
