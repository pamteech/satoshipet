#!/usr/bin/env bash
# Build do .app (macOS). Rode da raiz do repo: ./tools/build_mac.sh
# ATENÇÃO: escrito com cuidado mas ainda não testado num Mac de verdade.
set -euo pipefail
python3 -m pip install -e ".[tray,build]"
if [[ -n "${TAMAGOSHI_LICENSE_SECRET:-}" ]]; then
  python3 -c "import os;open('src/tamagoshi_cripto/_segredo.py','w').write('SEGREDO=%r\n'%os.environ['TAMAGOSHI_LICENSE_SECRET'])"
fi
# ícone .icns a partir do PNG (sips/iconutil já vêm no macOS)
ICONSET=build/Tamagoshi.iconset; mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
  sips -z $s $s src/tamagoshi_cripto/assets/icone.png --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o build/Tamagoshi.icns
pyinstaller --windowed --noconfirm --name "Tamagoshi Cripto" \
  --icon build/Tamagoshi.icns \
  --add-data "src/tamagoshi_cripto/assets:tamagoshi_cripto/assets" \
  --collect-submodules tamagoshi_cripto --paths src \
  --osx-bundle-identifier com.tamagoshi.cripto \
  tools/run_app.py
# LSUIElement=1: sem ícone no Dock (é um widget, afinal)
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "dist/Tamagoshi Cripto.app/Contents/Info.plist" || true
echo "Pronto: dist/Tamagoshi Cripto.app  (sem assinatura: botão direito > Abrir na 1ª vez)"
