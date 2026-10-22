# arts.py - personalidade do bicho: nomes, cores, títulos e as frases de trader.
# (Os desenhos agora são pixel art em sprites.py -> assets/sprites/*.png)
import random

ESTADOS = ("garimpando", "moon", "rekt")
TITULOS = {"garimpando": "GARIMPANDO", "moon": "TO THE MOON!", "rekt": "REKT!"}
CORES = {"garimpando": "#f7931a", "moon": "#00ff88", "rekt": "#ff4d4d"}
NOMES = {"BTC": "Satoshinho", "ETH": "Vitalikinho", "SOL": "Solzinho",
         "DOGE": "Doguinho", "PEPE": "Sapo Degen"}
SKINS_DISPONIVEIS = ["padrao", "cyberpunk", "gato", "sapo"]  # + "satoshi" (secreta) + plugins

# frases de lore por moeda (misturadas com as gerais)
LORE = {
    "BTC": ["not your keys, not your coins", "tick tock, next block", "21 milhões e nem um a mais",
            "1 BTC = 1 BTC"],
    "ETH": ["gas tá caro, vou de L2", "ultrasound money!", "o merge mudou minha vida",
            "approve ilimitado? confia"],
    "SOL": ["a rede caiu? não, foi só um soluço", "400ms por slot, bebê", "meme coin nova a cada bloco"],
    "DOGE": ["much wow", "very hodl", "such community", "to the moon (literalmente)"],
    "PEPE": ["ngmi? não, WAGMI", "rug ou moon, sem meio-termo", "gm gm gm", "comprei o topo de novo, ser"],
}
DEGEN = ["ser, isso é alpha", "few understand", "probably nothing", "aped in", "wen lambo?",
         "gm", "ngmi", "LFG!!!", "diamond hands 💎"]

# Doguinho tem legenda própria, porque doge sem legenda não é doge
LEGENDAS_DOGE = {"garimpando": "such work. wow", "moon": "much wow. very moon",
                 "rekt": "such loss. much cry"}

FRASES = {
    "garimpando": ["compra no topo, vende no fundo", "lateralizou... hora do café",
                   "DCA é amor, DCA é vida", "não é conselho financeiro, hein",
                   "minerando paciência...", "o gráfico tá de lado, eu também"],
    "moon": ["LAMBO OU NADA!", "eu sempre soube! (mentira)", "vendi cedo demais de novo?",
             "WAGMI!!!", "comprei no fundo, sou gênio", "próxima parada: Marte"],
    "rekt": ["é só uma correção saudável...", "HODL até o fim", "a culpa é das baleias",
             "volta pro miojo, bora", "isso é desconto, né? né??", "comprei no topo, clássico"],
}


def frase(estado, moeda=None, extras=None):
    """Sorteia uma frase: estado + lore da moeda + degen + frases do plugin."""
    if moeda == "DOGE" and random.random() < 0.3:
        return LEGENDAS_DOGE[estado]
    pool = list(FRASES[estado])
    if extras:
        pool += extras.get(estado, [])
    r = random.random()
    if r < 0.25 and moeda in LORE:
        pool = LORE[moeda]
    elif r < 0.33:
        pool = [d for d in DEGEN if "💎" not in d]
    return random.choice(pool)


# reações ao carinho (clique no bicho)
REACOES = {
    "garimpando": ["hehe, cócegas!", "valeu pelo apoio moral", "carinho não paga gas, mas ajuda"],
    "moon": ["WEEE! mais um pump!", "toca aqui, baleia!", "te amo mais que lambo"],
    "rekt": ["obrigado... precisava", "um abraço vale mais que USDT", "não me vende, por favor"],
}


def reacao(estado):
    return random.choice(REACOES[estado])
