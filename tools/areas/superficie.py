"""Superfície aberta em blocos (revisão 2, fase 2, tarefa 5).

Uso: python3 tools/areas/superficie.py   (grava content/areas/superficie_*.json)

Seção 5.2 de docs/spec/05-mapa.md e seção 7 de docs/spec/07-arte-personagens-vila.md.
Mundo "superficie_aberta" (o nome "superficie" ainda é das faixas lineares da revisão 1), Y para cima,
a Boca do Poço na origem e o norte em +Z. Limite jogável: x de -318 a 318, z de -102 a 573.

Estrutura:
  - `superficie_aberta` ("Superfície"): caixa de todo o mapa, sempre carregada enquanto o jogador está na
    superfície. Tem o terreno (grade de alturas de 4 m com colisão de malha), as muralhas do leito do rio,
    a parede de tempestade com a colisão do limite, e os marcos que precisam ser vistos de longe: a Antena,
    a Torre d'Água e o viaduto caído. Também os carros soterrados e destroços espalhados.
  - Áreas menores, carregadas pela distância (margem de 45 m): Boca do Poço, Ruínas Próximas, as duas
    Escotilhas, o Leito Seco do Rio (as duas travessias), O Marco, a Torre d'Água, o Viaduto Caído e a
    Colina da Antena. Têm os detalhes, os interiores que servem de abrigo e as escadas de mão.
Relevo: ondulação suave (±2 m), subida leve para o norte, morros além do limite, a colina da Antena 25 m
acima com uma crista até a ponta do viaduto (encostas de até ~35 graus, abaixo dos 45 de src/config.ts),
platôs nivelados sob as construções e o leito do rio 4,5 m abaixo, entre muralhas de concreto.
Regra de bloqueio (seção 5.3): as rotas de referência ficam em `rotasReferencia` da área base e são
medidas por tests/fase2_superficie.spec.ts.
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_areas import Area  # noqa: E402
from subsolo_vila import B, V, corrimao, r3  # noqa: E402

R = random.Random(505)
MUNDO = "superficie_aberta"

# ---------------------------------------------------------------- limites e grade do terreno
LX0, LX1, LZ0, LZ1 = -318.0, 318.0, -102.0, 573.0
PASSO = 4.0
GX0, GZ0 = -384.0, -168.0
NX, NZ = 193, 203                       # x de -384 a 384, z de -168 a 640
Y_CAIXA = (-15.0, 140.0)

# ---------------------------------------------------------------- pontos da seção 5.2
BOCA = (0.0, 0.0)
ESC_OESTE = (-178.0, 115.0)
ESC_LESTE = (191.0, 76.0)
RIO_Z0, RIO_Z1 = 191.5, 215.5           # faces internas das muralhas (faixa de 191 a 216)
MURO_S = (188.0, RIO_Z0)
MURO_N = (RIO_Z1, 220.0)
Y_LEITO = -4.5
Y_MURO = 0.4
MARCO = (-51.0, 255.0)
PRACA = (-71.0, -31.0, 239.0, 271.0)
TORRE = (-229.0, 382.0)
VIA_A = (153.0, 331.0)                  # ponta caída (no chão)
VIA_B = (51.0, 382.0)                   # ponta alta, encostada na crista da colina
ANTENA = (38.0, 484.0)
ALT_COLINA = 25.0

# travessias do rio: ponte inteira (oeste) e ponte desabada (leste), a única saída do leito
PONTE = (-49.0, -39.0, 186.0, 222.0)    # x0, x1, z0, z1 do tabuleiro
Y_PONTE = 0.15                          # degrau baixo na entrada da ponte (o máximo é 0,35)
DESAB = (100.0, 112.0)                  # vão nas muralhas da ponte desabada
DESAB_X = (102.0, 110.0)                # largura das rampas de entulho
# (z, topo) das rampas, ~15 graus; as pontas no chão caem sobre linhas da grade do terreno (z = 184 e 224)
RAMPA_S = ((184.0, 0.02), (200.0, Y_LEITO + 0.1))
RAMPA_N = ((208.0, Y_LEITO + 0.1), (224.0, 0.02))

# construções com interior (abrigos): x0, x1, z0, z1, andares, face da porta, material
PREDIOS = [
    dict(id="abrigo_ruinas_a", x0=-38.0, x1=-22.0, z0=62.0, z1=74.0, andares=2, porta="-z", mat="reboco"),
    dict(id="abrigo_ruinas_b", x0=28.0, x1=40.0, z0=86.0, z1=104.0, andares=2, porta="-x", mat="tijolo"),
    dict(id="abrigo_ruinas_c", x0=-84.0, x1=-70.0, z0=102.0, z1=116.0, andares=5, porta="+x", mat="concreto"),
    dict(id="abrigo_ruinas_d", x0=58.0, x1=66.0, z0=112.0, z1=120.0, andares=1, porta="-z", mat="tijolo"),
]
PREDIO_MARCO = dict(id="abrigo_marco", x0=-88.0, x1=-76.0, z0=250.0, z1=262.0, andares=2, porta="+x", mat="reboco")
CABANA = dict(id="abrigo_antena", x0=22.0, x1=28.0, z0=486.0, z1=491.0, andares=1, porta="+x", mat="metal")
POSTO = (48.0, 68.0, 50.0, 64.0)
# entulho de prédio desabado que atravessa as ruínas, com duas brechas
ENTULHO_Z = (123.0, 128.0)
ENTULHO_X = [(-62.0, -14.0), (-6.0, 18.0), (26.0, 56.0)]

# rotas de referência (x, z) para o teste da seção 5.3; ficam livres de destroços sorteados
ROTA_MARCO = [(0.0, 8.0), (-2.0, 40.0), (-10.0, 125.5), (-44.0, 180.0), (-44.0, 228.0), (-50.0, 242.0), (-51.0, 249.0)]
ROTA_ANTENA = ROTA_MARCO[:5] + [(-25.0, 300.0), (20.0, 420.0), (37.0, 474.0)]
ROTA_VIADUTO = [(160.0, 323.0), (153.5, 331.5), (51.0, 382.0), (44.0, 430.0), (39.0, 474.0)]
ROTA_DESABADA = [(106.0, 172.0), (106.0, 182.0), (106.0, 203.0), (106.0, 224.0), (106.0, 234.0)]
CORREDORES = [ROTA_MARCO, ROTA_ANTENA, [(-44.0, 228.0), (-25.0, 300.0)], ROTA_VIADUTO[:2], ROTA_DESABADA]


# ====================================================================== relevo

def ss(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def base(x, z):
    """Ondulação suave, subida leve para o norte e morros além do limite jogável."""
    h = 1.1 * math.sin(x / 47 + 0.6) * math.cos(z / 59 - 0.3) + 0.7 * math.sin((x - z) / 83 + 1.9)
    h += 0.35 * math.sin(x / 19 + z / 23)
    h += 0.011 * max(0.0, z - 260)
    dentro = min(x - LX0, LX1 - x, z - LZ0, LZ1 - z)
    h += 16 * ss((40 - dentro) / 100)
    return h


def dist_segmento(px, pz, a, b):
    ax, az = a
    bx, bz = b
    vx, vz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / (vx * vx + vz * vz)))
    return math.hypot(px - ax - vx * t, pz - az - vz * t), t


Y_VIA = round(base(*VIA_B) + 10.0, 2)    # tabuleiro do viaduto


def colina(x, z):
    """Colina da Antena (25 m) e a crista que desce até a ponta alta do viaduto."""
    r = math.hypot(x - ANTENA[0], z - ANTENA[1])
    h = ALT_COLINA * ss((72 - r) / 60)
    d, t = dist_segmento(x, z, VIA_B, ANTENA)
    alto0 = Y_VIA - base(*VIA_B) - 0.15
    crista = (alto0 + (ALT_COLINA - alto0) * t) * ss((28 - d) / 22)
    return max(h, crista)


def relevo(x, z):
    return base(x, z) + colina(x, z)


def ret(x0, x1, z0, z1, y=None, mistura=6.0):
    if y is None:
        y = relevo((x0 + x1) / 2, (z0 + z1) / 2)
    return (x0, x1, z0, z1, y, mistura)


def platôs():
    p = [ret(-22, 22, -22, 22, 0.0, 15.0),                  # pátio da Boca
         ret(-400, 400, 182, 226, 0.0, 12.0)]                # margens do rio
    for q in PREDIOS + [PREDIO_MARCO]:
        p.append(ret(q["x0"] - 3, q["x1"] + 3, q["z0"] - 3, q["z1"] + 3))
    p.append(ret(*POSTO))
    p.append(ret(PRACA[0] - 2, PRACA[1] + 2, PRACA[2] - 2, PRACA[3] + 2, mistura=10.0))
    p.append(ret(TORRE[0] - 9, TORRE[0] + 9, TORRE[1] - 9, TORRE[1] + 9, mistura=8.0))
    for e in (ESC_OESTE, ESC_LESTE):
        p.append(ret(e[0] - 4, e[0] + 4, e[1] - 4, e[1] + 4, mistura=5.0))
    p.append(ret(ANTENA[0] - 16, ANTENA[0] + 16, ANTENA[1] - 16, ANTENA[1] + 16,
                 base(*ANTENA) + ALT_COLINA, 8.0))            # topo da colina
    return p


PLATOS = platôs()


def altura_continua(x, z):
    h = relevo(x, z)
    for x0, x1, z0, z1, y, m in PLATOS:
        dx = max(x0 - x, 0.0, x - x1)
        dz = max(z0 - z, 0.0, z - z1)
        w = ss(1 - math.hypot(dx, dz) / m)
        h += (y - h) * w
    if 190.0 <= z <= 217.0:
        h = Y_LEITO + 0.15 * math.sin(x / 7.0)
    if DESAB[0] - 0.1 <= x <= DESAB[1] + 0.1:   # sob as rampas da ponte desabada o terreno fica abaixo delas
        for (z0, y0), (z1, y1) in (RAMPA_S, RAMPA_N):
            alto = z0 if y0 > y1 else z1           # ponta no chão: a linha da grade ali fica como está
            if z0 <= z <= z1 and abs(z - alto) > 0.5:
                h = min(h, y0 + (y1 - y0) * (z - z0) / (z1 - z0) - 0.05)
    return h


ALTURAS = [[round(altura_continua(GX0 + i * PASSO, GZ0 + j * PASSO), 2) for i in range(NX)] for j in range(NZ)]


def alt(x, z):
    """Altura do terreno como a malha do jogo (dois triângulos por célula, diagonal de (i+1, j) a (i, j+1))."""
    fx, fz = (x - GX0) / PASSO, (z - GZ0) / PASSO
    i, j = max(0, min(NX - 2, int(math.floor(fx)))), max(0, min(NZ - 2, int(math.floor(fz))))
    u, v = fx - i, fz - j
    a, b = ALTURAS[j][i], ALTURAS[j][i + 1]
    c, d = ALTURAS[j + 1][i], ALTURAS[j + 1][i + 1]
    if u + v <= 1:
        return a + (b - a) * u + (c - a) * v
    return d + (c - d) * (1 - u) + (b - d) * (1 - v)


def alt_max(x0, x1, z0, z1):
    return max(alt(x, z) for x in (x0, (x0 + x1) / 2, x1) for z in (z0, (z0 + z1) / 2, z1))


def alt_min(x0, x1, z0, z1):
    return min(alt(x, z) for x in (x0, (x0 + x1) / 2, x1) for z in (z0, (z0 + z1) / 2, z1))


# ====================================================================== geometria

def rot(v, rx, ry, rz):
    """Gira um vetor como o Babylon gira uma malha (rotação de Euler: rolagem, arfagem e guinada)."""
    x, y, z = v
    a = math.radians(rz)
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    a = math.radians(rx)
    y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
    a = math.radians(ry)
    x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
    return x, y, z


def C(a: Area, cx, cy, cz, w, h, d, mat, **k):
    """Caixa pelo centro, com rotações opcionais (rx, ry, rz em graus)."""
    q = dict(x=r3(cx), y=r3(cy), z=r3(cz), w=r3(w), h=r3(h), d=r3(d), mat=mat)
    for eixo in ("rx", "ry", "rz"):
        v = k.pop(eixo, 0)
        if abs(v) > 1e-3:
            q[eixo] = r3(v)
    q.update(k)
    a.d["solidos"].append(q)


def laje_entre(a, p0, p1, y0, y1, largura, esp, mat, **k):
    """Laje reta (ou inclinada) cuja face de cima vai de (p0, y0) a (p1, y1), em qualquer direção no plano."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dz)
    ux, uz = dx / L, dz / L
    dy = y1 - y0
    ang = math.atan2(-dy, L)
    comp = math.hypot(L, dy) + (0.4 if abs(dy) > 1e-6 else 0.0)
    c, s = math.cos(ang), math.sin(ang)
    cx = (p0[0] + p1[0]) / 2 - ux * s * esp / 2
    cz = (p0[1] + p1[1]) / 2 - uz * s * esp / 2
    cy = (y0 + y1) / 2 - c * esp / 2
    C(a, cx, cy, cz, largura, esp, comp, mat, rx=math.degrees(ang), ry=math.degrees(math.atan2(ux, uz)), **k)


