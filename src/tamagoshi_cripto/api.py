"""api.py - API HTTP local (só 127.0.0.1) pra plugar o bicho em polybar, sketchybar, OBS...

GET /status       -> JSON completo
GET /status.txt   -> uma linha (barra de status)
GET /overlay      -> página HTML transparente pro OBS (Browser Source)
Porta padrão 8737 (T-A-M-A no teclado do celular, mais ou menos). Mude com $TAMAGOSHI_API_PORT.
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTA = int(os.environ.get("TAMAGOSHI_API_PORT", "8737"))

OVERLAY = """<!doctype html><meta charset=utf-8><style>
body{margin:0;background:transparent;font:16px monospace;color:#f4f4f4;text-shadow:2px 2px #1a1c2c}
#b{padding:8px 12px;background:#29213fcc;border:3px solid #1a1c2c;display:inline-block}
.moon{color:#38b764}.rekt{color:#b13e53}.garimpando{color:#ef7d57}</style>
<div id=b>carregando...</div><script>
async function t(){try{const s=await (await fetch('/status')).json();
b.innerHTML=`<b>${s.nome}</b> LV${s.nivel} ${s.estagio}<br>${s.moeda} ${s.preco_fmt} <span class=${s.humor}>${s.variacao_pct.toFixed(2)}% ${s.humor.toUpperCase()}</span><br>bloco ${s.btc.bloco??'?'} · fee ${s.btc.fee_sat_vb??'?'} sat/vB`}catch(e){}}
t();setInterval(t,5000)</script>"""


def iniciar(obter_status, porta=PORTA):
    """Sobe o servidor numa thread daemon. obter_status() deve ser thread-safe e barato."""

    class H(BaseHTTPRequestHandler):
        def _enviar(self, corpo, tipo):
            dados = corpo.encode()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_GET(self):
            if self.path.startswith("/status.txt"):
                s = obter_status()
                self._enviar(f"{s['emoji']} {s['moeda']} {s['preco_fmt']} {s['variacao_pct']:+.2f}% "
                             f"LV{s['nivel']}\n", "text/plain; charset=utf-8")
            elif self.path.startswith("/status"):
                self._enviar(json.dumps(obter_status(), ensure_ascii=False), "application/json")
            elif self.path.startswith("/overlay"):
                self._enviar(OVERLAY, "text/html; charset=utf-8")
            else:
                self.send_error(404, "tenta /status, /status.txt ou /overlay")

        def log_message(self, *a):  # silêncio no console
            pass

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    except OSError as e:
        print(f"[api] porta {porta} ocupada, API desligada:", e)
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
