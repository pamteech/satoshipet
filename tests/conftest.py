import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("SATOSHIPET_CONFIG", str(Path(tempfile.mkdtemp()) / "cfg.json"))

import pytest

# v1.5: o test_gui troca funções de rede por fakes "na marra" (atribuição direta). Sem isso, os fakes
# vazavam pros testes seguintes. Aqui a gente tira foto dos módulos e devolve tudo no fim de cada teste.
_MODULOS = ("logic", "lore", "onchain", "baleias", "noticias", "multichain", "license")


@pytest.fixture(autouse=True)
def _restaura_modulos_mockados():
    import importlib
    mods = [importlib.import_module(f"satoshipet.{m}") for m in _MODULOS]
    fotos = [(m, dict(vars(m))) for m in mods]
    yield
    for m, foto in fotos:
        for k, v in foto.items():
            if callable(v) and vars(m).get(k) is not v:
                setattr(m, k, v)