def viga(a, p, q, esp, mat, **k):
    """Barra reta entre dois pontos 3D num plano vertical alinhado com X ou com Z (contraventamentos)."""
    (x0, y0, z0), (x1, y1, z1) = p, q
    L = math.dist(p, q)
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    if abs(z1 - z0) < 1e-6:      # plano XY: gira em Z
        C(a, cx, cy, cz, L, esp, esp, mat, rz=math.degrees(math.atan2(y1 - y0, x1 - x0)), **k)
    else:                        # plano ZY: gira em X
        C(a, cx, cy, cz, esp, esp, L, mat, rx=math.degrees(math.atan2(-(y1 - y0), z1 - z0)), **k)


def parede(a, eixo, fixo, ini, fim, y0, y1, esp, vaos, mat, **k):
    """Parede ao longo de x (eixo 'x', centrada em z = fixo) ou de z, com vãos (s0, s1, v0, v1)."""
    def seg(s0, s1, v0, v1):
        if s1 - s0 < 0.05 or v1 - v0 < 0.05:
            return
        if eixo == "x":
            B(a, s0, s1, v0, v1, fixo - esp / 2, fixo + esp / 2, mat, **k)
        else:
            B(a, fixo - esp / 2, fixo + esp / 2, v0, v1, s0, s1, mat, **k)
    atual = ini
    for s0, s1, v0, v1 in sorted(vaos):
        seg(atual, s0, y0, y1)
        seg(s0, s1, y0, v0)
        seg(s0, s1, v1, y1)
        atual = s1
    seg(atual, fim, y0, y1)


ANDAR = 3.5
ESP_PAREDE = 0.5


