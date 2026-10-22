@echo off
REM Build do .exe (Windows). Rode da raiz do repo: tools\build_windows.bat
REM Para o build oficial, defina SATOSHIPET_LICENSE_SECRET antes (vira src\satoshipet\_segredo.py).
pip install -e ".[tray,build]" || exit /b 1
if defined SATOSHIPET_LICENSE_SECRET python -c "import os;open('src/satoshipet/_segredo.py','w').write('SEGREDO=%%r\n'%%os.environ['SATOSHIPET_LICENSE_SECRET'])"
pyinstaller --noconsole --onefile --name SatoshiPet ^
  --icon src\satoshipet\assets\icone.ico ^
  --add-data "src\satoshipet\assets;satoshipet\assets" ^
  --hidden-import pystray._win32 --collect-submodules satoshipet ^
  --paths src tools\run_app.py
echo Pronto: dist\SatoshiPet.exe
