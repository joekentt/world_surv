"""Converte os WAV de public/assets/audio para OGG Vorbis (fase 7: download menor).

Uso: /opt/bpyenv/bin/python tools/audio/converter_ogg.py
Requer o pacote soundfile (libsndfile com Vorbis). Os WAV são apagados depois da conversão.
"""
import glob
import os

import soundfile as sf

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
antes = depois = 0
for wav in sorted(glob.glob(os.path.join(RAIZ, "public", "assets", "audio", "*.wav"))):
    dados, taxa = sf.read(wav)
    ogg = wav[:-4] + ".ogg"
    sf.write(ogg, dados, taxa, format="OGG", subtype="VORBIS")
    antes += os.path.getsize(wav)
    depois += os.path.getsize(ogg)
    os.remove(wav)
print(f"áudio: {antes / 1e6:.2f} MB em WAV -> {depois / 1e6:.2f} MB em OGG")