def predio(a: Area, q, quebrado=True, telhado=True):
    """Prédio em ruínas com interior acessível pelo térreo (abrigo). Andares de cima sem acesso."""
    x0, x1, z0, z1, n = q["x0"], q["x1"], q["z0"], q["z1"], q["andares"]
    g = alt_min(x0, x1, z0, z1)
    gt = alt_max(x0, x1, z0, z1)
    e = ESP_PAREDE
    topo = g + ANDAR * n
    faces = {"-z": ("x", z0 + e / 2, x0, x1), "+z": ("x", z1 - e / 2, x0, x1),
             "-x": ("z", x0 + e / 2, z0 + e, z1 - e), "+x": ("z", x1 - e / 2, z0 + e, z1 - e)}
    for nome, (eixo, fixo, ini, fim) in faces.items():
        meio = (ini + fim) / 2
        vaos = []
        if nome == q["porta"]:
            vaos.append((meio - 1.2, meio + 1.2, g - 2.0, g + 2.8))
        corpo_topo = topo - (ANDAR if (quebrado and n > 1) else 0.0)
        for f in range(n):
            yj = g + ANDAR * f + 1.1
            if yj + 1.3 > corpo_topo:
                continue
            s = ini + 2.2
            while s < fim - 2.0:
                if not (nome == q["porta"] and f == 0 and abs(s - meio) < 2.4):
                    vaos.append((s - 0.65, s + 0.65, yj, yj + 1.3))
                s += 3.6
        parede(a, eixo, fixo, ini, fim, g - 2.0, corpo_topo, e, vaos, q["mat"])
        if quebrado and n > 1:      # último andar em pedaços de alturas diferentes
            partes = R.randint(2, 4)
            for p in range(partes):
                s0 = ini + (fim - ini) * p / partes
                s1 = ini + (fim - ini) * (p + 1) / partes
                h = corpo_topo + ANDAR * R.uniform(0.15, 1.0)
                if R.random() < 0.25:
                    continue
                parede(a, eixo, fixo, s0, s1, corpo_topo, h, e, [], q["mat"])
        # marca da porta: batente escuro e soleira
        if nome == q["porta"]:
            if eixo == "x":
                V(a, meio - 1.35, meio + 1.35, g + 2.8, g + 3.05, fixo - e / 2 - 0.08, fixo + e / 2 + 0.08, "escuro")
            else:
                V(a, fixo - e / 2 - 0.08, fixo + e / 2 + 0.08, g + 2.8, g + 3.05, meio - 1.35, meio + 1.35, "escuro")
    # piso do térreo, lajes intermediárias e telhado (com rombo)
    B(a, x0 + e, x1 - e, gt - 0.6, gt + 0.12, z0 + e, z1 - e, "concreto")
    for f in range(1, n):
        if quebrado and f == n - 1:
            continue
        B(a, x0 + e, x1 - e, g + ANDAR * f - 0.3, g + ANDAR * f, z0 + e, z1 - e, "concreto")
    if telhado:
        yt = g + ANDAR * (n - 1 if (quebrado and n > 1) else n)
        w, d = x1 - x0, z1 - z0
        rombo = (x0 + w * R.uniform(0.15, 0.45), x0 + w * R.uniform(0.55, 0.85), z0 + d * R.uniform(0.15, 0.4), z0 + d * R.uniform(0.6, 0.85))
        from subsolo_vila import laje
        laje(a, x0, x1, z0, z1, yt - 0.3, yt, furos=[rombo], mat="concreto")
        # escombros do telhado caídos no chão, sob o rombo
        cx, cz = (rombo[0] + rombo[1]) / 2, (rombo[2] + rombo[3]) / 2
        C(a, cx, gt + 0.4, cz, 2.2, 0.6, 1.6, "concreto", ry=R.uniform(0, 90), rz=R.uniform(-12, 12))
    ab = dict(id=q["id"], min=[r3(x0 + e), r3(g), r3(z0 + e)], max=[r3(x1 - e), r3(g + ANDAR), r3(z1 - e)])
    a.d.setdefault("abrigos", []).append(ab)
    # câmera do interior: sala (vila) ou, com 6 m ou menos de lado, cômodo apertado (tunel)
    tipo = "tunel" if min(x1 - x0, z1 - z0) <= 6.5 else "vila"
    a.d.setdefault("zonasCamera", []).append({"tipo": tipo, "min": ab["min"], "max": [ab["max"][0], r3(g + ANDAR - 0.3), ab["max"][2]]})


def carro(a: Area, x, z, yaw, mat=None, afundar=None, inclinar=True):
    """Carro soterrado: carroceria e cabine inclinadas, afundadas na areia, com um monte de areia ao lado."""
    mat = mat or R.choice(["carro_vermelho", "carro_azul", "carro_bege", "ferrugem", "ferrugem", "metal"])
    afundar = R.uniform(0.25, 0.75) if afundar is None else afundar
    rx = R.uniform(-9, 9) if inclinar else 0.0
    rz = R.uniform(-12, 12) if inclinar else 0.0
    g = alt(x, z)
    cy = g + 0.65 - afundar
    C(a, x, cy, z, 1.8, 1.3, 4.3, mat, rx=rx, ry=yaw, rz=rz)
    ox, oy, oz = rot((0.0, 1.0, -0.3), rx, yaw, rz)
    C(a, x + ox, cy + oy, z + oz, 1.6, 0.75, 2.2, mat, rx=rx, ry=yaw, rz=rz)
    ox, oy, oz = rot((0.0, 1.02, -0.3), rx, yaw, rz)
    C(a, x + ox, cy + oy, z + oz, 1.66, 0.42, 2.27, "escuro", rx=rx, ry=yaw, rz=rz, semColisao=True)
    lado = R.choice([-1, 1])
    ox, oy, oz = rot((lado * 1.3, 0.0, 0.4), 0, yaw, 0)
    C(a, x + ox, g - 0.2, z + oz, 1.6, 1.0, 3.6, "areia", ry=yaw + R.uniform(-15, 15), rz=lado * 22)


def rocha(a: Area, x, z, tam):
    g = alt(x, z)
    C(a, x, g + tam * 0.25, z, tam, tam * 0.9, tam * 1.2, R.choice(["rocha", "rocha", "concreto"]),
      rx=R.uniform(-20, 20), ry=R.uniform(0, 180), rz=R.uniform(-20, 20))


def arvore_morta(a: Area, x, z, h=None):
    h = h or R.uniform(4.0, 7.5)
    g = alt(x, z)
    inc = R.uniform(-8, 8)
    C(a, x, g + h / 2 - 0.3, z, 0.38, h, 0.38, "madeira_escura", rz=inc)
    for _ in range(2):
        yb = g + h * R.uniform(0.5, 0.85)
        ang = R.uniform(0, 360)
        comp = R.uniform(1.5, 2.8)
        dx, dz = math.sin(math.radians(ang)) * comp / 2, math.cos(math.radians(ang)) * comp / 2
        C(a, x + dx, yb + 0.5, z + dz, 0.16, 0.16, comp, "madeira_escura", rx=-35, ry=ang, semColisao=True)


def perto_de_rota(x, z, folga):
    for rota in CORREDORES:
        for p, q in zip(rota, rota[1:]):
            if dist_segmento(x, z, p, q)[0] < folga:
                return True
    return False


def em_ret(x, z, r, folga=0.0):
    return r[0] - folga <= x <= r[1] + folga and r[2] - folga <= z <= r[3] + folga


def nova(id_, nome, x0, x1, z0, z1) -> Area:
    a = Area(id_, nome, MUNDO, "superficie", None, x0, x1, superficie=True)
    a.d["zonaPadrao"] = "superficie"
    a.caixa((x0, Y_CAIXA[0], z0), (x1, Y_CAIXA[1], z1))
    return a


def entrada(a: Area, nome, x, z, yaw=0.0):
    a.d["entradas"][nome] = dict(x=r3(x), y=r3(alt(x, z) + 0.1), z=r3(z), yaw=yaw)


# ====================================================================== área base (sempre carregada)

def muralhas_do_rio(a: Area):
    """Muralhas de concreto das duas margens; vão na ponte desabada e muralha rebaixada sob a ponte inteira."""
    for z0, z1 in (MURO_S, MURO_N):
        trechos = [(-336.0, PONTE[0], Y_MURO), (PONTE[0], PONTE[1], Y_PONTE - 0.8), (PONTE[1], DESAB[0], Y_MURO),
                   (DESAB[1], 336.0, Y_MURO)]
        for x0, x1, topo in trechos:
            B(a, x0, x1, Y_LEITO - 1.0, topo, z0, z1, "concreto")
        # faixa escura de umidade antiga no pé da face interna
        zi = z1 if z0 < 200 else z0
        for x0, x1, topo in trechos:
            if topo == Y_MURO:
                V(a, x0, x1, Y_LEITO - 0.2, Y_LEITO + 0.6, zi - 0.03, zi + 0.03, "concreto_escuro")


def tempestade(a: Area):
    """Colisão invisível no limite jogável. A cortina de poeira é desenhada pelo jogo em volta de `limiteJogavel`
    (src/world/tempestade.ts)."""
    for x0, x1, z0, z1 in ((LX0 - 2, LX0, LZ0 - 2, LZ1 + 2), (LX1, LX1 + 2, LZ0 - 2, LZ1 + 2),
                           (LX0, LX1, LZ0 - 2, LZ0), (LX0, LX1, LZ1, LZ1 + 2)):
        B(a, x0, x1, -30.0, 170.0, z0, z1, "parede", invisivel=True, semCamera=True)


