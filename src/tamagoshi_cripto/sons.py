# sons.py - chiptune raiz v2: 2 canais de pulso + ruído, envelopes e arpejos. Tudo gerado em código,
# zero arquivos de áudio no repo. Toca sem travar a janela.
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from pathlib import Path

TAXA = 22050
PASTA = Path(tempfile.gettempdir()) / "tamagoshi_sons_v2"
NOTAS = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(nota):
    """'A4' -> 440.0 ; '-' = pausa. Porque ninguém decora frequência."""
    if not nota or nota == "-":
        return 0.0
    nome, oit = nota[:-1], int(nota[-1])
    return 440.0 * 2 ** ((NOTAS[nome] + 12 * (oit + 1) - 69) / 12)


def _seq(texto, dur):
    """'C5 E5 G5 -' -> [(hz, dur)...]. Sufixo ':n' multiplica a duração (ex.: C6:4)."""
    out = []
    for t in texto.split():
        n, _, k = t.partition(":")
        out.append((hz(n), dur * (float(k) if k else 1)))
    return out


# cada som: canais (pulso1, pulso2, ruído) + duty de cada pulso. pulso2 costuma ser baixo/harmonia.
MUSICAS = {
    "moon": {"p1": _seq("C5 E5 G5 C6 E6 G6:3", .055), "p2": _seq("C4:2 G4:2 C5:2", .09), "duty": (.125, .5)},
    "rekt": {"p1": _seq("G4 F#4 F4 E4:6", .11), "p2": _seq("C3:3 B2:3 A#2:4", .11),
             "ruido": [(0, .33), (1, .25)], "duty": (.5, .25)},
    "garimpando": {"p1": _seq("A5 - A5", .04), "ruido": [(1, .02), (0, .04), (1, .02)], "duty": (.25, .5)},
    "alerta": {"p1": _seq("A5 - A5 - D6:3", .06), "p2": _seq("A4 - A4 - D5:3", .06), "duty": (.25, .125)},
    "clique": {"p1": _seq("E5 B5", .035), "duty": (.125, .5)},
    "comer": {"p1": _seq("A3 - G3 - B3:2", .035), "ruido": [(1, .03), (0, .04), (1, .03), (0, .04), (1, .05)],
              "duty": (.5, .5)},
    "evoluir": {"p1": _seq("C5 E5 G5 C6 E5 G5 C6 E6 G5 C6 E6 G6:6", .05), "p2": _seq("C3:4 G3:4 C4:4 C4:6", .05),
                "duty": (.25, .5)},
    "panico": {"p1": _seq("A5 E5 A5 E5 A5 E5 A5 E5", .045), "ruido": [(1, .36)], "duty": (.5, .5)},
    "conquista": {"p1": _seq("G5 B5 D6 G6:2 - D6 G6:4", .06), "p2": _seq("G4:4 D5:4 G5:4", .06), "duty": (.25, .5)},
    "bloco": {"p1": _seq("C6 G5 C6:2", .04), "p2": _seq("C4:4", .04), "duty": (.125, .5)},
    "eclodir": {"p1": _seq("E5 - E5 - G5 C6 E6 G6 C7:6", .05), "ruido": [(1, .06), (0, .06), (1, .06)],
                "duty": (.25, .5)},
    "pegou": {"p1": _seq("B5 E6", .03), "duty": (.125, .5)},
    "errou": {"p1": _seq("E4 C4", .05), "duty": (.5, .5)},
    "fim_jogo": {"p1": _seq("C5 D5 E5 G5 E5 G5 C6:4", .07), "p2": _seq("C4:2 G3:2 C4:4", .07), "duty": (.25, .5)},
    "update": {"p1": _seq("G5 C6", .06), "duty": (.25, .5)},
}
# bgm: loop de 8 compassos, bem baixinho. Desligado por padrão (ninguém merece música no trabalho).
BGM = {"p1": _seq("E5 - G5 - A5 G5 E5 - D5 - E5 - C5:4 "
                  "E5 - G5 - A5 C6 A5 - G5 - E5 - G5:4", .16),
       "p2": _seq("A2:4 A3:4 F2:4 F3:4 C3:4 C4:4 G2:4 G3:4", .16), "duty": (.25, .5)}
