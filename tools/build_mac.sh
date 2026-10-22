#!/usr/bin/env bash
# Build do .app (macOS). Rode da raiz do repo: ./tools/build_mac.sh
# ATENÇÃO: escrito com cuidado mas ainda não testado num Mac de verdade.
set -euo pipefail
python3 -m pip install -e ".[tray,build]"
if [[ -n "${SATOSHIPET_LICENSE_SECRET:-}" ]]; then
  python3 -c "import os;open('src/satoshipet/_segredo.py','w').write('SEGREDO=%r\n'%os.environ['SATOSHIPET_LICENSE_SECRET'])"
fi
# ícone .icns a partir do PNG (sips/iconutil já vêm no macOS)
ICONSET=build/SatoshiPet.iconset; mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
  sips -z $s $s src/satoshipet/assets/icone.png --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o build/SatoshiPet.icns
pyinstaller --windowed --noconfirm --name "SatoshiPet" \
  --icon build/SatoshiPet.icns \
  --add-data "src/satoshipet/assets:satoshipet/assets" \
  --collect-submodules satoshipet --paths src \
  --osx-bundle-identifier com.pamtech.satoshipet \
  tools/run_app.py
# LSUIElement=1: sem ícone no Dock (é um widget, afinal)
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "dist/SatoshiPet.app/Contents/Info.plist" || true
echo "Pronto: dist/SatoshiPet.app  (sem assinatura: botão direito > Abrir na 1ª vez)"