def viaduto(a: Area):
    """Viaduto caído: o primeiro vão desabou e virou rampa até o tabuleiro, que segue até a crista da colina."""
    dx, dz = VIA_B[0] - VIA_A[0], VIA_B[1] - VIA_A[1]
    L = math.hypot(dx, dz)
    ux, uz = dx / L, dz / L
    nx_, nz_ = uz, -ux
    yaw = math.degrees(math.atan2(ux, uz))

    def P(t, lado=0.0):
        return (VIA_A[0] + dx * t + nx_ * lado, VIA_A[1] + dz * t + nz_ * lado)

    t_caido = 0.245
    g0 = alt(*VIA_A) + 0.15
    # vão desabado (rampa); a ponta de cima passa 2 cm do tabuleiro, que começa logo depois (sem degrau)
    laje_entre(a, P(0.0), P(t_caido), g0, Y_VIA + 0.02, 9.4, 1.0, "concreto")
    laje_entre(a, P(t_caido + 0.001), P(1.07), Y_VIA, Y_VIA, 10.0, 1.2, "concreto")
    # vigas laterais do tabuleiro (faixa escura que marca o perfil de longe)
    for lado in (-5.1, 5.1):
        laje_entre(a, P(t_caido, lado), P(1.0, lado), Y_VIA - 1.2, Y_VIA - 1.2, 0.3, 1.0, "concreto_escuro", semColisao=True)
    # pilares (pares) e travessas
    for t in (0.37, 0.55, 0.73, 0.9):
        for lado in (-3.0, 3.0):
            px, pz = P(t, lado)
            g = alt(px, pz)
            C(a, px, (g - 1.0 + Y_VIA - 1.2) / 2, pz, 1.6, Y_VIA - 1.2 - g + 1.0, 1.6, "concreto", ry=yaw)
        cx, cz = P(t)
        C(a, cx, Y_VIA - 1.7, cz, 9.0, 1.0, 1.8, "concreto", ry=yaw)
    # pilar quebrado sob o vão desabado e o toco do pilar inclinado
    px, pz = P(0.12, 2.5)
    C(a, px, alt(px, pz) + 1.6, pz, 1.6, 4.0, 1.6, "concreto", ry=yaw, rz=14)
    # guarda-corpos do tabuleiro (com colisão), com trechos caídos
    for lado in (-4.85, 4.85):
        t = t_caido + 0.01
        while t < 1.0:
            t1 = min(1.0, t + 0.08)
            if R.random() > 0.2:
                laje_entre(a, P(t, lado), P(t1, lado), Y_VIA + 0.9, Y_VIA + 0.9, 0.3, 0.9, "concreto")
            t = t1 + 0.004


# Antena: seções da treliça e plataforma do mirante (a escada de mão fica na área da colina)
ANT_SECOES, ANT_HS, ANT_HW0, ANT_PASSO = 6, 9.0, 7.0, 0.9
ANT_PLAT = 7.0          # meia largura da plataforma a 10 m
Y_PLAT = 10.0


def antena(a: Area):
    """A Antena: torre treliçada de 54 m no topo da colina, mastro de 18 m, plataforma a 10 m e luz vermelha."""
    cx, cz = ANTENA
    g = base(*ANTENA) + ALT_COLINA
    hs = ANT_HS
    hw1 = ANT_HW0
    for k in range(ANT_SECOES):
        hw = ANT_HW0 - ANT_PASSO * k
        hw1 = ANT_HW0 - ANT_PASSO * (k + 1)
        y0 = g + hs * k
        y1 = y0 + hs
        for sx in (-1, 1):
            for sz in (-1, 1):
                # perna em degraus: cada seção um pouco mais para dentro
                C(a, cx + sx * hw, (y0 + y1) / 2, cz + sz * hw, 1.2, hs + 0.1, 1.2, "ferro")
        for s in (-1, 1):   # anel no topo da seção
            C(a, cx, y1, cz + s * hw1, 2 * hw1 + 1.2, 0.5, 0.5, "ferro")
            C(a, cx + s * hw1, y1, cz, 0.5, 0.5, 2 * hw1 + 1.2, "ferro")
        # contraventamento em X nas quatro faces (sem o X na face sul até a plataforma, onde fica a escada)
        for s in (-1, 1):
            if not (s == -1 and k < 2):
                viga(a, (cx - hw, y0, cz + s * hw), (cx + hw1, y1, cz + s * hw), 0.4, "ferro")
                viga(a, (cx + hw, y0, cz + s * hw), (cx - hw1, y1, cz + s * hw), 0.4, "ferro")
            viga(a, (cx + s * hw, y0, cz - hw), (cx + s * hw, y1, cz + hw1), 0.4, "ferro")
            viga(a, (cx + s * hw, y0, cz + hw), (cx + s * hw, y1, cz - hw1), 0.4, "ferro")
    topo_trelica = g + hs * ANT_SECOES
    # sapatas de concreto
    for sx in (-1, 1):
        for sz in (-1, 1):
            px, pz = cx + sx * ANT_HW0, cz + sz * ANT_HW0
            B(a, px - 1.1, px + 1.1, g - 1.0, g + 0.5, pz - 1.1, pz + 1.1, "concreto")
    # plataforma do mirante e casa de equipamentos (18 a 23 m)
    B(a, cx - ANT_PLAT, cx + ANT_PLAT, g + Y_PLAT - 0.3, g + Y_PLAT, cz - ANT_PLAT, cz + ANT_PLAT, "grade")
    B(a, cx - 3.2, cx + 3.2, g + 18.0, g + 23.0, cz - 3.2, cz + 3.2, "ferro")
    # mastro e antenas de prato
    C(a, cx, topo_trelica + 9.0, cz, 1.2, 18.0, 1.2, "ferro")
    C(a, cx, topo_trelica + 19.0, cz, 0.4, 2.0, 0.4, "ferro")
    for yy, ang in ((g + 28.0, 30.0), (g + 33.0, 160.0), (g + 38.0, 250.0)):
        ox, _, oz = rot((0.0, 0.0, 4.4), 0, ang, 0)
        C(a, cx + ox, yy, cz + oz, 4.0, 4.0, 0.6, "chapa_clara", ry=ang, rx=-12)
    for i, yy in enumerate((topo_trelica + 4.0, topo_trelica + 10.0)):
        C(a, cx, yy, cz, 0.3, 3.0, 3.6, "chapa_clara", ry=45 + 90 * i, semColisao=True)
    # luzes de alerta (só emissivo, sem luz pontual)
    C(a, cx, topo_trelica + 20.4, cz, 1.0, 1.0, 1.0, "luz_vermelha", semColisao=True)
    for sx in (-1, 1):
        C(a, cx + sx * (hw1 + 0.3), topo_trelica + 0.7, cz, 0.7, 0.7, 0.7, "luz_vermelha", semColisao=True)


def torre_dagua(a: Area):
    """Torre d'Água: quatro pernas de 24 m, contraventamento, passarela e caixa octogonal."""
    cx, cz = TORRE
    g = alt(cx, cz)
    hw = 4.0
    ht = 24.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            C(a, cx + sx * hw, g + ht / 2 - 0.5, cz + sz * hw, 1.0, ht + 1.0, 1.0, "ferro")
            B(a, cx + sx * hw - 0.9, cx + sx * hw + 0.9, g - 1.0, g + 0.6, cz + sz * hw - 0.9, cz + sz * hw + 0.9, "concreto")
    for y in (8.0, 16.0):
        for s in (-1, 1):
            C(a, cx, g + y, cz + s * hw, 2 * hw + 1.0, 0.4, 0.4, "ferro")
            C(a, cx + s * hw, g + y, cz, 0.4, 0.4, 2 * hw + 1.0, "ferro")
    for y0 in (0.6, 8.0, 16.0):
        y1 = min(y0 + 8.0, 23.7) if y0 > 1 else 8.0
        for s in (-1, 1):
            if s == -1:
                continue   # face sul livre (escada)
            viga(a, (cx - hw, g + y0, cz + s * hw), (cx + hw, g + y1, cz + s * hw), 0.28, "ferro")
            viga(a, (cx + hw, g + y0, cz + s * hw), (cx - hw, g + y1, cz + s * hw), 0.28, "ferro")
        for s in (-1, 1):
            viga(a, (cx + s * hw, g + y0, cz - hw), (cx + s * hw, g + y1, cz + hw), 0.28, "ferro")
            viga(a, (cx + s * hw, g + y0, cz + hw), (cx + s * hw, g + y1, cz - hw), 0.28, "ferro")
    # passarela a 24 m e caixa d'água octogonal (duas caixas, uma girada 45 graus)
    B(a, cx - 7.0, cx + 7.0, g + ht - 0.3, g + ht, cz - 7.0, cz + 7.0, "grade")
    C(a, cx, g + ht + 4.5, cz, 8.0, 9.0, 8.0, "ferro")
    C(a, cx, g + ht + 4.5, cz, 8.0, 9.0, 8.0, "ferro", ry=45)
    C(a, cx, g + ht + 1.2, cz, 8.4, 0.5, 8.4, "ferro", semColisao=True)
    C(a, cx, g + ht + 7.6, cz, 8.4, 0.5, 8.4, "ferro", ry=45, semColisao=True)
    C(a, cx, g + ht + 9.5, cz, 6.6, 1.0, 6.6, "ferro")
    C(a, cx, g + ht + 10.5, cz, 4.0, 1.0, 4.0, "ferro", ry=45)
    C(a, cx, g + ht + 11.5, cz, 1.2, 1.2, 1.2, "ferro")
    # letreiro desbotado na caixa, virado para o sudeste (para a Boca)
    ox, _, oz = rot((0.0, 0.0, 4.05), 0, 155, 0)
    C(a, cx + ox, g + ht + 4.5, cz + oz, 3.0, 1.6, 0.1, "chapa_clara", ry=155, semColisao=True)


