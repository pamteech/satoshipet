# packaging/ - rascunhos de distribuição (v1.5.0) — NADA aqui foi publicado/submetido

| Arquivo | Pra quê | Status |
|---|---|---|
| pyinstaller/tamagoshi_mac.spec | .app do macOS (LSUIElement, sem ícone no Dock) | não testado num Mac |
| pyinstaller/tamagoshi_win.spec | .exe onefile do Windows | não testado num Windows |
| homebrew/tamagoshi.rb | fórmula (tap próprio) | rascunho: pamteech + sha256 a preencher |
| winget/*.yaml | manifests winget 1.6 | rascunho, não submetido |
| scoop/tamagoshi.json | manifest scoop | rascunho, não submetido |

Wheel local verificada em venv limpo: `pip install .` -> `tamagoshi --help`/`--tui` ok (wheel 1.5.0 ≈ 1989 KB, sha256 `8051a23c70b89b81…`).
