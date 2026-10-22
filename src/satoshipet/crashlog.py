"""crashlog.py - quando o bicho tropeça, anota no diário. 'Enviar relatório' só abre uma issue preenchida
no GitHub no seu navegador: você revisa e decide se manda. Nada é enviado sozinho."""
import platform
import sys
import time
import traceback
import urllib.parse
from pathlib import Path

from . import __version__

PASTA = Path.home() / ".satoshipet"
ARQUIVO = PASTA / "crash.log"
MAX_BYTES = 200_000
REPO = "pamteech/satoshipet"


def registrar(exc_tipo, exc, tb, contexto=""):
    texto = "".join(traceback.format_exception(exc_tipo, exc, tb))
    try:
        PASTA.mkdir(parents=True, exist_ok=True)
        if ARQUIVO.exists() and ARQUIVO.stat().st_size > MAX_BYTES:  # roda o log: fica só a metade nova
            ARQUIVO.write_text(ARQUIVO.read_text(encoding="utf-8", errors="replace")[-MAX_BYTES // 2:], encoding="utf-8")
        with open(ARQUIVO, "a", encoding="utf-8") as f:
            f.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} v{__version__} {contexto}\n{texto}")
    except OSError:
        pass
    return texto


def instalar():
    """sys.excepthook -> arquivo (e ainda imprime no terminal)."""
    anterior = sys.excepthook

    def gancho(t, e, tb):
        registrar(t, e, tb, "fatal")
        anterior(t, e, tb)
    sys.excepthook = gancho


def ultimo(max_chars=1500):
    try:
        txt = ARQUIVO.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    blocos = txt.split("\n=== ")
    return ("=== " + blocos[-1]).strip()[-max_chars:] if len(blocos) > 1 else txt[-max_chars:]


def _limpar(txt):
    """Tira o caminho da home (pode ter seu nome de usuário) antes de ir pro navegador."""
    return txt.replace(str(Path.home()), "~")


def url_issue(repo=REPO, extra=""):
    corpo = (f"**Versão:** {__version__}\n**SO:** {platform.system()} {platform.release()} ({platform.machine()})\n"
             f"**Python:** {platform.python_version()}\n\n**O que aconteceu?**\n{extra or '(descreva aqui)'}\n\n"
             f"**Log (revise antes de enviar):**\n```\n{_limpar(ultimo()) or 'sem crash registrado'}\n```\n")
    q = urllib.parse.urlencode({"title": f"[crash] v{__version__}", "labels": "bug", "body": corpo})
    return f"https://github.com/{repo}/issues/new?{q}"
