# packaging/ - rascunhos de distribuição (v1.5.0) — NADA aqui foi publicado/submetido

| Arquivo | Pra quê | Status |
|---|---|---|
| pyinstaller/satoshipet_mac.spec | .app do macOS (LSUIElement, sem ícone no Dock) | não testado num Mac |
| pyinstaller/satoshipet_win.spec | .exe onefile do Windows | não testado num Windows |
| homebrew/satoshipet.rb | fórmula (tap próprio) | rascunho: pamteech + sha256 a preencher |
| winget/*.yaml | manifests winget 1.6 | rascunho, não submetido |
| scoop/satoshipet.json | manifest scoop | rascunho, não submetido |

Wheel local verificada em venv limpo: `pip install .` -> `satoshipet --help`/`--tui` ok (wheel 1.5.0 ≈ 1989 KB, sha256 `8051a23c70b89b81…`).
