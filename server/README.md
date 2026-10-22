# Leaderboard server (optional)

Tiny, stdlib-only (Python 3.9+, `http.server` + SQLite). **Opt-in** on the client (off by default).

| | |
|---|---|
| `POST /api/stats` | `{"device_id": "<32 hex, random>", "nick": "satoshi_fan", "xp": 1234, "nivel": 12, "estagio": "WHALE", "blocos": 40, "conquistas": 7, "moeda": "BTC"}` → `{"ok": true, "posicao": 3}` |
| `GET /api/top?n=50` | top 50 by XP (no device ids) |
| `GET /health` | `{"ok": true}` |

**Privacy:** only the fields above are stored. No IP (kept in memory for 60 s for rate limiting only), no e-mail,
no wallet address (nicks that look like addresses/e-mails are rejected), no price data.
**Limits:** 10 POST/min per IP, 1 POST / 20 s per device, 2 KB body, sane value ranges.

```bash
python server/ranking.py                       # http://0.0.0.0:8740, ranking.db in cwd
docker build -t tamagoshi-ranking server
docker run -p 8740:8740 -v "$PWD/data:/data" tamagoshi-ranking
```
Deploy anywhere that runs a container (Fly.io, Render, a $5 VPS) behind HTTPS, then set the URL in the
app config (`"ranking_url"`) and in `site/config.js`.
