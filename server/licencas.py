"""licencas.py - servidor de chaves simples (stdlib + SQLite). Feito pro Hotmart, serve pra qualquer loja com webhook.

Fluxo Hotmart (o Hotmart não tem API pública de license key):
  1. Hotmart → Ferramentas → Webhooks: URL https://SEU-HOST/hotmart/webhook, eventos PURCHASE_APPROVED,
     PURCHASE_COMPLETE, PURCHASE_REFUNDED, PURCHASE_CHARGEBACK, PURCHASE_CANCELED. Copie o "hottok".
  2. Compra aprovada → este servidor gera a chave (HMAC do e-mail, mesmo formato do tools/keygen.py) e guarda.
     Se SMTP_* estiver configurado, manda o e-mail com a chave; senão, a chave aparece em GET /admin/chaves.
  3. O app (licenca_provedor = "servidor", licenca_url = https://SEU-HOST) chama
     GET /api/licenca/validar?email=...&chave=...  →  {"valida": true} | {"valida": false, "motivo": "..."}
  4. Reembolso/chargeback/cancelamento → chave marcada como revogada (o app derruba o Pro na próxima validação;
     offline ele mantém só pelo período de graça).

Env: HOTMART_HOTTOK (obrigatório p/ webhook), TAMAGOSHI_LICENSE_SECRET, ADMIN_TOKEN, DB, PORT, HOST,
     SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/SMTP_FROM (opcional).
"""
import hashlib
import hmac
import json
import os
import smtplib
import sqlite3
import threading
import time
import urllib.parse
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APROVADA = {"PURCHASE_APPROVED", "PURCHASE_COMPLETE"}
REVOGADA = {"PURCHASE_REFUNDED", "PURCHASE_CHARGEBACK", "PURCHASE_CANCELED", "PURCHASE_PROTEST"}


def gerar_chave(segredo, email):
    dig = hmac.new(segredo, email.strip().lower().encode(), hashlib.sha256).hexdigest().upper()[:16]
    return "-".join(dig[i:i + 4] for i in range(0, 16, 4))


class Chaves:
    def __init__(self, db=":memory:", segredo=b"dev-only-nao-use-em-producao"):
        self.segredo = segredo
        self.lock = threading.Lock()
        self.db = sqlite3.connect(db, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS licencas (email TEXT PRIMARY KEY, chave TEXT NOT NULL,
            status TEXT NOT NULL, transacao TEXT, atualizado INTEGER)""")
        self.db.commit()

    def evento(self, d):
        """Processa o JSON do webhook (v2). Retorna (email, status) ou None se ignorado."""
        ev = d.get("event")
        dados = d.get("data") or {}
        email = ((dados.get("buyer") or {}).get("email") or "").strip().lower()
        trans = (dados.get("purchase") or {}).get("transaction")
        if not email or ev not in APROVADA | REVOGADA:
            return None
        status = "ativa" if ev in APROVADA else "revogada"
        chave = gerar_chave(self.segredo, email)
        with self.lock:
            self.db.execute("""INSERT INTO licencas VALUES (?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET
                status=excluded.status, transacao=excluded.transacao, atualizado=excluded.atualizado""",
                            (email, chave, status, trans, int(time.time())))
            self.db.commit()
        return email, status, chave

    def validar(self, email, chave):
        email, chave = (email or "").strip().lower(), (chave or "").strip().upper()
        with self.lock:
            row = self.db.execute("SELECT email, status FROM licencas WHERE chave=?", (chave,)).fetchone()
        if not row:
            return {"valida": False, "motivo": "nao_encontrada"}
        if email and row[0] != email:
            return {"valida": False, "motivo": "email"}
        if row[1] != "ativa":
            return {"valida": False, "motivo": "reembolso"}
        return {"valida": True}

    def listar(self):
        with self.lock:
            return [dict(zip(("email", "chave", "status"), r))
                    for r in self.db.execute("SELECT email, chave, status FROM licencas ORDER BY atualizado DESC")]


def enviar_email(email, chave):
    host = os.environ.get("SMTP_HOST")
    if not host:
        return False
    msg = EmailMessage()
    msg["Subject"] = "Sua chave do Tamagoshi Cripto Pro 🐣"
    msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", ""))
    msg["To"] = email
    msg.set_content(f"Valeu pela compra!\n\nE-mail: {email}\nChave: {chave}\n\n"
                    "No app: botão direito → Ativar Pro. Nunca te pediremos seed ou chave privada de carteira.")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587)), timeout=15) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
        s.send_message(msg)
    return True


def criar_servidor(host="127.0.0.1", porta=8741, db=":memory:", hottok=None, segredo=None, admin=None, mailer=enviar_email):
    ch = Chaves(db, segredo or os.environ.get("TAMAGOSHI_LICENSE_SECRET", "dev-only-nao-use-em-producao").encode())
    hottok = hottok if hottok is not None else os.environ.get("HOTMART_HOTTOK", "")
    admin = admin if admin is not None else os.environ.get("ADMIN_TOKEN", "")

    class H(BaseHTTPRequestHandler):
        def _json(self, cod, obj):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(cod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            if u.path == "/api/licenca/validar":
                return self._json(200, ch.validar(q.get("email"), q.get("chave")))
            if u.path == "/admin/chaves":
                if not admin or not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {admin}"):
                    return self._json(401, {"erro": "não autorizado"})
                return self._json(200, {"licencas": ch.listar()})
            if u.path == "/health":
                return self._json(200, {"ok": True})
            self._json(404, {"erro": "não achei"})

        def do_POST(self):
            if self.path != "/hotmart/webhook":
                return self._json(404, {"erro": "não achei"})
            tok = self.headers.get("X-HOTMART-HOTTOK", "")
            if not hottok or not hmac.compare_digest(tok, hottok):
                return self._json(401, {"erro": "hottok inválido"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > 64 * 1024:
                return self._json(413, {"erro": "grande demais"})
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"erro": "json inválido"})
            r = ch.evento(d)
            if r and r[1] == "ativa":
                try:
                    mailer(r[0], r[2])
                except Exception as e:  # e-mail falhou: a chave continua em /admin/chaves
                    print("[licencas] e-mail falhou:", e)
            self._json(200, {"ok": True, "processado": bool(r)})

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer((host, porta), H)
    srv.chaves = ch
    return srv


if __name__ == "__main__":
    h, p = os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", 8741))
    if not os.environ.get("HOTMART_HOTTOK"):
        print("AVISO: HOTMART_HOTTOK vazio, o webhook vai recusar tudo.")
    print(f"servidor de licenças em http://{h}:{p}")
    criar_servidor(h, p, os.environ.get("DB", "licencas.db")).serve_forever()
