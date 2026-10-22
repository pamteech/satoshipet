"""ranking.py - servidor de leaderboard do SatoshiPet. Só stdlib (http.server + sqlite3).

Privacidade por design (é anônimo mesmo, juro de dedinho):
  - guarda só: device_id aleatório (gerado no cliente), apelido, xp, nível, estágio, blocos, conquistas, moeda;
  - NUNCA guarda IP, e-mail, endereço de carteira, preço ou qualquer coisa pessoal;
  - apelido que parece endereço BTC/ETH ou e-mail é recusado;
  - o IP só vive na memória, pro rate limit, e some depois de 1 min.

Rodar:  python server/ranking.py          (PORT=8740 HOST=0.0.0.0 DB=ranking.db)
Docker: docker build -t satoshipet-ranking server && docker run -p 8740:8740 -v $PWD/data:/data satoshipet-ranking
"""
import json
import os
import re
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RE_DEVICE = re.compile(r"^[0-9a-f]{32}$")
RE_NICK = re.compile(r"^[A-Za-z0-9_\-]{3,16}$")
RE_PROIBIDO = re.compile(r"^(bc1|0x|[13][a-km-zA-HJ-NP-Z1-9]{10,})|@", re.I)
ESTAGIOS = {"OVO", "BEBE", "ADULTO", "WHALE", "DIAMOND HANDS"}
MOEDAS = {"BTC", "ETH", "SOL", "DOGE", "PEPE"}
XP_MAX = 10_000_000          # mais que isso é hack (ou alguém rodando desde o bloco gênese)
POSTS_POR_MIN_IP = 10
INTERVALO_DEVICE = 20        # segundos entre envios do mesmo device
MAX_CORPO = 2048


