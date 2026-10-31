"""Gera os efeitos sonoros do jogo por síntese (numpy) e grava WAV em public/assets/audio/.

Uso: /opt/bpyenv/bin/python tools/audio/gerar_sons.py   (qualquer Python com numpy)

Nada é gravado de fonte externa. Loops terminam com cruzamento suave para não estalar.
Vozes de NPC ficam para a etapa da ElevenLabs (decisão pendente sobre uso comercial).
"""
from __future__ import annotations

import os
import wave

import numpy as np

TAXA = 22050
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAIDA = os.path.join(RAIZ, "public", "assets", "audio")
rng = np.random.default_rng(11)


def t(seg):
    return np.arange(int(seg * TAXA)) / TAXA


def ruido(seg):
    return rng.uniform(-1, 1, int(seg * TAXA))


def passa_baixa(x, corte):
    a = np.exp(-2 * np.pi * corte / TAXA)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def passa_banda(x, centro, q=4.0):
    w0 = 2 * np.pi * centro / TAXA
    alfa = np.sin(w0) / (2 * q)
    b0, b1, b2 = alfa, 0.0, -alfa
    a0, a1, a2 = 1 + alfa, -2 * np.cos(w0), 1 - alfa
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        out = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, out
        y[i] = out
    return y


def envelope(n, ataque, queda):
    e = np.ones(n)
    na, nq = int(ataque * TAXA), int(queda * TAXA)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nq:
        e[-nq:] *= np.exp(-np.linspace(0, 6, nq))
    return e


def laco(x, cruz=0.4):
    n = int(cruz * TAXA)
    inicio = x[:n].copy()
    x = x[n:].copy()
    rampa = np.linspace(0, 1, n)
    x[-n:] = x[-n:] * (1 - rampa) + inicio * rampa
    return x


def normalizar(x, pico=0.85):
    m = np.max(np.abs(x)) or 1
    return x / m * pico


