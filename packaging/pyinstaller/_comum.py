# _comum.py - pedaços compartilhados pelos .spec (PyInstaller roda o spec como Python, então dá pra importar).
# Enxugando o app: fora tudo que o PyInstaller puxa "por via das dúvidas" e a gente não usa.
from pathlib import Path

RAIZ = Path(SPECPATH).resolve().parents[1] if "SPECPATH" in globals() else Path(__file__).resolve().parents[2]  # noqa: F821
SRC = RAIZ / "src"
ASSETS = (str(SRC / "satoshipet" / "assets"), "satoshipet/assets")
EXCLUIR = [
    "numpy", "pandas", "matplotlib", "scipy", "IPython", "pytest", "_pytest", "setuptools", "pkg_resources",
    "PIL.ImageQt", "PIL.ImageTk_test", "PyQt5", "PyQt6", "PySide2", "PySide6", "unittest", "pydoc_data",
    "lib2to3", "xmlrpc", "test", "tkinter.test", "sqlite3", "curses",
]
