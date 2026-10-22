"""api.py - API HTTP local (só 127.0.0.1) pra plugar o bicho em polybar, sketchybar, OBS...

GET /status       -> JSON completo
GET /status.txt   -> uma linha (barra de status)
GET /overlay      -> página HTML transparente pro OBS (Browser Source)
GET /card.svg     -> card de perfil animado (README do GitHub) - v1.4
GET /stream       -> overlay de streamer (sprite + preço + chat da Twitch) - v1.4
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


STREAM = r"""<!doctype html><meta charset=utf-8><title>Tamagoshi - overlay</title><style>
html,body{margin:0;background:transparent;overflow:hidden;font:bold 18px monospace;color:#1a1c2c}
#w{position:absolute;left:16px;bottom:16px;display:flex;align-items:flex-end;gap:12px}
#s{width:192px;height:192px;image-rendering:pixelated}
#bal{background:#f4f4f4;border:4px solid #1a1c2c;box-shadow:4px 4px 0 #1a1c2c;padding:8px 12px;max-width:320px;margin-bottom:120px}
#tk{background:#29213f;color:#f4f4f4;border:4px solid #1a1c2c;padding:6px 10px;margin-top:6px;display:inline-block}
.moon{color:#38b764}.rekt{color:#b13e53}.garimpando{color:#ef7d57}
#chat{position:absolute;left:16px;bottom:236px;color:#ffcd75;text-shadow:2px 2px #1a1c2c;transition:opacity .4s}
#pat{display:none;background:#ffcd75;border:3px solid #1a1c2c;padding:2px 6px;font-size:12px;position:absolute;left:16px;top:8px}
</style><div id=w><div><canvas id=s width=48 height=48></canvas><br><span id=tk>...</span></div><div id=bal>gm!</div></div>
<div id=chat></div><div id=pat>PATROCINADO</div><script>
const L={garimpando:0,moon:1,rekt:2,pulo:3},cv=document.getElementById('s'),g=cv.getContext('2d');g.imageSmoothingEnabled=false;
let img=new Image(),chave='',st={humor:'garimpando'},f=0,pulo=0,ult=0;
function frame(){if(img.complete&&img.naturalWidth){g.clearRect(0,0,48,48);
g.drawImage(img,f*48,(L[pulo>0?'pulo':st.humor]||0)*48,48,48,0,0,48,48)}f=(f+1)%4;if(pulo)pulo--}
setInterval(frame,180);
async function t(){try{st=await (await fetch('/status')).json();
const k=st.moeda+st.skin+st.estagio+JSON.stringify(st.genes)+st.fantasma;if(k!==chave){chave=k;img.src='/sprite.png?'+encodeURIComponent(k)}
document.getElementById('bal').textContent=st.frase||'';
document.getElementById('tk').innerHTML=st.moeda+' '+st.preco_fmt+' <span class='+st.humor+'>'+(st.variacao_pct>=0?'+':'')+st.variacao_pct.toFixed(2)+'%</span> LV'+st.nivel;
document.getElementById('pat').style.display=st.patrocinado?'block':'none';
const s=st.stream||{};const c=document.getElementById('chat');
if(s.t&&s.t!==ult){ult=s.t;pulo=8;c.textContent=s.ultimo;c.style.opacity=1;setTimeout(()=>c.style.opacity=0,4000)}
}catch(e){}}
t();setInterval(t,2000)</script>"""


def iniciar(obter_status, porta=PORTA, folha=None):
    """Sobe o servidor numa thread daemon. obter_status() deve ser thread-safe e barato.
    folha() -> bytes PNG da folha de sprites atual (com DNA), usada pelo /stream."""

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
            elif self.path.startswith("/card.svg"):
                from . import cartao
                self._enviar(cartao.svg(cartao.exportar_stats(obter_status())), "image/svg+xml")
            elif self.path.startswith("/stream"):
                self._enviar(STREAM, "text/html; charset=utf-8")
            elif self.path.startswith("/sprite.png") and folha:
                dados = folha()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(dados)))
                self.send_header("Cache-Control", "max-age=60")
                self.end_headers()
                self.wfile.write(dados)
            elif self.path.startswith("/overlay"):
                self._enviar(OVERLAY, "text/html; charset=utf-8")
            else:
                self.send_error(404, "tenta /status, /status.txt, /overlay, /stream ou /card.svg")

        def log_message(self, *a):  # silêncio no console
            pass

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", porta), H)
    except OSError as e:
        print(f"[api] porta {porta} ocupada, API desligada:", e)
        return None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
