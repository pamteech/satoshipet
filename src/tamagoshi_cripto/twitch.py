"""twitch.py - lê o chat da Twitch ANÔNIMO (login justinfan, sem conta, sem token, sem OAuth).

Só leitura: o bot nunca manda mensagem. Comandos aceitos: !pet !moon !rekt !price !dna !dance.
Ligue com cfg["twitch_canal"] = "seu_canal" (vazio = desligado).
"""
import random
import re
import socket
import ssl
import threading
import time

HOST, PORTA = "irc.chat.twitch.tv", 443  # TLS na 443 passa em firewall chato (a 6697 também existe)
RE_CANAL = re.compile(r"^[a-z0-9_]{3,25}$")
RE_MSG = re.compile(r"^(?:@\S+ )?:(\w+)!\S+ PRIVMSG #(\w+) :(.*)$")


def canal_valido(c):
    return bool(RE_CANAL.match((c or "").strip().lower().lstrip("#")))


def parse_linha(linha, comandos):
    """(usuario, comando) se a linha for um PRIVMSG com comando conhecido, senão None."""
    m = RE_MSG.match(linha.strip())
    if not m:
        return None
    usuario, _, texto = m.groups()
    cmd = (texto.strip().split() or [""])[0].lower()
    return (usuario[:25], cmd) if cmd in comandos else None


class Leitor:
    def __init__(self, canal, comandos, ao_comando):
        self.canal = canal.strip().lower().lstrip("#")
        self.comandos, self.ao_comando = comandos, ao_comando
        self.parar = False
        self.conectado = False

    def iniciar(self):
        if not canal_valido(self.canal):
            raise ValueError("canal inválido")
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _loop(self):
        espera = 2
        while not self.parar:
            try:
                self._sessao()
                espera = 2
            except Exception as e:
                print("[twitch] caiu, reconectando:", e)
            self.conectado = False
            time.sleep(espera)
            espera = min(espera * 2, 120)

    def _sessao(self):
        bruto = socket.create_connection((HOST, PORTA), timeout=330)
        s = ssl.create_default_context().wrap_socket(bruto, server_hostname=HOST)
        nick = f"justinfan{random.randint(10000, 99999)}"  # login anônimo oficial da Twitch
        s.sendall(f"NICK {nick}\r\nJOIN #{self.canal}\r\n".encode())
        self.conectado = True
        buf = b""
        while not self.parar:
            dados = s.recv(4096)
            if not dados:
                raise ConnectionError("fim da conexão")
            buf += dados
            *linhas, buf = buf.split(b"\r\n")
            for l in linhas:
                t = l.decode("utf-8", "replace")
                if t.startswith("PING"):
                    s.sendall(("PONG" + t[4:] + "\r\n").encode())
                    continue
                r = parse_linha(t, self.comandos)
                if r:
                    self.ao_comando(*r)
        s.close()