def destroços_espalhados(a: Area):
    """Engarrafamentos de carros soterrados, carros soltos, rochas e árvores mortas pelo campo aberto."""
    proibidos = [(-26, 26, -26, 30), (-126, 126, 40, 135), (-400, 400, 180, 228),
                 (PRACA[0] - 22, PRACA[1] + 6, PRACA[2] - 6, PRACA[3] + 6), (TORRE[0] - 14, TORRE[0] + 14, TORRE[1] - 14, TORRE[1] + 14),
                 (ANTENA[0] - 22, ANTENA[0] + 22, ANTENA[1] - 22, ANTENA[1] + 22),
                 (ESC_OESTE[0] - 8, ESC_OESTE[0] + 8, ESC_OESTE[1] - 8, ESC_OESTE[1] + 8),
                 (ESC_LESTE[0] - 8, ESC_LESTE[0] + 8, ESC_LESTE[1] - 8, ESC_LESTE[1] + 8)]

    def livre(x, z, folga=4.0):
        if not (LX0 + 12 < x < LX1 - 12 and LZ0 + 12 < z < LZ1 - 12):
            return False
        if any(em_ret(x, z, r) for r in proibidos):
            return False
        if dist_segmento(x, z, VIA_A, VIA_B)[0] < 8:
            return False
        return not perto_de_rota(x, z, folga)

    # engarrafamentos: filas de carros ao longo de antigas avenidas, atravessando as rotas diretas
    filas = [((-150, 150), (160, 150), 7.0), ((-120, -40), (-40, 20), 7.5), ((40, 30), (150, 20), 7.0),
             ((-200, 260), (-110, 300), 7.5), ((-10, 280), (90, 300), 7.0), ((-60, 360), (40, 380), 7.0),
             ((-170, 430), (-60, 440), 7.5), ((180, 250), (260, 380), 8.0), ((90, 440), (180, 470), 7.5)]
    for (x0, z0), (x1, z1), passo in filas:
        L = math.hypot(x1 - x0, z1 - z0)
        yaw = math.degrees(math.atan2(x1 - x0, z1 - z0))
        n = int(L / passo)
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t + R.uniform(-1.5, 1.5)
            z = z0 + (z1 - z0) * t + R.uniform(-1.5, 1.5)
            if R.random() < 0.12 or not livre(x, z):
                continue
            carro(a, x, z, yaw + R.uniform(-35, 35))
    # carros soltos, rochas e árvores
    for _ in range(40):
        x, z = R.uniform(LX0, LX1), R.uniform(LZ0, LZ1)
        if livre(x, z):
            carro(a, x, z, R.uniform(0, 360))
    for _ in range(45):
        x, z = R.uniform(LX0, LX1), R.uniform(LZ0, LZ1)
        if livre(x, z, 3.0):
            rocha(a, x, z, R.uniform(1.2, 3.2))
    for _ in range(28):
        x, z = R.uniform(LX0, LX1), R.uniform(LZ0, LZ1)
        if livre(x, z, 3.0):
            arvore_morta(a, x, z)
    # postes tombados ao longo da avenida norte
    for z in range(40, 180, 26):
        if z < 135:
            continue
        x = 14.0 + R.uniform(-1, 1)
        g = alt(x, z)
        C(a, x, g + 3.0, z, 0.25, 6.5, 0.25, "metal", rz=R.uniform(-25, 25))


def area_base() -> Area:
    a = nova("superficie_aberta", "Superfície", GX0, -GX0, GZ0, GZ0 + PASSO * (NZ - 1))
    a.d["terreno"] = dict(x0=GX0, z0=GZ0, passo=PASSO, nx=NX, nz=NZ, alturas=[v for linha in ALTURAS for v in linha])
    a.d["zonasCamera"] = [{"tipo": "superficie", "min": [GX0, Y_CAIXA[0], GZ0], "max": [-GX0, Y_CAIXA[1], GZ0 + PASSO * (NZ - 1)]}]
    muralhas_do_rio(a)
    tempestade(a)
    a.d["limiteJogavel"] = dict(x0=LX0, x1=LX1, z0=LZ0, z1=LZ1)
    viaduto(a)
    antena(a)
    torre_dagua(a)
    destroços_espalhados(a)
    entrada(a, "inicio", 0.0, 12.0)
    a.d["rotasReferencia"] = {
        "marco": ROTA_MARCO, "antena": ROTA_ANTENA, "viaduto": ROTA_VIADUTO, "desabada": ROTA_DESABADA,
        "pontos": {"boca": BOCA, "marco": MARCO, "antena": ANTENA, "torre": TORRE},
    }
    return a


# ====================================================================== áreas carregadas pela distância

def boca() -> Area:
    a = nova("superficie_boca", "Boca do Poço", -40.0, 40.0, -40.0, 40.0)
    # casamata da eclusa sobre o poço (10 x 10 m), porta ao norte
    B(a, -5.0, 5.0, -1.0, 4.5, -5.0, 5.0, "concreto")
    B(a, -5.4, 5.4, 4.5, 5.0, -5.4, 5.4, "concreto_escuro")
    V(a, -1.5, 1.5, 0.0, 3.0, 5.0, 5.12, "escuro")                         # vão da porta
    B(a, -1.3, 1.3, 0.0, 2.8, 5.0, 5.18, "metal")                          # porta da eclusa (fechada)
    V(a, -0.15, 0.15, 1.2, 1.6, 5.18, 5.3, "ferrugem")                     # volante
    for x in (-1.75, 1.75):
        V(a, x - 0.25, x + 0.25, 0.0, 3.2, 5.0, 5.35, "lona_amarela")        # batentes listrados
    V(a, -1.75, 1.75, 3.0, 3.3, 5.0, 5.35, "lona_amarela")
    V(a, -0.3, 0.3, 3.45, 3.75, 5.0, 5.3, "luz_ambar")                     # lâmpada sobre a porta
    # máquinas no teto: exaustores, caixa do elevador de carga e mastro
    B(a, -3.8, -1.2, 5.0, 6.6, -3.8, -1.2, "metal")
    B(a, 1.0, 3.6, 5.0, 7.4, -3.6, -1.0, "ferrugem")
    for x, z in ((-2.5, 2.4), (2.4, 2.4)):
        B(a, x - 0.5, x + 0.5, 5.0, 6.8, z - 0.5, z + 0.5, "metal")
        V(a, x - 0.6, x + 0.6, 6.8, 7.0, z - 0.6, z + 0.6, "ferrugem")
    B(a, 4.2, 4.5, 5.0, 13.0, -4.5, -4.2, "metal")
    V(a, 4.1, 4.6, 12.6, 13.0, -4.6, -4.1, "luz_vermelha")
    # placa da eclusa
    V(a, -4.4, -2.2, 2.0, 3.0, 5.0, 5.08, "chapa_clara")
    # pátio de concreto com barreiras e sacos de areia (aberto ao norte)
    B(a, -14.0, 14.0, -0.6, 0.06, -14.0, 14.0, "concreto_escuro")
    for i in range(-12, 13, 4):
        if abs(i) > 4:
            B(a, i - 1.5, i + 1.5, 0.0, 0.9, 13.4, 14.0, "concreto")      # barreiras ao norte, com passagem central
        B(a, i - 1.5, i + 1.5, 0.0, 0.9, -14.0, -13.4, "concreto")
        B(a, -14.0, -13.4, 0.0, 0.9, i - 1.5, i + 1.5, "concreto")
        B(a, 13.4, 14.0, 0.0, 0.9, i - 1.5, i + 1.5, "concreto")
    for x, z in ((-8.0, 8.0), (8.5, 7.0), (-9.0, -6.0)):
        B(a, x - 1.6, x + 1.6, 0.0, 0.7, z - 0.6, z + 0.6, "pano")
        V(a, x - 1.2, x + 1.2, 0.7, 1.15, z - 0.5, z + 0.5, "pano")
    # poste com bandeira da vila (vermelha) e marcos de pintura no chão
    B(a, 6.8, 7.1, 0.0, 6.0, 9.8, 10.1, "metal")
    V(a, 7.1, 8.6, 5.0, 5.9, 9.9, 9.96, "lona_vermelha")
    for z in (8.0, 10.5, 13.0):
        V(a, -0.5, 0.5, 0.06, 0.08, z - 0.6, z + 0.6, "lona_amarela")
    a.saida(0.0, 0.0, "boca_estacao", "superficie", "Entrar na eclusa", tipo="eclusa")
    a.d["saidas"][-1]["z"] = 5.6
    a.d["entradas"]["boca"] = dict(x=0.0, y=0.1, z=8.0, yaw=0.0)
    a.d["entradas"]["inicio"] = dict(x=0.0, y=0.1, z=8.0, yaw=0.0)
    return a


