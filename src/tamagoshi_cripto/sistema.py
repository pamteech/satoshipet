"""sistema.py - integração com o SO: bandeja/menu bar, iniciar com o sistema, transparência.

Windows: bandeja via pystray (thread) + chave HKCU\\...\\Run.
macOS:   menu bar via pystray.run_detached() (experimental, opt-in) + LaunchAgent plist.
Linux:   tudo vira no-op educado.
NOTA: o código de macOS foi escrito com cuidado, mas não testado num Mac de verdade ainda.
"""
import plistlib
import sys
import threading
from pathlib import Path

NOME_RUN = "TamagoshiCripto"
LABEL_MAC = "com.tamagoshi.cripto"
PLIST_MAC = Path.home() / "Library" / "LaunchAgents" / f"{LABEL_MAC}.plist"
WIN, MAC = sys.platform == "win32", sys.platform == "darwin"


# ---------------- transparência ----------------
def aplicar_transparencia(root, canvas, cor_chave):
    """Retorna a cor de fundo a usar nos widgets.
    Windows: cor-chave vira buraco. Mac: systemTransparent. Linux: alpha parcial."""
    import tkinter as tk
    if WIN:
        root.attributes("-transparentcolor", cor_chave)
        return cor_chave
    if MAC:
        try:
            root.wm_attributes("-transparent", True)
            root.configure(bg="systemTransparent")
            canvas.configure(bg="systemTransparent")
            return "systemTransparent"
        except tk.TclError:
            pass
    try:
        root.attributes("-alpha", 0.95)
    except tk.TclError:
        pass
    return cor_chave


# ---------------- bandeja / menu bar ----------------
def tray_disponivel(mac_menubar=False):
    if not (WIN or (MAC and mac_menubar)):
        return False
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def iniciar_tray(icone_png, mostrar, esconder, sair, mac_menubar=False):
    """Callbacks devem voltar pra thread do Tk (o app usa root.after)."""
    if not tray_disponivel(mac_menubar):
        return None
    import pystray
    from PIL import Image
    img = Image.open(icone_png).convert("RGBA").resize((64, 64), Image.NEAREST)
    menu = pystray.Menu(
        pystray.MenuItem("Mostrar", lambda i, it: mostrar(), default=True),
        pystray.MenuItem("Esconder", lambda i, it: esconder()),
        pystray.MenuItem("Sair", lambda i, it: (i.stop(), sair())),
    )
    icon = pystray.Icon("tamagoshi", img, "Tamagoshi Cripto", menu)
    try:
        if MAC:
            icon.run_detached()  # no Mac precisa ser na thread principal, junto do loop do Tk
        else:
            threading.Thread(target=icon.run, daemon=True).start()
    except Exception as e:  # menu bar é bônus; sem ela o bicho vive igual
        print("Bandeja indisponível:", e)
        return None
    return icon


# ---------------- iniciar com o sistema ----------------
def _argv_inicio():
    if getattr(sys, "frozen", False):  # .exe / .app do PyInstaller
        return [sys.executable]
    exe = Path(sys.executable)
    if WIN and exe.with_name("pythonw.exe").exists():
        exe = exe.with_name("pythonw.exe")
    return [str(exe), "-m", "tamagoshi_cripto"]


def autostart_suportado():
    return WIN or MAC


def autostart_ativo():
    if MAC:
        return PLIST_MAC.exists()
    if not WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
            winreg.QueryValueEx(k, NOME_RUN)
            return True
    except OSError:
        return False


def plist_mac():
    return {"Label": LABEL_MAC, "ProgramArguments": _argv_inicio(), "RunAtLoad": True,
            "KeepAlive": False, "ProcessType": "Interactive"}


def definir_autostart(ligar):
    """Windows: HKCU Run (sem admin). Mac: ~/Library/LaunchAgents/<label>.plist."""
    try:
        if MAC:
            if ligar:
                PLIST_MAC.parent.mkdir(parents=True, exist_ok=True)
                PLIST_MAC.write_bytes(plistlib.dumps(plist_mac()))
            elif PLIST_MAC.exists():
                PLIST_MAC.unlink()
            return True
        if not WIN:
            return False
        import winreg
        caminho = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, caminho, 0, winreg.KEY_SET_VALUE) as k:
            if ligar:
                cmd = " ".join(f'"{a}"' if " " in a else a for a in _argv_inicio())
                winreg.SetValueEx(k, NOME_RUN, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, NOME_RUN)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def nome_autostart():
    return "Abrir ao iniciar o Mac" if MAC else "Iniciar com o Windows"


def janela_sem_borda(root):
    """Tira a moldura da janela.

    No macOS, overrideredirect(True) cria uma janela que NUNCA vira "key window":
    o teclado some (onboarding, console, ajustes...). Lá usamos o estilo 'plain' do Tk,
    que também não tem borda mas aceita foco. Se o Tk for velho e não souber, cai no
    overrideredirect de sempre. Windows/Linux: nada muda.
    """
    if MAC:
        try:
            root.tk.call("::tk::unsupported::MacWindowStyle", "style", root._w, "plain", "none")
            return "mac-plain"
        except Exception:
            pass
    root.overrideredirect(True)
    return "override"


def focar_teclado(root, widget=None, atraso=80):
    """Traz a janela pra frente e pede o teclado (no Mac precisa de um after, senão o Cocoa ignora)."""
    def _f():
        try:
            root.lift()
            root.focus_force()
            (widget or root).focus_set()
        except Exception:
            pass
    if MAC:
        root.after(atraso, _f)
    else:
        _f()
