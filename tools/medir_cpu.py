"""Mede o uso de CPU do widget parado (idle). Uso: xvfb-run -a python tools/medir_cpu.py [segundos]

Abre o app com config temporária (onboarding já feito, sem som), espera 10 s de aquecimento e mede
o tempo de CPU (user+sys, incluindo threads) via psutil ou /proc. Meta: < ~2% de um núcleo.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEG = float(sys.argv[1]) if len(sys.argv) > 1 else 60


def cpu_s(pid):
    try:
        import psutil
        t = psutil.Process(pid).cpu_times()
        return t.user + t.system
    except ImportError:
        campos = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(campos[11]) + int(campos[12])) / os.sysconf("SC_CLK_TCK")


def main():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "cfg.json").write_text(json.dumps({"onboarding_ok": True, "mudo": True, "versao_config": 3}))
    env = dict(os.environ, TAMAGOSHI_CONFIG=str(tmp / "cfg.json"), PYTHONPATH=str(RAIZ / "src"),
               TAMAGOSHI_API_PORT="18799", HOME=str(tmp))
    p = subprocess.Popen([sys.executable, "-m", "tamagoshi_cripto", "--no-tray"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(10)
        c0, t0 = cpu_s(p.pid), time.time()
        time.sleep(SEG)
        c1, t1 = cpu_s(p.pid), time.time()
    finally:
        p.terminate()
    pct = (c1 - c0) / (t1 - t0) * 100
    print(f"CPU idle: {pct:.2f}% de um núcleo ({c1 - c0:.2f}s de CPU em {t1 - t0:.0f}s)")
    return pct


if __name__ == "__main__":
    main()
