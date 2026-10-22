"""console.py - o terminal hacker do bicho (abre com ` na janela, ou : no modo --tui).

O interpretador é puro: recebe um "contexto" (o app ou a TUI) que expõe status() e ações,
e devolve linhas de texto. A linha especial SPRITE vira o próprio sprite no neofetch.
"""
import random
import shlex

from . import __version__, lore, onchain

SPRITE = "\0SPRITE"
FED = ["Jerome P.", "a impressora do Fed", "o QE infinito", "o comitê do FOMC", "a taxa Selic (?)"]

AJUDA = [
    "comandos:",
    "  help            esta ajuda",
    "  price           preço e variação",
    "  feed            dá um bloco pro bicho",
    "  pet             faz carinho",
    "  stats           vida, xp, nível, fome",
    "  mempool         fees e tamanho da mempool",
    "  halving         contagem regressiva",
    "  fng             fear & greed index",
    "  hashrate        poder de hash da rede",
    "  gas             gas do ETH (gwei)",
    "  wallet [addr]   carteira watch-only",
    "  sats            alterna USD/sats",
    "  skin <x>        troca skin",
    "  coin <x>        troca moeda",
    "  neofetch        info do sistema (do bicho)",
    "  share           card PNG + post pronto no X",
    "  play            mini-game: pega os sats (20s)",
    "  update          procura versão nova (só avisa)",
    "  rank [on <nick>|off]  leaderboard (opt-in)",
    "  genes           DNA do bicho e raridade",
    "  petcode         seu código de pet (copia)",
    "  breed <n|code>  cruza com pet do estábulo/amigo",
    "  stable / adopt <n>  estábulo de pets",
    "  battle [code]   batalha (vs IA ou amigo)",
    "  hardcore on|off modo hardcore (pode morrer!)",
    "  rip             Cemitério de Honra",
    "  clear / exit",
]


