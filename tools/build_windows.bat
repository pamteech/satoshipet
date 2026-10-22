@echo off
REM Build do .exe (Windows). Rode da raiz do repo: tools\build_windows.bat
REM Para o build oficial, defina TAMAGOSHI_LICENSE_SECRET antes (vira src\tamagoshi_cripto\_segredo.py).
pip install -e ".[tray,build]" || exit /b 1
if defined TAMAGOSHI_LICENSE_SECRET python -c "import os;open('src/tamagoshi_cripto/_segredo.py','w').write('SEGREDO=%%r\n'%%os.environ['TAMAGOSHI_LICENSE_SECRET'])"
pyinstaller --noconsole --onefile --name TamagoshiCripto ^
  --icon src\tamagoshi_cripto\assets\icone.ico ^
  --add-data "src\tamagoshi_cripto\assets;tamagoshi_cripto\assets" ^
  --hidden-import pystray._win32 --collect-submodules tamagoshi_cripto ^
  --paths src tools\run_app.py
echo Pronto: dist\TamagoshiCripto.exe
