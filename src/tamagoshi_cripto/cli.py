"""cli.py - `tamagoshi` na linha de comando. Rode `tamagoshi --help`."""
import argparse
import sys

from . import __version__, config


def parser():
    p = argparse.ArgumentParser(
        prog="tamagoshi",
        description="Tamagoshi Cripto: um bichinho em pixel art que sente o mercado cripto.",
        epilog="Config: ~/.tamagoshi_cripto.json (ou $TAMAGOSHI_CONFIG). Skins: ~/.tamagoshi_cripto/skins/")
    p.add_argument("--tui", action="store_true", help="roda no terminal (half-blocks unicode, truecolor)")
    p.add_argument("--coin", choices=list(config.MOEDAS), help="moeda (fora BTC exige Pro na janela)")
    p.add_argument("--skin", help="padrao, cyberpunk, gato, sapo, plugin:<id> ...")
    p.add_argument("--scale", type=int, choices=range(1, 7), metavar="1-6", help="zoom do sprite (padrão 3)")
    p.add_argument("--crt", action="store_true", help="liga scanlines estilo CRT")
    p.add_argument("--mute", action="store_true", help="sem sons")
    p.add_argument("--config", help="caminho alternativo do JSON de config")
    p.add_argument("--skins-dir", help="pasta extra com skins da comunidade")
    p.add_argument("--skip-intro", action="store_true", help="pula o onboarding (ovo chocando)")
    p.add_argument("--no-update-check", action="store_true", help="não pergunta pro GitHub se há versão nova")
    p.add_argument("--no-tray", action="store_true", help="não cria ícone na bandeja/menu bar")
    p.add_argument("--no-api", action="store_true", help="desliga a API local http://127.0.0.1:8737/status")
    p.add_argument("--status", action="store_true", help="imprime o JSON de uma instância rodando e sai")
    p.add_argument("--frames", type=int, default=0, help="(TUI) sai depois de N frames; útil pra testes")
    p.add_argument("--list-skins", action="store_true", help="lista skins disponíveis e sai")
    p.add_argument("--version", action="version", version=f"tamagoshi-cripto {__version__}")
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    if a.config:
        from pathlib import Path
        config.CONFIG_PATH = Path(a.config).expanduser()
    opcoes = {"moeda": a.coin, "skin": a.skin, "escala": a.scale, "crt": True if a.crt else None,
              "mudo": True if a.mute else None, "skins_dir": a.skins_dir, "sem_tray": a.no_tray,
              "sem_onboarding": a.skip_intro, "sem_updates": a.no_update_check,
              "sem_api": a.no_api}
    if a.status:
        import urllib.request
        from . import api
        try:
            print(urllib.request.urlopen(f"http://127.0.0.1:{api.PORTA}/status", timeout=3).read().decode())
            return 0
        except OSError:
            print("nenhum tamagoshi rodando (ou API desligada)", file=sys.stderr)
            return 1
    if a.list_skins:
        from . import arts, plugins
        print("Embutidas:", ", ".join(arts.SKINS_DISPONIVEIS))
        for pid, meta in plugins.descobrir(a.skins_dir).items():
            print(f"  {pid:<20} {meta['nome']} (por {meta['autor']})")
        return 0
    if a.tui:
        from . import tui
        return tui.rodar(opcoes, frames=a.frames)
    from .main import Tamagoshi
    Tamagoshi(opcoes).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
