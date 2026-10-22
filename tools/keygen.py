"""keygen.py - gera chaves Pro (NÃO distribua). Uso:
    TAMAGOSHI_LICENSE_SECRET=seu-segredo python tools/keygen.py cliente@email.com
Use o MESMO segredo configurado no GitHub Secret do workflow de release.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tamagoshi_cripto.license import gerar_chave  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if not os.environ.get("TAMAGOSHI_LICENSE_SECRET"):
        print("AVISO: sem TAMAGOSHI_LICENSE_SECRET -> chaves de DEV (não valem no build oficial)\n")
    for email in sys.argv[1:]:
        print(f"{email.strip().lower()}  ->  {gerar_chave(email)}")
