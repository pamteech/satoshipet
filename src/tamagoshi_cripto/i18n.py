"""i18n.py - pt-BR / EN dentro do app. O texto-fonte é o português (é a língua da casa 🇧🇷).

Como funciona: TODO texto desenhado passa por `_txt`, que chama `t()`. Se o idioma for EN,
procura a tradução exata; senão tenta os prefixos (pra textos com número no fim); senão
deixa em português mesmo (melhor um "garimpando" perdido do que um crash).
Idioma: cfg["idioma"] = "auto" (detecta pelo sistema) | "pt" | "en".
"""
from __future__ import annotations

import locale
import os

IDIOMAS = ("auto", "pt", "en")
NOMES = {"auto": "auto", "pt": "português", "en": "English"}
_atual = "pt"


def _idioma_mac() -> str:
    """App aberto pelo Finder não herda LANG: pergunta direto pro macOS (ex.: "pt-BR")."""
    import sys
    if sys.platform != "darwin":
        return ""
    import subprocess
    for chave in ("AppleLanguages", "AppleLocale"):
        try:
            r = subprocess.run(["defaults", "read", "-g", chave], capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            continue
        v = r.stdout.replace("(", "").replace('"', "").strip().split(",")[0].strip()
        if v:
            return v
    return ""


def detectar() -> str:
    """pt se o sistema falar português, en pro resto do mundo."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(var)
        if v:
            return "pt" if v.lower().startswith("pt") else "en"
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    if not loc:
        loc = _idioma_mac()
    return "pt" if loc.lower().startswith(("pt", "portuguese")) else "en"


def definir(escolha: str | None) -> str:
    global _atual
    _atual = detectar() if escolha in (None, "", "auto") else ("en" if escolha == "en" else "pt")
    return _atual


def atual() -> str:
    return _atual


def t(texto: str) -> str:
    if _atual == "pt" or not texto:
        return texto
    if texto in EN:
        return EN[texto]
    for pt, en in PREFIXOS:
        if texto.startswith(pt):
            return en + texto[len(pt):]
    return texto


PREFIXOS = [
    ("vazio = ", "empty = "), ("recorde: ", "record: "), ("modo hardcore: ", "hardcore mode: "),
    ("patrocínio: ", "sponsor: "), ("skin: ", "skin: "), ("unidade: ", "unit: "), ("moeda trocada: ", "coin changed: "),
    ("comprou ", "bought "), ("vendeu ", "sold "), ("você não tem ", "you don't have "),
    ("saldo fictício insuficiente", "not enough fake balance"), ("HARDCORE: morre em ~", "HARDCORE: dies in ~"),
    ("SALDO ", "BALANCE "), ("Tamanho ", "Size "), ("nível ", "level "), ("idioma: ", "language: "),
]

EN = {
    # ---- menu ----
    "Trocar moeda": "Change coin", "Trocar skin": "Change skin", "Ajustes... (S)": "Settings... (S)",
    "Conquistas": "Achievements", "Console hacker (`)": "Hacker console (`)",
    "Compartilhar card (X)": "Share card (X)", "Brincar: Pega os Sats (P)": "Play: Catch the Sats (P)",
    "Genética e batalhas": "Genetics & battles", "Copiar meu código de pet": "Copy my pet code",
    "Cruzar com código de amigo...": "Breed with a friend's code...", "Estábulo (console: stable)": "Stable (console: stable)",
    "Batalhar contra IA": "Battle the AI", "Batalhar contra código de amigo...": "Battle a friend's code...",
    "Modo hardcore (pode morrer!)": "Hardcore mode (can die!)", "Cemitério de Honra": "Hall of Honor graveyard",
    "Mercado": "Market", "Corretora de mentirinha (paper trading)": "Pretend broker (paper trading)",
    "Carteiras ETH/SOL watch-only...": "ETH/SOL watch-only wallets...",
    "Alerta de baleia (mempool.space)": "Whale alert (mempool.space)", "Manchetes RSS no balão": "RSS headlines in bubble",
    "Loja de skins": "Skin shop", "Abrir loja de skins": "Open skin shop", "Resgatar código...": "Redeem code...",
    "Overlay de streamer (OBS + Twitch)...": "Streamer overlay (OBS + Twitch)...",
    "Ajuda": "Help", "Rever introdução": "Replay intro", "Procurar atualização": "Check for updates",
    "Enviar relatório de erro...": "Send error report...", "Mostrar em sats": "Show in sats", "Mudo": "Mute",
    "Esconder (bandeja)": "Hide (tray)", "Ativar Pro": "Activate Pro", "Pro ativo": "Pro active", "Sair": "Quit",
    "Iniciar com o sistema": "Start with system",
    # ---- cenas ----
    "ESCOLHA SUA MOEDA": "PICK YOUR COIN", "< > escolhe - ENTER confirma": "< > pick - ENTER confirms",
    "QUAL O NOME DELE?": "WHAT'S ITS NAME?", "ENTER confirma": "ENTER confirms", "DICAS RÁPIDAS": "QUICK TIPS",
    "SUAS ESCOLHAS": "YOUR CHOICES", "tudo opcional, muda depois no menu": "all optional, change later in settings",
    "NASCEU! gm, fren!": "IT HATCHED! gm, fren!", "Pro na janela (grátis no --tui)": "Pro in window (free in --tui)",
    "USAR BTC": "USE BTC", "carinho (+XP)": "pet it (+XP)", "CRASE `": "BACKTICK `", "console hacker": "hacker console",
    "BOTÃO DIR.": "RIGHT CLICK", "menu de tudo": "menu of everything", "mini-game: pega sats": "mini-game: catch sats",
    "move o widget": "move the widget", "TEM ALGUÉM AÍ DENTRO!": "SOMEONE'S IN THERE!", "SONS 8-BIT": "8-BIT SOUNDS",
    "jingles chiptune (S)": "chiptune jingles (S)", "apelido + stats, anônimo (R)": "nickname + stats, anonymous (R)",
    "sem servidor (ver config)": "no server (see settings)", "BATIZAR": "NAME IT", "BELEZA": "COOL", "COMEÇAR!": "START!",
    "ENTENDI": "GOT IT", "VAMOS!": "LET'S GO!", "LINDO!": "CUTE!", "PULAR": "SKIP", "SAIR": "EXIT", "OK": "OK",
    "< > pega sats - evita FUD": "< > catch sats - dodge FUD", "FIM DE JOGO!": "GAME OVER!",
    "CEMITÉRIO DE HONRA": "HALL OF HONOR", "ninguém morreu (ainda)": "nobody died (yet)", "RENASCER DO OVO": "REBORN FROM EGG",
    "LABORATÓRIO DE DNA": "DNA LAB", "CORRETORA DE MENTIRINHA": "PRETEND BROKER", "LOJA DE SKINS": "SKIN SHOP",
    "nenhum pacote disponível": "no packs available", "EM USO": "IN USE", "USAR": "USE", "CÓDIGO": "CODE",
    "VENDER": "SELL", "VIDA": "LIFE", "PATROCINADO": "SPONSORED", "preço real, dinheiro de mentira": "real price, fake money",
    "DINHEIRO FICTÍCIO": "FAKE MONEY", "COMPRAR A QUEDA ANTES\nQUE ELE MORRA!": "BUY THE DIP BEFORE\nIT DIES!",
    "esperando bloco... zzz": "waiting for a block... zzz", "sem preço ainda": "no price yet",
    "sem preço ainda (espera a API)": "no price yet (wait for the API)", " sats pegos": " sats caught",
    "CONQUISTA!": "ACHIEVEMENT!", "ALERTA!": "ALERT!",
    # ---- ajustes ----
    "AJUSTES": "SETTINGS", "GERAL": "MAIN", "VISUAL": "LOOK", "GRANA": "MONEY", "CONTA": "ACCT", "SOBRE": "ABOUT",
    "Idioma": "Language", "Moeda": "Coin", "Skin": "Skin", "Nome do bicho": "Pet name", "Mostrar em sats ": "Show in sats ",
    "Som": "Sound", "Música": "Music", "Iniciar c/ sistema": "Start w/ system", "Tamanho": "Size",
    "Alto contraste": "High contrast", "Paleta dia/noite": "Day/night palette", "Chapéus de época": "Seasonal hats",
    "Tremidinha": "Screen shake", "Efeito CRT": "CRT effect", "Limite MOON %": "MOON threshold %",
    "Limite REKT %": "REKT threshold %", "Alerta acima $": "Alert above $", "Alerta abaixo $": "Alert below $",
    "Baleias": "Whales", "Manchetes RSS": "RSS headlines", "Hardcore": "Hardcore", "Carteira BTC": "BTC wallet",
    "Licença": "License", "E-mail": "E-mail", "Chave": "Key", "ATIVAR PRO": "ACTIVATE PRO", "Ranking": "Leaderboard",
    "Servidor": "Server", "Apelido": "Nickname", "IA (BYO)": "AI (BYO)", "Avisar versão nova": "Notify new version",
    "API local": "Local API", "Versão": "Version", "Rever intro": "Replay intro", "Atualização": "Update",
    "Relatório de erro": "Error report", "Privacidade": "Privacy", "ligado": "on", "desligado": "off",
    "nenhuma": "none", "ativa": "active", "grátis": "free", "PROCURAR": "CHECK", "ABRIR": "OPEN", "VER": "VIEW",
    "ENVIAR": "SEND", "DESLIGAR": "TURN OFF", "ENTER salva - ESC cancela": "ENTER saves - ESC cancels",
    "TAB/setas - ENTER muda - ESC sai": "TAB/arrows - ENTER - ESC exits",
    "salvo!": "saved!", "precisa do Pro": "needs Pro", "valor inválido": "invalid value",
    "nada sai do seu PC sem você ligar": "nothing leaves your PC unless you opt in",
    "Carteira ETH": "ETH wallet", "Carteira SOL": "SOL wallet", "Saldo em": "Balance in", "Esconder saldo": "Hide balance",
    "MARCO!": "MILESTONE!", "carteira cresceu!": "wallet grew!", "Código da loja": "Shop code", "Canal Twitch": "Twitch channel",
    "Servidor + Apelido": "Server + Nickname", "INFO": "INFO", "CONQUISTAS": "ACHIEVEMENTS", "OPS": "OOPS",
    "CÓDIGO DO PET": "PET CODE", "ATUALIZAÇÕES": "UPDATES", "RELATÓRIO": "REPORT", "PERIGO!": "DANGER!",
    "NOVA VERSÃO!": "NEW VERSION!", "ALERTA DE BALEIA": "WHALE ALERT", "LICENÇA": "LICENSE",
    "chat da Twitch desligado": "Twitch chat off", "canal inválido (a-z, 0-9, _)": "invalid channel (a-z, 0-9, _)",
    "carteira removida": "wallet removed", "preencha e-mail e chave": "fill in e-mail and key",
    "código copiado! manda pro amigo": "code copied! send it to a friend",
    "cole o código do amigo (Ctrl+V) e ENTER": "paste your friend's code (Ctrl+V) and ENTER",
    "abri no navegador. nada foi enviado sozinho": "opened in browser. nothing was sent automatically",
    # ---- frases do bicho (arts) ----
    "TO THE MOON!": "TO THE MOON!", "ser, isso é alpha": "ser, this is alpha", "aped in": "aped in",
    "21 milhões e nem um a mais": "21 million and not one more", "gas tá caro, vou de L2": "gas is pricey, going L2",
    "o merge mudou minha vida": "the merge changed my life", "approve ilimitado? confia": "unlimited approve? trust me",
    "a rede caiu? não, foi só um soluço": "network down? nah, just a hiccup", "400ms por slot, bebê": "400ms per slot, baby",
    "meme coin nova a cada bloco": "new meme coin every block", "to the moon (literalmente)": "to the moon (literally)",
    "ngmi? não, WAGMI": "ngmi? no, WAGMI", "rug ou moon, sem meio-termo": "rug or moon, no in-between",
    "comprei o topo de novo, ser": "bought the top again, ser", "compra no topo, vende no fundo": "buy high, sell low",
    "lateralizou... hora do café": "sideways... coffee time", "DCA é amor, DCA é vida": "DCA is love, DCA is life",
    "não é conselho financeiro, hein": "not financial advice, ok?", "minerando paciência...": "mining patience...",
    "o gráfico tá de lado, eu também": "chart's sideways, so am I", "LAMBO OU NADA!": "LAMBO OR BUST!",
    "eu sempre soube! (mentira)": "I always knew! (lie)", "vendi cedo demais de novo?": "sold too early again?",
    "comprei no fundo, sou gênio": "bought the bottom, I'm a genius", "próxima parada: Marte": "next stop: Mars",
    "é só uma correção saudável...": "just a healthy correction...", "HODL até o fim": "HODL to the end",
    "a culpa é das baleias": "blame the whales", "volta pro miojo, bora": "back to instant noodles",
    "isso é desconto, né? né??": "it's a discount, right? right??", "comprei no topo, clássico": "bought the top, classic",
    "hehe, cócegas!": "hehe, tickles!", "valeu pelo apoio moral": "thanks for the moral support",
    "carinho não paga gas, mas ajuda": "pets don't pay gas, but they help", "WEEE! mais um pump!": "WEEE! another pump!",
    "toca aqui, baleia!": "high five, whale!", "te amo mais que lambo": "love you more than a lambo",
    "obrigado... precisava": "thanks... I needed that", "um abraço vale mais que USDT": "a hug is worth more than USDT",
    "não me vende, por favor": "please don't sell me", "garimpando": "mining",
}