def ruinas() -> Area:
    a = nova("superficie_ruinas", "Ruínas Próximas", -126.0, 126.0, 40.0, 135.0)
    for q in PREDIOS:
        predio(a, q, quebrado=q["andares"] > 1, telhado=True)
    # posto de gasolina: cobertura sobre pilares e ilhas das bombas
    x0, x1, z0, z1 = POSTO
    g = alt((x0 + x1) / 2, (z0 + z1) / 2)
    for x in (x0 + 2, x1 - 2):
        for z in (z0 + 2, z1 - 2):
            B(a, x - 0.35, x + 0.35, g - 1.0, g + 5.0, z - 0.35, z + 0.35, "metal")
    C(a, (x0 + x1) / 2, g + 5.3, (z0 + z1) / 2, x1 - x0, 0.6, z1 - z0 - 2, "chapa_clara", rz=-6)
    for z in (z0 + 5, z1 - 5):
        B(a, x0 + 6, x1 - 6, g - 0.3, g + 0.25, z - 0.8, z + 0.8, "concreto")
        for x in (x0 + 8, x1 - 8):
            B(a, x - 0.4, x + 0.4, g + 0.25, g + 1.7, z - 0.3, z + 0.3, "lona_vermelha")
    # entulho de prédio desabado (com duas brechas), mais alto que o pulo
    z0, z1 = ENTULHO_Z
    for x0, x1 in ENTULHO_X:
        x = x0
        while x < x1 - 0.5:
            w = min(R.uniform(4.0, 7.0), x1 - x)
            h = R.uniform(1.7, 2.8)
            g = alt_min(x, x + w, z0, z1)
            C(a, x + w / 2, g + h / 2 - 0.4, (z0 + z1) / 2 + R.uniform(-0.6, 0.6), w + 0.6, h + 0.8, z1 - z0 + R.uniform(-0.5, 1.0),
              R.choice(["concreto", "tijolo", "reboco", "areia"]), ry=R.uniform(-6, 6), rz=R.uniform(-5, 5))
            x += w
        # vergalhões e lajes inclinadas por cima
        for _ in range(2):
            x = R.uniform(x0 + 2, x1 - 2)
            g = alt(x, (z0 + z1) / 2)
            C(a, x, g + 2.6, (z0 + z1) / 2, 4.0, 0.3, 3.0, "concreto", rz=R.uniform(15, 30), ry=R.uniform(-20, 20), semColisao=True)
    # muros quebrados, carros e sucata entre os prédios
    for x, z, w, d in ((-12, 52, 9, 0.5), (14, 62, 0.5, 8), (-58, 84, 10, 0.5), (60, 84, 0.5, 9), (-48, 58, 0.5, 6),
                       (8, 108, 7, 0.5), (-96, 76, 0.5, 10), (92, 104, 8, 0.5)):
        if perto_de_rota(x, z, 4.0):
            continue
        g = alt(x, z)
        h = R.uniform(1.2, 2.6)
        B(a, x - w / 2, x + w / 2, g - 0.5, g + h, z - d / 2, z + d / 2, R.choice(["tijolo", "reboco", "concreto"]))
    vagas = [(-14, 46, 80), (6, 58, 10), (20, 72, 95), (-48, 96, 30), (-20, 100, 120), (48, 76, 170), (80, 66, 60),
             (-100, 60, 0), (-60, 66, 75), (14, 118, 85), (-34, 112, 10), (90, 120, 140), (108, 84, 20)]
    for x, z, yaw in vagas:
        if not perto_de_rota(x, z, 3.5):
            carro(a, x, z, yaw)
    for _ in range(14):
        x, z = R.uniform(-110, 110), R.uniform(45, 120)
        if perto_de_rota(x, z, 3.0) or any(em_ret(x, z, (q["x0"], q["x1"], q["z0"], q["z1"]), 3) for q in PREDIOS) or em_ret(x, z, POSTO, 2):
            continue
        g = alt(x, z)
        s = R.uniform(0.6, 1.4)
        C(a, x, g + s * 0.3, z, s * 1.6, s * 0.9, s * 1.2, R.choice(["ferrugem", "metal", "madeira", "chapa_azul"]),
          ry=R.uniform(0, 180), rz=R.uniform(-15, 15))
    entrada(a, "inicio", -29.8, 56.0, 0.0)
    return a


def escotilha(id_, nome, pos) -> Area:
    x, z = pos
    a = nova(id_, nome, x - 24, x + 24, z - 22, z + 22)
    g = alt(x, z)
    B(a, x - 1.8, x + 1.8, g - 1.0, g + 0.5, z - 1.8, z + 1.8, "concreto")           # gola de concreto
    B(a, x - 1.1, x + 1.1, g + 0.5, g + 0.62, z - 1.1, z + 1.1, "metal")              # alçapão fechado
    V(a, x - 0.08, x + 0.08, g + 0.62, g + 0.82, z - 0.6, z + 0.6, "ferrugem")        # alavanca da tranca
    V(a, x - 0.9, x + 0.9, g + 0.62, g + 0.64, z - 0.12, z + 0.12, "lona_amarela")
    B(a, x + 2.6, x + 2.85, g, g + 4.5, z + 2.0, z + 2.25, "ferrugem")                # estaca de sinalização
    V(a, x + 2.85, x + 4.0, g + 3.7, g + 4.4, z + 2.08, z + 2.14, "lona_vermelha")
    for ang in range(0, 360, 45):                                                     # sacos de areia em volta
        if ang in (135, 180):
            continue
        ox, _, oz = rot((0.0, 0.0, 3.6), 0, ang, 0)
        C(a, x + ox, g + 0.3, z + oz, 1.8, 0.6, 0.7, "pano", ry=ang + 90)
    carro(a, x - 9.0, z + 6.0, 35)
    rocha(a, x + 8.0, z - 7.0, 2.4)
    entrada(a, "escotilha", x, z - 3.0, 0.0)
    entrada(a, "inicio", x, z - 6.0, 0.0)
    return a


