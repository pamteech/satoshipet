"""Soak curto no pytest (6 h simuladas, ~15 s). O longo: xvfb-run -a python tests/soak.py --horas 48."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="precisa de display (use xvfb-run)")
@pytest.mark.parametrize("semente", [11])
def test_soak_6h(semente):
    r = subprocess.run([sys.executable, str(RAIZ / "tests" / "soak.py"), "--horas", "6", "--semente", str(semente)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "SOAK OK" in r.stdout, (r.stdout[-2000:], r.stderr[-4000:])
