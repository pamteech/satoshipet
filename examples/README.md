# Integrações com a API local

O app sobe um servidor HTTP **só em `127.0.0.1`** (nunca exposto na rede), porta `8737`
(mude com `SATOSHIPET_API_PORT`; desligue com `--no-api` ou `"api": false` na config).

| Endpoint | O que é |
|---|---|
| `GET /status` | JSON completo (preço, humor, nível, estágio, bloco, fee, hashrate, gas, carteira...) |
| `GET /status.txt` | uma linha pronta pra barra: `🚀 BTC $67,123.00 +2.41% LV7` |
| `GET /overlay` | página HTML transparente pro **OBS** (Browser Source, 360×120) |

- **sketchybar (macOS):** [`sketchybar/satoshipet.sh`](sketchybar/satoshipet.sh)
- **polybar (Linux):** [`polybar/satoshipet.ini`](polybar/satoshipet.ini)
- **OBS:** Fontes → Navegador → URL `http://127.0.0.1:8737/overlay`
- **Shell:** `satoshipet --status | jq .btc` ou `curl -s localhost:8737/status | jq`