def rio() -> Area:
    a = nova("superficie_rio", "Leito Seco do Rio", LX0, LX1, 178.0, 228.0)
    # travessia 1: ponte de concreto inteira (tabuleiro, guarda-corpos e pilares no leito)
    x0, x1, z0, z1 = PONTE
    B(a, x0, x1, Y_PONTE - 0.8, Y_PONTE, z0, z1, "concreto")
    V(a, x0 + 1.2, x1 - 1.2, Y_PONTE, Y_PONTE + 0.02, z0 + 0.5, z1 - 0.5, "asfalto")
    corrimao(a, "z", x0 + 0.2, z0 + 1.0, z1 - 1.0, Y_PONTE)
    corrimao(a, "z", x1 - 0.2, z0 + 1.0, z1 - 1.0, Y_PONTE)
    for z in (199.0, 208.0):
        B(a, x0 + 1.0, x1 - 1.0, Y_LEITO - 0.5, Y_PONTE - 0.8, z - 0.9, z + 0.9, "concreto")
    # travessia 2: ponte desabada, o tabuleiro caiu e virou duas rampas de entulho pelo leito
    d0, d1 = DESAB_X
    # rampas a ~15 graus, com o terreno rebaixado embaixo (o degrau íngreme junto às muralhas barraria a subida)
    xm = (d0 + d1) / 2
    for (z0, y0), (z1, y1) in (RAMPA_S, RAMPA_N):
        laje_entre(a, (xm, z0), (xm, z1), y0, y1, d1 - d0, 1.2, "concreto")
    for z in (194.0, 214.0):   # entulho que escora as rampas
        B(a, d0 + 0.5, d1 - 0.5, Y_LEITO - 0.3, Y_LEITO + 1.2, z - 2.0, z + 2.0, "concreto_escuro")
    for z in (186.0, 222.0):   # cabeceiras quebradas
        B(a, DESAB[0] - 1.0, DESAB[0] + 0.6, -0.5, 1.4, z - 2.0, z + 2.0, "concreto")
        B(a, DESAB[1] - 0.6, DESAB[1] + 1.0, -0.5, 1.1, z - 2.0, z + 2.0, "concreto")
    # pedaços do tabuleiro e pilar tombado no meio do leito (obstáculos, com passagem)
    C(a, 103.5, Y_LEITO + 0.6, 203.5, 5.0, 1.0, 6.0, "concreto", ry=18, rz=9)
    C(a, 111.5, Y_LEITO + 0.9, 205.0, 1.6, 1.6, 7.0, "concreto", ry=-40)
    # entulho, carro e pedras no leito
    for x, z, s in ((-140, 200, 2.2), (-90, 210, 1.6), (30, 196, 2.6), (70, 211, 1.8), (160, 202, 2.4), (230, 207, 2.0),
                    (-230, 197, 2.6), (-20, 205, 1.4)):
        rocha(a, x, z, s)
    carro(a, 58.0, 203.0, 75)
    carro(a, -190.0, 205.0, 120)
    for x, z, w in ((-120, 193.0, 5.0), (12, 214.0, 4.0), (190, 193.0, 6.0)):   # lascas caídas da muralha
        C(a, x, Y_LEITO + 0.6, z, w, 1.2, 1.6, "concreto", ry=R.uniform(-15, 15), rz=R.uniform(-10, 10))
    # placa de rua antiga perto da ponte
    B(a, -51.0, -50.75, 0.0, 3.2, 180.0, 180.25, "metal")
    V(a, -52.4, -49.4, 2.5, 3.2, 180.25, 180.3, "chapa_verde")
    entrada(a, "inicio", -44.0, 176.0, 0.0)
    entrada(a, "desabada", 106.0, 172.0, 0.0)
    return a


def marco() -> Area:
    a = nova("superficie_praca_marco", "O Marco", -104.0, -12.0, 226.0, 292.0)
    x0, x1, z0, z1 = PRACA
    g = alt(*MARCO)
    # calçamento em placas e mureta da praça antiga (aberturas nos quatro lados)
    for i, x in enumerate(range(int(x0), int(x1), 4)):
        for j, z in enumerate(range(int(z0), int(z1), 4)):
            if R.random() < 0.18:
                continue
            mat = "reboco" if (i + j) % 2 else "concreto"
            B(a, x + 0.05, x + 3.95, g - 0.3, g + 0.08, z + 0.05, z + 3.95, mat)
    for (eixo, fixo, ini, fim) in (("x", z0, x0, x1), ("x", z1, x0, x1), ("z", x0, z0, z1), ("z", x1, z0, z1)):
        meio = (ini + fim) / 2
        parede(a, eixo, fixo, ini, fim, g - 0.4, g + 0.75, 0.4, [(meio - 3.0, meio + 3.0, g - 0.4, g + 0.75)], "reboco")
    # o Marco: base em degraus, pedestal e obelisco levemente inclinado
    mx, mz = MARCO
    for k, (hw, y1) in enumerate(((4.4, 0.3), (3.4, 0.6), (2.4, 0.9))):
        B(a, mx - hw, mx + hw, g - 0.2, g + y1, mz - hw, mz + hw, "concreto")
    B(a, mx - 1.5, mx + 1.5, g + 0.9, g + 3.6, mz - 1.5, mz + 1.5, "chapa_clara")
    V(a, mx - 1.0, mx + 1.0, g + 1.8, g + 2.8, mz - 1.53, mz - 1.5, "metal")           # placa de bronze
    C(a, mx, g + 3.6 + 5.0, mz, 1.5, 10.0, 1.5, "chapa_clara", rz=3.0)
    C(a, mx + 0.62, g + 3.6 + 12.0, mz, 1.0, 4.4, 1.0, "chapa_clara", rz=3.0)
    C(a, mx + 0.82, g + 3.6 + 14.6, mz, 0.6, 1.0, 0.6, "metal", rz=3.0, ry=45)
    # chafariz seco, bancos, postes e árvores mortas
    fx, fz = mx + 9.0, mz + 8.0
    for s in (-1, 1):
        B(a, fx - 3.0, fx + 3.0, g, g + 0.55, fz + s * 3.0 - 0.25, fz + s * 3.0 + 0.25, "concreto")
        B(a, fx + s * 3.0 - 0.25, fx + s * 3.0 + 0.25, g, g + 0.55, fz - 3.0, fz + 3.0, "concreto")
    B(a, fx - 0.4, fx + 0.4, g, g + 1.6, fz - 0.4, fz + 0.4, "concreto")
    for x, z, r in ((mx - 10, mz - 6, 0), (mx - 10, mz + 6, 0), (mx + 10, mz - 7, 90), (mx - 4, mz + 11, 90)):
        if r:
            B(a, x - 0.3, x + 0.3, g, g + 0.45, z - 1.0, z + 1.0, "madeira")
        else:
            B(a, x - 1.0, x + 1.0, g, g + 0.45, z - 0.3, z + 0.3, "madeira")
    for x, z in ((x0 + 3, z0 + 3), (x1 - 3, z0 + 3), (x0 + 3, z1 - 3), (x1 - 3, z1 - 3)):
        C(a, x, g + 2.8, z, 0.2, 5.6, 0.2, "metal", rz=R.uniform(-12, 12))
    for x, z in ((mx - 14, mz + 12), (mx + 14, mz - 11), (mx - 15, mz - 12), (mx + 4, mz - 12)):
        arvore_morta(a, x, z, R.uniform(5.0, 7.0))
    # fachadas em ruínas em volta da praça e o prédio que serve de abrigo
    predio(a, PREDIO_MARCO)
    for (fx0, fx1, fz0, fz1, h) in ((-66.0, -40.0, 276.0, 276.6, 9.0), (-26.0, -25.4, 240.0, 262.0, 6.5), (-62.0, -50.0, 232.0, 232.6, 4.0)):
        gg = alt_min(fx0, fx1, fz0, fz1)
        eixo = "x" if fx1 - fx0 > fz1 - fz0 else "z"
        if eixo == "x":
            vaos = [(x, x + 1.4, gg + 1.2, gg + 2.6) for x in range(int(fx0) + 2, int(fx1) - 2, 4)]
            parede(a, "x", (fz0 + fz1) / 2, fx0, fx1, gg - 1.0, gg + h, fz1 - fz0, vaos, "tijolo")
        else:
            vaos = [(z, z + 1.4, gg + 1.2, gg + 2.6) for z in range(int(fz0) + 2, int(fz1) - 2, 4)]
            parede(a, "z", (fx0 + fx1) / 2, fz0, fz1, gg - 1.0, gg + h, fx1 - fx0, vaos, "reboco")
    entrada(a, "inicio", mx, mz - 12.0, 0.0)
    return a


