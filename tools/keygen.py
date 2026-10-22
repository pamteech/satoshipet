"""keygen.py - gera chaves Pro (NÃO distribua). Uso:
    TAMAGOSHI_LICENSE_SECRET=seu-segredo python tools/keygen.py cliente@email.com
    ... keygen.py --pack neon_nights cliente@email.com   -> código SKIN-... do pacote (só pra esse e-mail)
    ... keygen.py --pack neon_nights '*'                 -> código promocional (vale pra todo mundo)
Use o MESMO segredo configurado no GitHub Secret do workflow de release.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tamagoshi_cripto.license import gerar_chave

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if not os.environ.get("TAMAGOSHI_LICENSE_SECRET"):
        print("AVISO: sem TAMAGOSHI_LICENSE_SECRET -> chaves de DEV (não valem no build oficial)\n")
    if sys.argv[1] == "--pack":
        from tamagoshi_cripto.loja import gerar_codigo
        for email in sys.argv[3:] or ["*"]:
            print(f"{sys.argv[2]} {email}  ->  {gerar_codigo(sys.argv[2], email)}")
        sys.exit(0)
    for email in sys.argv[1:]:
        print(f"{email.strip().lower()}  ->  {gerar_chave(email)}")
