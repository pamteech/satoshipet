# sons.py - chiptune raiz: gera WAVs de 8 bits em código e toca sem travar a janela
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

TAXA = 22050
PASTA = Path(tempfile.gettempdir()) / "tamagoshi_sons"

# cada som = lista de (frequência Hz, duração s); 0 Hz = silêncio
MELODIAS = {
    "moon": [(523, .07), (659, .07), (784, .07), (1047, .14)],      # subindo! arpejo feliz
    "rekt": [(392, .12), (330, .12), (262, .12), (196, .25)],      # descendo... wah wah
    "garimpando": [(440, .06), (0, .03), (440, .06)],               # tic-tic da picareta
    "alerta": [(880, .08), (0, .04), (880, .08), (0, .04), (1175, .15)],
    "clique": [(660, .04), (990, .06)],
    "conquista": [(784, .08), (988, .08), (1175, .08), (1568, .2)],
}


def gerar_wav(notas, caminho, volume=0.35):
    """Onda quadrada 8-bit mono. Pequeno, nostálgico e sem dependência nenhuma."""
    amostras = bytearray()
    for freq, dur in notas:
        n = int(TAXA * dur)
        for i in range(n):
            if freq <= 0:
                v = 0.0
            else:
                v = volume if math.sin(2 * math.pi * freq * i / TAXA) >= 0 else -volume
                v *= min(1.0, (n - i) / (TAXA * 0.01))  # fade curtinho pra não estalar
            amostras.append(int(128 + v * 127))
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(TAXA)
        w.writeframes(bytes(amostras))
    return caminho


def preparar():
    PASTA.mkdir(parents=True, exist_ok=True)
    return {nome: gerar_wav(notas, PASTA / f"{nome}.wav") for nome, notas in MELODIAS.items()}


class Som:
    def __init__(self, mudo=False):
        self.mudo = mudo
        try:
            self.arquivos = preparar()
        except OSError:
            self.arquivos = {}
        self.player = None
        if sys.platform != "win32":
            self.player = shutil.which("afplay") or shutil.which("aplay") or shutil.which("paplay")

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
                args = [self.player, "-q", arq] if self.player.endswith("aplay") else [self.player, arq]
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except Exception:
            pass
        return False