class Console:
    def __init__(self, ctx):
        self.ctx = ctx
        self.historico = []

    def executar(self, linha):
        linha = linha.strip()
        if not linha:
            return []
        self.historico.append(linha)
        try:
            partes = shlex.split(linha)
        except ValueError:
            partes = linha.split()
        cmd, args = partes[0].lower(), partes[1:]
        if linha.replace(" ", "") in ("rm-rf/", "sudorm-rf/", "rm-rf/*", "sudorm-rf/*"):
            self.ctx.panico()
            return ["rm: removendo /...", "rm: removendo /blockchain...", "AAAAAAAAA SOCORRO",
                    "...brincadeira. não existe rm -rf na blockchain.", "imutabilidade, bebê. (ctrl+z ativado)"]
        if cmd == "sudo":
            if args[:1] == ["moon"]:
                self.ctx.sudo_moon()
                return ["[sudo] senha para satoshi: ********", "permissão concedida. ativando modo lua...",
                        "isso não muda o preço real. infelizmente."]
            return [f"satoshi não está no arquivo sudoers. este incidente será reportado ao Fed."]
        if cmd == "git" and args[:1] == ["blame"]:
            return [f"^1f3d2a ({random.choice(FED)} 2008-10-31) inflação += 'transitória'",
                    f"^b10c4d ({random.choice(FED)} 2020-03-15) money_printer.go(brrrr=True)",
                    "^000000 (Satoshi Nakamoto 2009-01-03) The Times 03/Jan/2009 Chancellor..."]
        fn = getattr(self, "cmd_" + cmd, None)
        if not fn:
            return [f"{cmd}: comando não encontrado. tenta 'help'"]
        try:
            return fn(args)
        except Exception as e:  # rede caiu, API morreu... o console não pode morrer junto
            return [f"erro: {e}"]

    # ---------------- comandos ----------------
    def cmd_help(self, a):
        return list(AJUDA)

    def cmd_price(self, a):
        s = self.ctx.status()
        linhas = [f"{s['moeda']}: {s['preco_fmt']} ({s['variacao_pct']:+.2f}%) -> {s['humor']}"]
        if s["btc"].get("sats_por_dolar"):
            linhas.append(f"moscow time: 1 USD = {s['btc']['sats_por_dolar']:,} sats".replace(",", "."))
        return linhas

    def cmd_feed(self, a):
        return [self.ctx.alimentar()]

    def cmd_pet(self, a):
        return [self.ctx.carinho() or "<3"]

    def cmd_stats(self, a):
        s = self.ctx.status()
        return [f"nome: {s['nome']}  estágio: {s['estagio']}",
                f"nível {s['nivel']}  xp {s['xp']} ({s['xp_pct']:.0%} pro próximo)",
                f"vida {s['vida']:.1f}/10  fome: {s['btc'].get('fome', '?')}",
                f"blocos comidos: {s['btc'].get('comidos', 0)}  crashes: {s['crashes']}",
                f"conquistas: {s['conquistas']}"]

    def cmd_mempool(self, a):
        f = onchain.fees()
        m = onchain.mempool()
        return [f"fees (sat/vB): rápido {f['fastestFee']} | 30min {f['halfHourFee']} | 1h {f['hourFee']} | eco {f['economyFee']}",
                f"mempool: {m['count']:,} txs, {m['vsize'] / 1e6:.1f} MvB".replace(",", "."),
                f"fome do bicho: {onchain.fome_por_fee(f['halfHourFee'])[1]}"]

    def cmd_halving(self, a):
        altura = self.ctx.status()["btc"].get("bloco") or onchain.ultimo_bloco()[0]
        faltam, dias, n = lore.halving(altura)
        return [f"bloco atual: {altura:,}".replace(",", "."),
                f"halving #{n} em {faltam:,} blocos (~{dias:.0f} dias)".replace(",", "."),
                "recompensa vai cair pela metade. tick tock, next block."]

    def cmd_fng(self, a):
        v, rot = lore.fear_greed()
        barra = "#" * (v // 5) + "." * (20 - v // 5)
        return [f"fear & greed: {v}/100 {rot}", f"[{barra}]"]

    def cmd_hashrate(self, a):
        return [f"hashrate da rede: {onchain.formatar_hashrate(onchain.hashrate())}",
                "o bicho contribui com 0 H/s, mas com muito amor."]

    def cmd_gas(self, a):
        g = onchain.gas_eth()
        return [f"ETH gas: {g:.2f} gwei", onchain.humor_gas(g)]

    def cmd_wallet(self, a):
        if not a:
            return self.ctx.carteira(None)
        return self.ctx.carteira(a[0])

    def cmd_sats(self, a):
        return [self.ctx.alternar_sats()]

    def cmd_skin(self, a):
        if not a:
            return ["skins: " + ", ".join(self.ctx.skins())]
        r = self.ctx.trocar_skin(a[0])
        return [r or f"skin: {a[0]} (se for Pro, destrave no menu)"]

    def cmd_play(self, a):
        f = getattr(self.ctx, "brincar", None)
        return f() if f else ["mini-game só na janela (por enquanto)"]

    def cmd_update(self, a):
        from . import __version__, updates
        info = updates.checar()
        if not info:
            return [f"v{__version__}: nada novo (ou offline / repo ainda placeholder)"]
        return [f"nova versão v{info['versao']}!", info["url"], "(nada é instalado sozinho: baixe quando quiser)"]

    def cmd_share(self, a):
        return self.ctx.compartilhar()

    def cmd_rank(self, a):
        return self.ctx.ranking(a)

    # ---- v1.4: genética, batalha, hardcore ----
    def _so_janela(self, nome, *args):
        f = getattr(self.ctx, nome, None)
        return f(*args) if f else ["isso só funciona na janela (por enquanto)"]

    def cmd_genes(self, a):
        from . import genetica
        st = self.ctx.status()
        g = st.get("genes") or {}
        if not g:
            return ["sem DNA (?!)"]
        return [f"{k:<10} {v}" for k, v in g.items()] + [f"raridade   {st.get('raridade', '?')}"]

    def cmd_petcode(self, a):
        r = self._so_janela("petcode")
        return [r, "(copiado! manda pro amigo: breed/battle <código>)"] if isinstance(r, str) else r

    def cmd_breed(self, a):
        return self._so_janela("cruzar", " ".join(a)) if a else ["uso: breed <n do estábulo | TAMA1-...>"]

    def cmd_stable(self, a):
        return self._so_janela("estabulo")

    def cmd_adopt(self, a):
        return self._so_janela("adotar", a[0] if a else "")

    def cmd_battle(self, a):
        return self._so_janela("batalhar", " ".join(a) or None)

    def cmd_hardcore(self, a):
        if a[:1] not in (["on"], ["off"]):
            return ["uso: hardcore on|off  (on = o bicho pode MORRER de abandono)"]
        f = getattr(self.ctx, "cfg", None)
        if f is None:
            return ["só na janela"]
        if bool(f.get("hardcore")) == (a[0] == "on"):
            return ["já tá assim"]
        return self.ctx.alternar_hardcore()

    def cmd_rip(self, a):
        return self._so_janela("ver_cemiterio")

    cmd_cemiterio = cmd_rip

    def cmd_coin(self, a):
        if not a:
            return ["uso: coin BTC|ETH|SOL|DOGE|PEPE"]
        m = a[0].upper()
        if m not in ("BTC", "ETH", "SOL", "DOGE", "PEPE"):
            return [f"coin: {m}? isso aí é shitcoin demais até pra mim"]
        r = self.ctx.trocar_moeda(m)
        if r:
            return [r]
        return [f"moeda trocada: {m}" if self.ctx.status()["moeda"] == m else f"{m} é Pro (destrave no menu)"]

    def cmd_neofetch(self, a):
        s = self.ctx.status()
        return [SPRITE,
                f"satoshi@{s['nome'].lower().replace(' ', '-')}",
                "-" * 22,
                f"OS: Tamagoshi OS {__version__}",
                f"Host: {s['moeda']} mainnet",
                f"Kernel: proof-of-{'stake' if s['moeda'] == 'ETH' else 'work'}",
                f"Uptime: {s['uptime_min']} min",
                f"Shell: tamash 0.21M",
                f"Estágio: {s['estagio']} LV{s['nivel']}",
                f"Humor: {s['humor']}",
                f"Bloco: {s['btc'].get('bloco') or '?'}",
                f"Fee: {s['btc'].get('fee_sat_vb') or '?'} sat/vB",
                f"Vida: {'<3' * int(round(s['vida'] / 2))}"]

    def cmd_whoami(self, a):
        return ["satoshi (provavelmente não)"]

    def cmd_ls(self, a):
        return ["carteira.dat  seed_phrase.txt(mentira)  memes/  lambo_fund/  hopium.json"]

    def cmd_cat(self, a):
        if a and any(x in a[0].lower() for x in ("seed", "wallet", "key", "prv")):
            return ["boa tentativa. not your keys, not your coins."]
        return ["cat: miau"]

    def cmd_ping(self, a):
        return ["pong (latência: 1 bloco)"]