def salvar(nome, x, pico=0.85):
    os.makedirs(SAIDA, exist_ok=True)
    x = normalizar(x, pico)
    dados = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(SAIDA, nome + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(dados.tobytes())
    print(f"{nome}.wav {len(x) / TAXA:.1f}s")


def principal():
    # sirene: duas notas que sobem e descem, com harmônicos e eco da galeria
    tt = t(6)
    f = 520 + 260 * (0.5 - 0.5 * np.cos(2 * np.pi * tt / 3))
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    s = np.sin(fase) + 0.4 * np.sin(2 * fase) + 0.2 * np.sign(np.sin(fase)) * 0.3
    eco = np.zeros_like(s)
    d = int(0.23 * TAXA)
    eco[d:] = s[:-d] * 0.35
    salvar("sirene", (s + eco) * envelope(len(s), 0.2, 0.6))

    for nome, corte, dur, tom in (("passo_concreto", 1400, 0.12, 0), ("passo_areia", 700, 0.16, 0), ("passo_metal", 2500, 0.18, 380)):
        x = passa_baixa(ruido(dur), corte) * envelope(int(dur * TAXA), 0.003, dur * 0.9)
        if tom:
            x += 0.4 * np.sin(2 * np.pi * tom * t(dur)) * envelope(int(dur * TAXA), 0.001, dur)
        salvar(nome, x, 0.6)

    x = passa_banda(ruido(0.3), 900, 1.5) * envelope(int(0.3 * TAXA), 0.02, 0.25)
    salvar("pulo", x, 0.4)
    x = passa_baixa(ruido(0.25), 300) * envelope(int(0.25 * TAXA), 0.002, 0.24) + 0.6 * np.sin(2 * np.pi * 70 * t(0.25)) * envelope(int(0.25 * TAXA), 0.001, 0.2)
    salvar("aterrissar", x, 0.7)

    tt = t(0.6)
    x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, k in ((1320, 9), (1980, 12), (2640, 15)))
    salvar("coleta", x * envelope(len(tt), 0.002, 0.5), 0.5)

    tt = t(0.22)
    salvar("alerta", np.sin(2 * np.pi * 1250 * tt) * envelope(len(tt), 0.005, 0.05), 0.45)
    tt = t(0.5)
    salvar("alerta_grave", np.sign(np.sin(2 * np.pi * 440 * tt)) * 0.5 * envelope(len(tt), 0.005, 0.1), 0.4)

    tt = t(0.4)
    x = passa_baixa(ruido(0.4), 500) * np.exp(-tt * 10) + np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 8)
    salvar("dano", x, 0.7)

    base = passa_banda(ruido(9), 400, 0.7)
    lento = passa_baixa(ruido(9), 0.6)
    salvar("vento", laco(base * (0.6 + 2.5 * np.abs(lento))), 0.5)
    base = passa_banda(ruido(9), 650, 0.6) + 0.5 * passa_baixa(ruido(9), 200)
    lento = passa_baixa(ruido(9), 1.5)
    salvar("tempestade", laco(base * (0.5 + 4 * np.abs(lento))), 0.75)

    x = np.zeros(int(7 * TAXA))
    for _ in range(9):
        i = rng.integers(0, len(x) - 4000)
        tt = t(0.12)
        f0 = rng.uniform(900, 1700)
        x[i:i + len(tt)] += np.sin(2 * np.pi * (f0 - 3000 * tt) * tt) * np.exp(-tt * 40)
    salvar("goteira", laco(x + passa_baixa(ruido(7), 150) * 0.05), 0.5)

    tt = t(6)
    zumbido = sum(np.sin(2 * np.pi * f * tt) / k for k, f in enumerate((60, 120, 180, 240), 1))
    pas = 0.5 + 0.5 * np.sin(2 * np.pi * 7.5 * tt)
    salvar("ventilador", laco(zumbido * 0.4 + passa_banda(ruido(6), 300, 1.0) * pas), 0.45)
    salvar("zumbido_fluor", laco(sum(np.sin(2 * np.pi * f * tt) / k ** 1.5 for k, f in enumerate((120, 240, 360, 480, 600), 1))), 0.3)

    # multidão: ruído formântico com sílabas aleatórias de várias "vozes"
    dur = 10
    x = np.zeros(int(dur * TAXA))
    for v in range(10):
        silabas = passa_baixa((rng.random(int(dur * TAXA)) < 0.0009).astype(float), 8) * 400
        silabas = np.clip(silabas, 0, 1)
        formante = passa_banda(ruido(dur), rng.uniform(350, 900), 3) + 0.6 * passa_banda(ruido(dur), rng.uniform(1100, 2200), 4)
        x += formante * silabas
    salvar("multidao", laco(x), 0.4)

    # sermão: voz grave com entonação + coro de fundo em quinta
    dur = 12
    tt = t(dur)
    f0 = 105 + 18 * np.sin(2 * np.pi * 0.21 * tt) + 9 * np.sin(2 * np.pi * 0.83 * tt)
    fase = 2 * np.pi * np.cumsum(f0) / TAXA
    glotal = sum(np.sin(k * fase) / k for k in range(1, 14))
    frases = np.clip(passa_baixa((np.sin(2 * np.pi * 0.35 * tt) > -0.3).astype(float), 3), 0, 1)
    silab = 0.5 + 0.5 * np.sin(2 * np.pi * 3.7 * tt + 2 * np.sin(2 * np.pi * 0.7 * tt))
    voz = (passa_banda(glotal, 600, 3) + passa_banda(glotal, 1100, 4) * 0.6) * frases * silab
    coro = sum(np.sin(2 * np.pi * f * tt) for f in (147, 220, 294)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * tt))
    salvar("sermao", laco(voz + 0.15 * coro), 0.5)

    dur = 4
    tt = t(dur)
    fase = (tt % 4) / 4
    resp = np.where(fase < 0.4, np.sin(np.pi * fase / 0.4), 0) + 0.7 * np.where(fase > 0.5, np.sin(np.pi * (fase - 0.5) / 0.45), 0)
    resp = np.clip(resp, 0, 1)
    salvar("respiracao", passa_banda(ruido(dur), 1400, 1.2) * resp, 0.4)

    x = np.concatenate([passa_banda(ruido(2.2), 3000, 0.8) * envelope(int(2.2 * TAXA), 0.1, 0.8),
                        (passa_baixa(ruido(0.5), 400) + np.sin(2 * np.pi * 90 * t(0.5))) * np.exp(-t(0.5) * 9)])
    salvar("eclusa", x, 0.7)
    salvar("chuveiro", laco(passa_banda(ruido(5), 2500, 0.5) + 0.4 * passa_baixa(ruido(5), 400)), 0.45)
    tt = t(3)
    salvar("morte", np.sin(2 * np.pi * (90 - 25 * tt) * tt) * envelope(len(tt), 0.05, 2.5) + passa_baixa(ruido(3), 200) * 0.3 * envelope(len(tt), 0.05, 2.5), 0.6)
    x = np.zeros(int(0.7 * TAXA))
    for i in range(4):
        tt = t(0.25)
        j = int(i * 0.11 * TAXA)
        x[j:j + len(tt)] += sum(np.sin(2 * np.pi * f * tt) for f in (2800 + i * 200, 4100 + i * 150)) * np.exp(-tt * 25)
    salvar("moedas", x, 0.4)
    tt = t(0.06)
    salvar("clique", np.sin(2 * np.pi * 900 * tt) * np.exp(-tt * 60), 0.3)
    tt = t(0.8)
    salvar("porta", (passa_baixa(ruido(0.8), 600) + 0.6 * np.sin(2 * np.pi * 110 * tt) + 0.3 * np.sin(2 * np.pi * 173 * tt)) * np.exp(-tt * 5), 0.7)
    tt = t(8)
    tons = np.sin(2 * np.pi * 880 * tt) * ((tt % 2.0) < 0.15)
    salvar("radio", laco(passa_banda(ruido(8), 2000, 0.7) * (0.4 + 0.3 * np.sin(2 * np.pi * 0.3 * tt)) + 0.2 * tons), 0.35)
    tt = t(8)
    salvar("ambiente_vila", laco(passa_baixa(ruido(8), 120) * 2 + 0.2 * np.sin(2 * np.pi * 50 * tt)), 0.35)
    salvar("ambiente_superficie", laco(passa_banda(ruido(8), 250, 0.5) * (0.7 + 0.3 * np.abs(passa_baixa(ruido(8), 0.4)) * 3)), 0.35)


if __name__ == "__main__":
    principal()