class Ranking:
    def __init__(self, caminho=":memory:"):
        self.db = sqlite3.connect(caminho, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("""CREATE TABLE IF NOT EXISTS jogadores (
            device_id TEXT PRIMARY KEY, nick TEXT NOT NULL, xp INTEGER NOT NULL, nivel INTEGER NOT NULL,
            estagio TEXT NOT NULL, blocos INTEGER NOT NULL, conquistas INTEGER NOT NULL, moeda TEXT NOT NULL,
            atualizado INTEGER NOT NULL)""")
        self.db.commit()
        self.ips = {}      # ip -> [timestamps] (só memória)
        self.devices = {}  # device -> último envio

    # ---------- validação ----------
    @staticmethod
    def limpar(d):
        """Retorna (registro, erro). Só campos da lista branca passam."""
        if not isinstance(d, dict):
            return None, "json deve ser objeto"
        dev, nick = str(d.get("device_id", "")), str(d.get("nick", "")).strip()
        if not RE_DEVICE.match(dev):
            return None, "device_id inválido (32 hex)"
        if not RE_NICK.match(nick) or RE_PROIBIDO.search(nick):
            return None, "apelido inválido (3-16 letras/números/_/-, nada de endereço ou e-mail)"
        try:
            xp, nivel = int(d.get("xp", 0)), int(d.get("nivel", 1))
            blocos, conq = int(d.get("blocos", 0)), int(d.get("conquistas", 0))
        except (TypeError, ValueError):
            return None, "números inválidos"
        if not (0 <= xp <= XP_MAX and 1 <= nivel <= 1000 and 0 <= blocos <= 10_000_000 and 0 <= conq <= 500):
            return None, "valores fora do intervalo"
        est = str(d.get("estagio", "OVO")).upper()
        moeda = str(d.get("moeda", "BTC")).upper()
        if est not in ESTAGIOS or moeda not in MOEDAS:
            return None, "estágio/moeda inválidos"
        return {"device_id": dev, "nick": nick, "xp": xp, "nivel": nivel, "estagio": est,
                "blocos": blocos, "conquistas": conq, "moeda": moeda}, None

    def permitido(self, ip, dev=None, agora=None):
        agora = agora or time.time()
        with self.lock:
            lista = [t for t in self.ips.get(ip, []) if agora - t < 60]
            if len(lista) >= POSTS_POR_MIN_IP:
                self.ips[ip] = lista
                return False
            if dev and agora - self.devices.get(dev, 0) < INTERVALO_DEVICE:
                return False
            lista.append(agora)
            self.ips[ip] = lista
            if dev:
                self.devices[dev] = agora
            # faxina: IP velho some da memória
            for k in [k for k, v in self.ips.items() if not v or agora - v[-1] > 60]:
                del self.ips[k]
            return True

    def salvar(self, r):
        with self.lock:
            self.db.execute("""INSERT INTO jogadores VALUES (:device_id,:nick,:xp,:nivel,:estagio,:blocos,
                :conquistas,:moeda,:t) ON CONFLICT(device_id) DO UPDATE SET nick=excluded.nick, xp=excluded.xp,
                nivel=excluded.nivel, estagio=excluded.estagio, blocos=excluded.blocos,
                conquistas=excluded.conquistas, moeda=excluded.moeda, atualizado=excluded.atualizado""",
                            {**r, "t": int(time.time())})
            self.db.commit()
            pos = self.db.execute("SELECT COUNT(*) FROM jogadores WHERE xp > ?", (r["xp"],)).fetchone()[0] + 1
        return pos

    def top(self, n=50):
        n = max(1, min(int(n), 50))
        with self.lock:
            linhas = self.db.execute("""SELECT nick, xp, nivel, estagio, blocos, conquistas, moeda FROM jogadores
                ORDER BY xp DESC, atualizado ASC LIMIT ?""", (n,)).fetchall()
        campos = ("nick", "xp", "nivel", "estagio", "blocos", "conquistas", "moeda")
        return [{"pos": i + 1, **dict(zip(campos, l))} for i, l in enumerate(linhas)]


def criar_servidor(host="127.0.0.1", porta=8740, db=":memory:"):
    rk = Ranking(db)

    class H(BaseHTTPRequestHandler):
        def _json(self, cod, obj):
            dados = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(cod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_OPTIONS(self):
            self._json(204, {})

        def do_GET(self):
            if self.path.startswith("/api/top"):
                n = 50
                if "n=" in self.path:
                    try:
                        n = int(self.path.split("n=")[1].split("&")[0])
                    except ValueError:
                        pass
                self._json(200, {"top": rk.top(n)})
            elif self.path.startswith("/health"):
                self._json(200, {"ok": True})
            else:
                self._json(404, {"erro": "tenta GET /api/top ou POST /api/stats"})

        def do_POST(self):
            if not self.path.startswith("/api/stats"):
                return self._json(404, {"erro": "não achei"})
            tam = int(self.headers.get("Content-Length") or 0)
            if tam > MAX_CORPO:
                return self._json(413, {"erro": "corpo grande demais"})
            try:
                d = json.loads(self.rfile.read(tam) or b"{}")
            except ValueError:
                return self._json(400, {"erro": "json inválido"})
            r, erro = rk.limpar(d)
            if erro:
                return self._json(400, {"erro": erro})
            # atrás de proxy (fly/render), use o 1º X-Forwarded-For só pro rate limit
            ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
            if not rk.permitido(ip, r["device_id"]):
                return self._json(429, {"erro": "calma, satoshi. tenta de novo em alguns segundos"})
            self._json(200, {"ok": True, "posicao": rk.salvar(r)})

        def log_message(self, *a):  # sem log de IP
            pass

    srv = ThreadingHTTPServer((host, porta), H)
    srv.ranking = rk
    return srv


if __name__ == "__main__":
    host, porta = os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", 8740))
    srv = criar_servidor(host, porta, os.environ.get("DB", "ranking.db"))
    print(f"ranking no ar em http://{host}:{porta}  (GET /api/top, POST /api/stats)")
    srv.serve_forever()