def torre() -> Area:
    cx, cz = TORRE
    a = nova("superficie_torre", "Torre d'Água", cx - 32, cx + 32, cz - 32, cz + 32)
    g = alt(cx, cz)
    ht = 24.0
    # escada de mão na face sul até a passarela, guarda-corpo da passarela (vão na escada)
    a.d["escadas"].append(dict(x=cx, z=r3(cz - 7.35), y0=r3(g), y1=r3(g + ht), tipo="escada", yaw=0))
    y = g + ht
    corrimao(a, "x", cz + 6.9, cx - 6.9, cx + 6.9, y)
    corrimao(a, "x", cz - 6.9, cx - 6.9, cx + 6.9, y, lacunas=[(cx - 0.8, cx + 0.8)])
    corrimao(a, "z", cx - 6.9, cz - 6.9, cz + 6.9, y)
    corrimao(a, "z", cx + 6.9, cz - 6.9, cz + 6.9, y)
    # cerca derrubada em volta, casinha da bomba e tubo
    for ang in range(0, 360, 30):
        if ang in (180, 210):
            continue
        ox, _, oz = rot((0.0, 0.0, 12.0), 0, ang, 0)
        C(a, cx + ox, alt(cx + ox, cz + oz) + 0.8, cz + oz, 0.12, 1.6, 0.12, "metal", rz=R.uniform(-20, 20))
        ox2, _, oz2 = rot((0.0, 0.0, 12.0), 0, ang + 30, 0)
        if R.random() < 0.6:
            mx, mz = (cx + ox + cx + ox2) / 2, (cz + oz + cz + oz2) / 2
            C(a, mx, alt(mx, mz) + 1.2, mz, 0.05, 1.0, math.hypot(ox2 - ox, oz2 - oz), "grade", ry=ang + 105, semColisao=True)
    B(a, cx + 7.0, cx + 11.0, g - 0.5, g + 2.6, cz - 2.0, cz + 2.0, "tijolo")
    V(a, cx + 6.96, cx + 7.0, g, g + 2.0, cz - 0.5, cz + 0.5, "escuro")
    B(a, cx - 0.4, cx + 0.4, g, g + 24.0, cz + 0.6, cz + 1.4, "ferrugem")
    carro(a, cx - 15.0, cz - 9.0, 200)
    entrada(a, "inicio", cx, cz - 14.0, 0.0)
    return a


def viaduto_area() -> Area:
    a = nova("superficie_viaduto", "Viaduto Caído", 36.0, 172.0, 312.0, 404.0)
    dx, dz = VIA_B[0] - VIA_A[0], VIA_B[1] - VIA_A[1]
    yaw = math.degrees(math.atan2(dx, dz))

    def P(t, lado=0.0):
        L = math.hypot(dx, dz)
        return (VIA_A[0] + dx * t + dz / L * lado, VIA_A[1] + dz * t - dx / L * lado)

    # carros e um ônibus parados no tabuleiro (é preciso contornar)
    for t, lado, gy in ((0.4, -2.2, 0), (0.52, 2.4, 25), (0.68, -1.5, -15), (0.83, 2.6, 180)):
        x, z = P(t, lado)
        C(a, x, Y_VIA + 0.65, z, 1.8, 1.3, 4.3, R.choice(["carro_vermelho", "carro_azul", "ferrugem"]), ry=yaw + gy)
        ox, oy, oz = rot((0.0, 1.0, -0.3), 0, yaw + gy, 0)
        C(a, x + ox, Y_VIA + 0.65 + oy, z + oz, 1.6, 0.75, 2.2, "ferrugem", ry=yaw + gy)
    x, z = P(0.6, 0.6)
    C(a, x, Y_VIA + 1.5, z, 2.6, 3.0, 11.0, "lona_amarela", ry=yaw + 8)
    C(a, x, Y_VIA + 2.3, z, 2.64, 0.8, 10.6, "escuro", ry=yaw + 8, semColisao=True)
    # ônibus caído ao pé do vão desabado e entulho
    x, z = P(0.05, 7.0)
    C(a, x, alt(x, z) + 1.0, z, 2.6, 3.0, 11.0, "ferrugem", ry=yaw + 70, rz=70)
    for t, lado in ((0.08, -6.0), (0.18, 7.5), (0.3, -8.0), (0.45, 9.0)):
        x, z = P(t, lado)
        rocha(a, x, z, R.uniform(1.6, 2.8))
    # placa de trânsito torta no tabuleiro
    x, z = P(0.95, -4.4)
    C(a, x, Y_VIA + 2.0, z, 0.2, 4.0, 0.2, "metal", rz=10)
    C(a, x, Y_VIA + 3.8, z, 0.1, 1.2, 2.6, "chapa_verde", ry=yaw + 90, rz=10)
    x, z = P(-0.06)
    entrada(a, "inicio", x, z, math.radians(yaw))
    return a


def colina_area() -> Area:
    cx, cz = ANTENA
    a = nova("superficie_colina", "Colina da Antena", -40.0, 116.0, 410.0, 560.0)
    g = base(*ANTENA) + ALT_COLINA
    # escada de mão até a plataforma do mirante (10 m) e guarda-corpo da plataforma
    m = ANT_PLAT - 0.1
    a.d["escadas"].append(dict(x=cx, z=r3(cz - ANT_PLAT - 0.35), y0=r3(g), y1=r3(g + Y_PLAT), tipo="escada", yaw=0))
    y = g + Y_PLAT
    corrimao(a, "x", cz + m, cx - m, cx + m, y)
    corrimao(a, "x", cz - m, cx - m, cx + m, y, lacunas=[(cx - 0.8, cx + 0.8)])
    corrimao(a, "z", cx - m, cz - m, cz + m, y)
    corrimao(a, "z", cx + m, cz - m, cz + m, y)
    # cabana de equipamentos (abrigo), cerca caída, carretéis de cabo e baterias
    predio(a, CABANA, quebrado=False, telhado=True)
    for x0, x1, z0, z1 in ((cx - 14, cx - 4, cz + 13.5, cz + 13.6), (cx + 4, cx + 14, cz + 13.5, cz + 13.6),
                           (cx + 13.5, cx + 13.6, cz - 14, cz + 2)):
        n = int(max(x1 - x0, z1 - z0) / 2.5)
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            z = z0 + (z1 - z0) * i / n
            C(a, x, alt(x, z) + 0.9, z, 0.12, 1.8, 0.12, "metal", rz=R.uniform(-15, 15))
    for x, z in ((cx + 9, cz + 6), (cx + 8, cz - 9)):
        C(a, x, g + 0.8, z, 1.6, 1.6, 0.8, "madeira", ry=R.uniform(0, 90))
    B(a, cx - 9.5, cx - 7.5, g, g + 1.2, cz - 9.0, cz - 6.0, "chapa_verde")
    # pedras e árvores mortas na encosta (cobertura e referência de subida)
    for _ in range(26):
        ang = R.uniform(0, 2 * math.pi)
        r = R.uniform(22, 64)
        x, z = cx + math.cos(ang) * r, cz + math.sin(ang) * r
        if perto_de_rota(x, z, 3.0) or not (LZ0 < z < LZ1 - 10):
            continue
        if R.random() < 0.7:
            rocha(a, x, z, R.uniform(1.0, 2.6))
        else:
            arvore_morta(a, x, z)
    entrada(a, "inicio", cx, cz - 9.0, 0.0)
    entrada(a, "topo", cx, cz - ANT_PLAT - 1.2, 0.0)
    return a


def todas():
    return [area_base(), boca(), ruinas(), escotilha("superficie_escotilha_oeste", "Escotilha Oeste", ESC_OESTE),
            escotilha("superficie_escotilha_leste", "Escotilha Leste", ESC_LESTE), rio(), marco(), torre(),
            viaduto_area(), colina_area()]


def salvar(area: Area):
    """A área base vai compacta (a grade do terreno tem ~39 mil alturas); as outras, como as demais áreas."""
    if "terreno" not in area.d:
        area.salvar()
        return
    import json
    from gerar_areas import DESTINO
    with open(os.path.join(DESTINO, f"{area.d['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(area.d, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{area.d['id']}: terreno {NX} x {NZ}, {len(area.d['solidos'])} sólidos")


if __name__ == "__main__":
    for area in todas():
        salvar(area)