MELODIAS = MUSICAS  # compat com testes/plugins antigos


def _canal_pulso(notas, duty, vol):
    out = []
    for freq, dur in notas:
        n = int(TAXA * dur)
        for i in range(n):
            if freq <= 0:
                out.append(0.0)
                continue
            fase = (freq * i / TAXA) % 1.0
            env = min(1.0, i / (TAXA * .004)) * max(0.0, 1 - i / n * .6) * min(1.0, (n - i) / (TAXA * .006))
            out.append((1.0 if fase < duty else -1.0) * vol * env)
    return out


def _canal_ruido(trechos, vol, semente=7):
    rnd = random.Random(semente)
    out, v = [], 0.0
    for liga, dur in trechos:
        n = int(TAXA * dur)
        for i in range(n):
            if i % 6 == 0:  # ruído "LFSR" com sample-and-hold, bem NES
                v = rnd.choice((-1.0, 1.0))
            out.append(v * vol * (1 - i / n) if liga else 0.0)
    return out


def renderizar(musica, volume=0.35):
    d1, d2 = musica.get("duty", (.5, .5))
    canais = [_canal_pulso(musica.get("p1", []), d1, volume),
              _canal_pulso(musica.get("p2", []), d2, volume * .55),
              _canal_ruido(musica.get("ruido", []), volume * .35)]
    n = max(len(c) for c in canais)
    return [max(-1.0, min(1.0, sum(c[i] if i < len(c) else 0.0 for c in canais))) for i in range(n)]


def gerar_wav(musica, caminho, volume=0.35):
    """WAV 8-bit mono. Aceita o formato novo (dict de canais) ou lista [(hz, dur)] antiga."""
    if isinstance(musica, list):
        musica = {"p1": musica}
    amostras = bytes(int(128 + v * 120) for v in renderizar(musica, volume))
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(TAXA)
        w.writeframes(amostras)
    return caminho


def preparar(volume=0.35):
    PASTA.mkdir(parents=True, exist_ok=True)
    arqs = {}
    for nome, m in MUSICAS.items():
        p = PASTA / f"{nome}_{int(volume * 100)}.wav"
        arqs[nome] = p if p.exists() else gerar_wav(m, p, volume)
    return arqs


class Som:
    def __init__(self, mudo=False, volume=0.35):
        self.mudo = mudo
        self.volume = volume
        try:
            self.arquivos = preparar(volume)
        except OSError:
            self.arquivos = {}
        self.player = None
        if sys.platform != "win32":
            self.player = shutil.which("afplay") or shutil.which("paplay") or shutil.which("aplay")
        self._bgm = None

    def _args(self, arq):
        return [self.player, "-q", arq] if self.player.endswith("aplay") and not self.player.endswith("paplay") \
            else [self.player, arq]

    def tocar(self, nome):
        """Não bloqueia. Se não houver como tocar, fica em silêncio (o bicho entende)."""
        if self.mudo or nome not in self.arquivos:
            return False
        arq = str(self.arquivos[nome])
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(arq, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                return True
            if self.player:
                subprocess.Popen(self._args(arq), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except Exception:
            pass
        return False

    # ---------- música de fundo (opcional) ----------
    def musica(self, ligar):
        if not ligar or self.mudo:
            if self._bgm:
                self._bgm.set()
                self._bgm = None
            return False
        if self._bgm or not (self.player or sys.platform == "win32"):
            return bool(self._bgm)
        PASTA.mkdir(parents=True, exist_ok=True)
        arq = PASTA / "bgm.wav"
        if not arq.exists():
            gerar_wav(BGM, arq, self.volume * .35)
        parar = threading.Event()
        self._bgm = parar

        def loop():
            while not parar.is_set():
                try:
                    subprocess.run(self._args(str(arq)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                except Exception:
                    return
        if sys.platform == "win32":  # winsound: 1 som por vez, então bgm só quando nada mais toca (limitação)
            return False
        threading.Thread(target=loop, daemon=True).start()
        return True
