# -*- mode: python -*-
# PyInstaller spec do macOS:  pyinstaller packaging/pyinstaller/satoshipet_mac.spec
# Gera dist/SatoshiPet.app (widget sem ícone no Dock: LSUIElement). Ícone: rode antes o
# trecho do tools/build_mac.sh que cria build/SatoshiPet.icns (sips/iconutil). Não assinado/notarizado.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))  # noqa: F821
from _comum import ASSETS, EXCLUIR, RAIZ, SRC  # noqa: E402

from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

icns = RAIZ / "build" / "SatoshiPet.icns"
a = Analysis([str(RAIZ / "tools" / "run_app.py")], pathex=[str(SRC)], datas=[ASSETS],  # noqa: F821
             hiddenimports=collect_submodules("satoshipet") + ["pystray._darwin", "keyring.backends.macOS"],
             excludes=EXCLUIR, noarchive=False)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="SatoshiPet", console=False, strip=True,  # noqa: F821
          upx=False, target_arch=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=True, upx=False, name="SatoshiPet")  # noqa: F821
app = BUNDLE(coll, name="SatoshiPet.app", icon=str(icns) if icns.exists() else None,  # noqa: F821
             bundle_identifier="com.pamtech.satoshipet", version="1.5.0",
             info_plist={"LSUIElement": True, "NSHighResolutionCapable": True,
                         "CFBundleShortVersionString": "1.5.0", "NSHumanReadableCopyright": "MIT"})
