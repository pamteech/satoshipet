# SatoshiPet · VS Code

Status bar pet + price, and a webview panel with the animated pixel sprite.

- If the desktop app is running, it reads `http://127.0.0.1:8737/status` (name, mood, level, price).
- Otherwise it uses CoinGecko's public keyless API for the price of `satoshipet.moeda`.
- No accounts, no keys, no telemetry. Not financial advice.

## Build (local, no publishing)

```bash
cd vscode
npx --yes @vscode/vsce package      # -> satoshipet-1.4.0.vsix
code --install-extension satoshipet-1.4.0.vsix
```

Publishing to the Marketplace (`vsce publish`) needs a publisher account + token. **Not done** on purpose.

## pt-BR

Bichinho + preço na barra de status, e um painel com o sprite animado. Clique no sprite = carinho.
Lê a API local do app (se estiver rodando) ou a CoinGecko pública (sem chave).
