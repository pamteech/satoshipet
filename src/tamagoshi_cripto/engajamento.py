"""engajamento.py - v1.4 fase 1: genes, cruzamento, batalhas e modo hardcore, plugados no app.

Mixin do Tamagoshi (main.py): tudo aqui roda na thread da GUI. Nada de rede, nada de blockchain:
o "código do pet" é só texto que você cola no zap do amigo.
"""
import random
import time
from tkinter import messagebox, simpledialog

from . import batalha, cenas, config, evolucao, genetica, hardcore

ADULTOS = ("adulto", "whale", "diamond")


class MixinEngajamento:
    # ---------- pet atual ----------
    def genes(self):
        g = self.cfg.get("genes")
        if not g:
            g = self.cfg["genes"] = genetica.aleatorio(moeda=self.cfg["moeda"])
        return g

    def pet_atual(self):
        return {"nome": self.nome_pet(), "genes": dict(self.genes(), moeda=self.cfg["moeda"]),
                "nivel": evolucao.nivel(self.evo.xp), "xp": self.evo.xp, "estagio": self.estagio}

    def petcode(self, copiar=True):
        cod = genetica.exportar(self.pet_atual())
        if copiar:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(cod)
            except Exception:
                pass
        return cod

    def _resolver_pet(self, arg):
        """'3' = pet do estábulo, 'TAMA1-...' = amigo. Retorna (pet, erro)."""
        arg = (arg or "").strip()
        if arg.isdigit():
            est = self.cfg.get("estabulo", [])
            i = int(arg) - 1
            return (est[i], None) if 0 <= i < len(est) else (None, f"estábulo não tem o #{arg} (veja 'stable')")
        return genetica.importar(arg)

    # ---------- estábulo / cruzamento ----------
    def estabulo(self):
        est = self.cfg.get("estabulo", [])
        if not est:
            return ["estábulo vazio. 'breed <código>' com o pet de um amigo bota um ovo aqui"]
        out = []
        for i, p in enumerate(est, 1):
            r, _ = genetica.raridade(p["genes"])
            out.append(f"#{i} {p['nome']:<12} {p['genes'].get('moeda', 'BTC')} {p.get('estagio', 'ovo'):<7} "
                       f"LV{p.get('nivel', 1)} {r}")
        return out + ["'adopt <n>' troca o bicho ativo (o atual vai pro estábulo)"]

    def cruzar(self, arg, mostrar=True, semente=None):
        if self.cfg.get("fantasma"):
            return ["fantasma não cruza. renasça primeiro (menu > Genética > Cemitério)"]
        if self.estagio not in ADULTOS:
            return [f"seu bicho precisa ser adulto pra cruzar (agora: {evolucao.NOMES[self.estagio]})"]
        outro, erro = self._resolver_pet(arg)
        if erro:
            return [erro]
        if outro.get("estagio", "ovo") not in ADULTOS:
            return [f"{outro['nome']} ainda não é adulto"]
        filho, mutou = genetica.cruzar(self.pet_atual()["genes"], outro["genes"], semente=semente)
        n = len(self.cfg.setdefault("estabulo", [])) + 1
        ovo = {"nome": f"Filhote{n}", "genes": filho, "nivel": 1, "xp": 0, "estagio": "ovo",
               "pais": [self.nome_pet(), outro["nome"]]}
        self.cfg["estabulo"].append(ovo)
        self.cfg["estabulo"] = self.cfg["estabulo"][-20:]
        config.salvar(self.cfg)
        if mostrar:
            self.console_aberto = False
            self.cena = cenas.Cruzamento(self, self.pet_atual(), outro, filho, mutou)
        r, _ = genetica.raridade(filho)
        return [f"um ovo {r.upper()}! foi pro estábulo como #{len(self.cfg['estabulo'])}"] + \
            ([f"mutação em: {', '.join(mutou)}"] if mutou else [])

    def adotar(self, arg):
        est = self.cfg.get("estabulo", [])
        if not arg.isdigit() or not 0 < int(arg) <= len(est):
            return ["uso: adopt <n> (veja 'stable')"]
        novo = est.pop(int(arg) - 1)
        if not self.cfg.get("fantasma"):
            est.append(self.pet_atual())
        self.cfg["genes"] = novo["genes"]
        self.cfg["nome_pet"] = novo["nome"]
        if novo["genes"].get("moeda") in self._moedas_liberadas():
            self.cfg["moeda"] = novo["genes"]["moeda"]
        self._recomecar_vida(xp=novo.get("xp", 0))
        return [f"{novo['nome']} agora é o seu bicho!"]

    def _moedas_liberadas(self):
        return list(config.MOEDAS) if self.pro else ["BTC"]

    # ---------- batalha ----------
    def batalhar(self, arg=None, semente=None, auto=False):
        if self.cfg.get("fantasma"):
            return ["fantasma não luta (atravessa os golpes, não vale)"]
        if arg:
            rival, erro = self._resolver_pet(arg)
            if erro:
                return [erro]
        else:
            rival = batalha.rival_ia(evolucao.nivel(self.evo.xp), semente, self.cfg["moeda"])
        preco = self.precos.get(self.cfg["moeda"])
        var = self._variacao(self.cfg["moeda"], preco) if preco else 0.0
        mr = (rival.get("genes") or {}).get("moeda")
        pr = self.precos.get(mr)
        var_r = self._variacao(mr, pr) if pr else 0.0
        self.console_aberto = False
        self.cena = cenas.Batalha(self, self.pet_atual(), rival, var, var_r, semente, auto)
        self._tocar()
        return [f"batalha contra {rival['nome']}! 1-4 escolhe o golpe"]

    def fim_batalha(self, ganhou, rival):
        b = self.cfg.setdefault("batalhas", {"vitorias": 0, "derrotas": 0})
        b["vitorias" if ganhou else "derrotas"] = b.get("vitorias" if ganhou else "derrotas", 0) + 1
        self._ganhar_xp("jogo", 40 if ganhou else 10)
        self.som.tocar("conquista" if ganhou else "rekt")
        if ganhou:
            self.juice.emitir("moon", self.LARG // 2, 120, 2)
        self.frase_atual = f"ganhei de {rival['nome']}! gg" if ganhou else f"{rival['nome']} me deu rug... revanche?"
        self._salvar_progresso()

    # ---------- hardcore ----------
    def _tocar(self):
        hardcore.tocar(self.cfg)

    def alternar_hardcore(self, var=None):
        ligar = bool(var.get()) if var is not None else not self.cfg.get("hardcore")
        if ligar and not self.op.get("sem_confirmar") and not messagebox.askyesno(
                "Modo hardcore", "No modo hardcore o bicho pode MORRER:\n"
                f"vida zerada por {hardcore.MORTE_MIN} min + {hardcore.ABANDONO_H} h sem carinho.\n"
                "Ele vira fantasma e vai pro Cemitério de Honra. Ligar?", parent=self.root):
            if var is not None:
                var.set(False)
            return ["ufa. covarde, mas vivo"]
        self.cfg["hardcore"] = ligar
        self._tocar()
        config.salvar(self.cfg)
        return ["HARDCORE LIGADO. cuide bem dele." if ligar else "hardcore desligado. ninguém morre (por enquanto)"]

    def checar_hardcore(self):
        if hardcore.checar(self.cfg, self.conq.vida):
            self.morrer()
            return True
        aviso = hardcore.risco(self.cfg, self.conq.vida)
        if aviso and random.random() < .3 and not self.toast:
            self.toast = [aviso, 22, "PERIGO!"]
        return False

    def morrer(self):
        reg = hardcore.lapide(self.cfg, self.nome_pet(), self.status())
        hardcore.enterrar(self.cfg, reg)
        self.cache_sprites.clear()
        self.som.tocar("rekt")
        self.frase_atual = "buuu... (sou um fantasma agora)"
        self.toast = [f"{reg['nome']} descansa em paz", 30, "R.I.P."]
        self._salvar_progresso()
        return reg

    def renascer(self):
        if not self.cfg.get("fantasma"):  # só fantasma renasce; vivo não perde XP por clique errado
            return ["ele tá vivinho, não precisa renascer"]
        self.cfg["fantasma"] = False
        self.cfg["genes"] = genetica.aleatorio(moeda=self.cfg["moeda"])
        self._recomecar_vida(xp=0)
        self.frase_atual = "...gm? (nasci de novo!)"
        self.som.tocar("eclodir")
        return ["um ovo novinho. dessa vez faz carinho, hein"]

    def _recomecar_vida(self, xp=0):
        self.evo = evolucao.Evolucao({"xp": xp})
        self.conq.d["vida"] = 6.0  # começa como qualquer bicho novo
        self.conq.d["crashes"] = 0
        self.estagio = evolucao.estagio(self.evo.xp, 0)
        self.cfg["nasceu_em"] = int(time.time())
        self._tocar()
        self.cache_sprites.clear()
        self._salvar_progresso()

    def ver_cemiterio(self):
        self.console_aberto = False
        self.cena = cenas.Cemiterio(self)
        self._desenhar()
        return [f"{len(self.cfg.get('cemiterio', []))} lápide(s) no Cemitério de Honra"]

    # ---------- v1.4 fase 3: IA BYO, export, card ----------
    def salvar_cfg(self):
        config.salvar(self.cfg)

    def perguntar_ia(self, pergunta):
        import threading
        from . import ai
        ctx = {k: v for k, v in self.status().items() if k in ("moeda", "humor", "variacao_pct", "nivel")}

        def tarefa():
            resp = ai.perguntar(pergunta, self.cfg, ctx)
            with self.lock:
                self.eventos.append(("console", ["bicho: " + resp]))
        threading.Thread(target=tarefa, daemon=True).start()

    def _pasta_saida(self):
        from pathlib import Path
        p = Path.home() / "Pictures"
        return p if p.exists() else Path.home()

    def exportar_stats(self):
        import json
        from . import __version__, cartao
        s = cartao.exportar_stats(self.status(), __version__)
        arq = self._pasta_saida() / "tamagoshi-stats.json"
        arq.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        return [f"stats salvos: {arq}", "só campos públicos (sem carteira/e-mail/licença).",
                "suba no seu repo de perfil + .github/workflows/profile-card.yml (docs/PROFILE_CARD.md)"]

    def gerar_card(self):
        from . import cartao
        s = cartao.exportar_stats(self.status())
        arq = self._pasta_saida() / "tamagoshi-card.svg"
        arq.write_text(cartao.svg(s), encoding="utf-8")
        cartao.png(s).save(arq.with_suffix(".png"))
        return [f"card: {arq} (+ .png)", "API local também serve: http://127.0.0.1:8737/card.svg"]

    # ---------- menu ----------
    def menu_genetica(self, m):
        import tkinter as tk
        mg = tk.Menu(m, tearoff=0)
        mg.add_command(label="Copiar meu código de pet", command=self._menu_petcode)
        mg.add_command(label="Cruzar com código de amigo...", command=lambda: self._menu_codigo("cruzar"))
        mg.add_command(label="Batalhar contra IA", command=self.batalhar)
        mg.add_command(label="Batalhar contra código de amigo...", command=lambda: self._menu_codigo("batalhar"))
        mg.add_command(label="Estábulo (console: stable)", command=lambda: self._menu_info(self.estabulo()))
        mg.add_separator()
        mg.add_command(label="Cemitério de Honra", command=self.ver_cemiterio)
        self.var_hardcore = tk.BooleanVar(value=bool(self.cfg.get("hardcore")))
        mg.add_checkbutton(label="Modo hardcore (pode morrer!)", variable=self.var_hardcore,
                           command=lambda: self.alternar_hardcore(self.var_hardcore))
        m.add_cascade(label="Genética e batalhas", menu=mg)

    def _menu_petcode(self):
        cod = self.petcode()
        messagebox.showinfo("Código do pet", "Copiado pra área de transferência:\n\n" + cod +
                            "\n\nManda pro amigo: ele cola em 'Cruzar' ou 'Batalhar'.", parent=self.root)

    def _menu_codigo(self, acao):
        cod = simpledialog.askstring("Código do pet", "Cole o código (TAMA1-...):", parent=self.root)
        if cod:
            linhas = getattr(self, acao)(cod)
            if not isinstance(self.cena, (cenas.Cruzamento, cenas.Batalha)):
                messagebox.showinfo("Hmm", "\n".join(linhas), parent=self.root)

    def _menu_info(self, linhas):
        messagebox.showinfo("Tamagoshi", "\n".join(linhas), parent=self.root)
