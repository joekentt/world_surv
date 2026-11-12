"""Vila Cisterna em três níveis, em blocos (revisão 2, fase 2, tarefa 2).

Uso: python3 tools/areas/subsolo_vila.py   (grava content/areas/vila_*.json)

Seção 5.1 de docs/spec/05-mapa.md e seção 7 de docs/spec/07-arte-personagens-vila.md.
Mundo "subsolo"; as áreas antigas da revisão 1 (praca, galerias, capela) continuam intactas.

Eixos: Y para cima, norte em +Z. A caverna vai de x = -70 a 70 e de z = -45 a 45, piso em y = 0
e teto a 25 m. Níveis:
  - piso: Praça do Reservatório (50 x 40 m) no centro, mercado de lonas, bomba d'água, Muro dos
    Subidores, casas em volta e o Portão da Caravana na parede sul (fechado, atrás de uma grade);
  - passarelas: passarela norte a 10 m (sede do Conselho a oeste até a Capela a leste), ponte sobre
    a praça a 8 m com mirante para o Portão e passarela leste a 10 m com mirante a 12 m;
  - Galerias Secas a 5 m abaixo do piso, com dois acessos por escadaria (circuito) e o poço vertical
    de 20 m (y de -5 a -25), aberto para a caverna, com barracos em andares ligados por escadas de mão
    e uma grade sobre o poço profundo no fundo.
Todos os valores respeitam src/config.ts: degraus de 0,25 m, corredores de 3,5 m, escadas de mão
encostadas numa face com o topo saindo para cima de um piso.
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_areas import AMBAR, FRIA, Area  # noqa: E402

R = random.Random(42)
DOURADO = [1.0, 0.86, 0.6]

DEGRAU = 0.25   # altura de cada degrau (máximo do personagem: 0,35)
PISADA = 0.4    # profundidade de cada degrau
CORRIMAO = 1.1  # altura dos guarda-corpos
ESP = 0.3       # espessura das passarelas

# Caverna
CX0, CX1, CZ0, CZ1, TETO = -70.0, 70.0, -45.0, 45.0, 25.0
LAJE = 1.5  # espessura do piso da caverna (as Galerias ficam embaixo)

# Galerias e poço
YG = -5.0                                  # piso das Galerias
G1 = (-37.5, -34.0, -16.0, 1.5)            # corredor oeste (x0, x1, z0, z1)
G3 = (-34.0, 30.0, -13.75, -10.25)         # corredor sob a praça
ESC_A = (-34.0, -26.0, -2.0, 1.5)          # escadaria do acesso oeste (desce para -x)
ESC_B = (30.0, 38.0, -13.75, -10.25)       # escadaria do acesso leste (sobe para +x)
POCO = (-47.0, -33.0, -31.0, -17.0)        # interior do poço vertical
FUNDO = YG - 20.0                          # fundo do poço (-25)
BURACO = (-43.0, -37.0, -27.0, -21.0)      # grade sobre o poço profundo

# Boca do Duto Norte na parede norte (x0, x1, altura); o duto em si fica em subsolo_duto.py
BOCA_DUTO = (-4.0, 4.0, 5.5)

# Passarelas e Capela
YP = 10.0
P2 = (-44.0, 44.0, 22.0, 25.0)             # passarela norte
CONSELHO = (-60.0, -44.0, 14.0, 32.0)
CAPELA = (46.0, 64.0, 12.0, 32.0)          # paredes da casa de máquinas
CAPELA_PISO = (44.0, 64.0, 10.0, 32.0)     # piso com sacada a oeste e ao sul
P3 = (50.0, 53.0, -27.0, 10.0)             # passarela leste
P4 = (-1.5, 1.5)                           # ponte sobre a praça (largura em x)
YP4 = 8.0
ESCADA_P3 = dict(x=50.05, z=-5.0, y0=0.0, y1=YP, tipo="escada", yaw=90)
# ponto inicial do jogo na praça (x, z, yaw em radianos)
INICIO_JOGO = (2.5, -19.0, -0.12)


def r3(v):
    return round(v, 3)


def B(a: Area, x0, x1, y0, y1, z0, z1, mat="parede", **k):
    """Caixa pelos limites (x0..x1, y0..y1, z0..z1)."""
    if x1 - x0 <= 1e-3 or y1 - y0 <= 1e-3 or z1 - z0 <= 1e-3:
        return
    a.d["solidos"].append(dict(x=r3((x0 + x1) / 2), y=r3((y0 + y1) / 2), z=r3((z0 + z1) / 2),
                               w=r3(x1 - x0), h=r3(y1 - y0), d=r3(z1 - z0), mat=mat, **k))


def V(a: Area, *args, **k):
    """Caixa só visual (sem colisão)."""
    B(a, *args, semColisao=True, **k)


def X(a: Area, *args, **k):
    """Caixa só visual substituída por uma peça de kit (tools/blender/kits/kits_r2.py): não entra na área, mas os
    argumentos continuam sendo avaliados, para o sorteio (R) seguir igual e o resto da vila não mudar."""


def laje(a: Area, x0, x1, z0, z1, y0, y1, furos=(), mat="chao", **k):
    """Laje retangular com furos retangulares: decompõe em faixas sem sobreposição."""
    xs = sorted({x0, x1, *[c for f in furos for c in (f[0], f[1]) if x0 < c < x1]})
    zs = sorted({z0, z1, *[c for f in furos for c in (f[2], f[3]) if z0 < c < z1]})

    def furada(cx, cz):
        return any(f[0] <= cx <= f[1] and f[2] <= cz <= f[3] for f in furos)

    linhas = []
    for j in range(len(zs) - 1):
        cz = (zs[j] + zs[j + 1]) / 2
        faixas, ini = [], None
        for i in range(len(xs) - 1):
            cx = (xs[i] + xs[i + 1]) / 2
            if not furada(cx, cz):
                ini = xs[i] if ini is None else ini
                fim = xs[i + 1]
            elif ini is not None:
                faixas.append((ini, fim))
                ini = None
        if ini is not None:
            faixas.append((ini, fim))
        linhas.append((zs[j], zs[j + 1], tuple(faixas)))
    # junta linhas vizinhas com as mesmas faixas
    juntas = []
    for z_a, z_b, f in linhas:
        if juntas and juntas[-1][2] == f and abs(juntas[-1][1] - z_a) < 1e-6:
            juntas[-1] = (juntas[-1][0], z_b, f)
        else:
            juntas.append((z_a, z_b, f))
    for z_a, z_b, faixas in juntas:
        for fx0, fx1 in faixas:
            B(a, fx0, fx1, y0, y1, z_a, z_b, mat, **k)


def corrimao(a: Area, eixo, fixo, ini, fim, y, lacunas=(), lado=0.0):
    """Guarda-corpo ao longo de x (eixo 'x', em z = fixo) ou de z (eixo 'z', em x = fixo).
    Colisão invisível que não barra a câmera; visual com barras e postes. `lado` desloca para dentro."""
    trechos, atual = [], ini
    for g0, g1 in sorted(lacunas):
        if g0 > atual:
            trechos.append((atual, min(g0, fim)))
        atual = max(atual, g1)
    if atual < fim:
        trechos.append((atual, fim))
    f = fixo + lado
    for t0, t1 in trechos:
        if t1 - t0 < 0.05:
            continue
        if eixo == "x":
            B(a, t0, t1, y, y + CORRIMAO, f - 0.05, f + 0.05, "metal", invisivel=True, semCamera=True)
            V(a, t0, t1, y + CORRIMAO - 0.08, y + CORRIMAO, f - 0.04, f + 0.04, "ferrugem")
            V(a, t0, t1, y + 0.5, y + 0.56, f - 0.03, f + 0.03, "metal")
        else:
            B(a, f - 0.05, f + 0.05, y, y + CORRIMAO, t0, t1, "metal", invisivel=True, semCamera=True)
            V(a, f - 0.04, f + 0.04, y + CORRIMAO - 0.08, y + CORRIMAO, t0, t1, "ferrugem")
            V(a, f - 0.03, f + 0.03, y + 0.5, y + 0.56, t0, t1, "metal")
        n = max(1, int((t1 - t0) / 1.6))
        for i in range(n + 1):
            p = t0 + (t1 - t0) * i / n
            if eixo == "x":
                V(a, p - 0.04, p + 0.04, y, y + CORRIMAO, f - 0.04, f + 0.04, "metal")
            else:
                V(a, f - 0.04, f + 0.04, y, y + CORRIMAO, p - 0.04, p + 0.04, "metal")


def lance(a: Area, x0, x1, z0, z1, y0, y1, sentido, base=None, mat="concreto"):
    """Lance de escadaria de y0 a y1 com degraus de DEGRAU m e pisada de PISADA m.
    sentido: '+x', '-x', '+z' ou '-z' (para onde se sobe). Cada degrau é um bloco desde `base`.
    O primeiro degrau começa na borda de entrada; o último tem topo em y1."""
    n = round(abs(y1 - y0) / DEGRAU)
    base = min(y0, y1) if base is None else base
    for i in range(n):
        topo = y0 + DEGRAU * (i + 1) * (1 if y1 > y0 else -1)
        if y1 < y0:  # descendo no sentido indicado
            topo = y0 - DEGRAU * (i + 1)
        if sentido == "+x":
            B(a, x0 + PISADA * i, x0 + PISADA * (i + 1), base, topo, z0, z1, mat)
        elif sentido == "-x":
            B(a, x1 - PISADA * (i + 1), x1 - PISADA * i, base, topo, z0, z1, mat)
        elif sentido == "+z":
            B(a, x0, x1, base, topo, z0 + PISADA * i, z0 + PISADA * (i + 1), mat)
        else:
            B(a, x0, x1, base, topo, z1 - PISADA * (i + 1), z1 - PISADA * i, mat)
    return n * PISADA


def escada_mao(a: Area, x, z, y0, y1, yaw):
    a.d["escadas"].append(dict(x=r3(x), z=r3(z), y0=y0, y1=y1, tipo="escada", yaw=yaw))


def zona_tunel(a: Area, x0, x1, y0, y1, z0, z1):
    a.d.setdefault("zonasCamera", []).append({"tipo": "tunel", "min": [x0, y0, z0], "max": [x1, y1, z1]})


def colunas_da_caverna():
    xs = [-66, -54, -42, -30, -18, -6, 6, 18, 30, 42, 54, 66]
    zs = [-42, -30, -18, -6, 6, 18, 30, 42]
    return [(x, z) for x in xs for z in zs]


def sobrepoe(r, s, folga=0.0):
    return r[0] < s[1] + folga and r[1] > s[0] - folga and r[2] < s[3] + folga and r[3] > s[2] - folga


# áreas reservadas no piso (sem colunas nem casas): buracos, construções e ruas
FUROS_PISO = [ESC_A, ESC_B, POCO]
CONSTRUCOES = [CONSELHO, (44.0, 64.0, 10.0, 34.0), (48.0, 56.0, -36.0, -30.0)]
SEM_COLUNAS = [(-12.0, 12.0, -45.0, -36.0)]  # largo diante do Portão
RUAS = [
    (-25.0, 25.0, -20.0, 20.0),     # praça
    (-70.0, 70.0, -8.0, -2.0),      # rua leste-oeste (até a escada de mão da passarela leste)
    (25.0, 42.0, -16.0, -8.0),      # saída da escadaria leste das Galerias
    (-5.0, 5.0, -45.0, 45.0),       # eixo norte-sul até o Portão
    (-13.0, 13.0, -45.0, -20.0),    # largo do Portão
    (-45.0, -16.0, 8.0, 24.0),      # caminho até a escadaria da passarela norte
    (-36.0, -24.0, -4.0, 3.5),      # boca da escadaria oeste das Galerias
    (-50.0, -30.0, -34.0, -14.0),   # poço e guarda-corpo
    (44.0, 52.0, -9.0, -1.0),       # pé da escada de mão
]


def casa(a: Area, x0, x1, z0, z1, h, mat, frente):
    """Casa de chapa e concreto, com telhado, porta e janela acesa na face `frente` (+x, -x, +z, -z)."""
    B(a, x0, x1, 0, h, z0, z1, mat)
    V(a, x0 - 0.25, x1 + 0.25, h, h + 0.18, z0 - 0.25, z1 + 0.25, R.choice(["ferrugem", "chapa_clara", "metal"]))
    w, d = x1 - x0, z1 - z0
    if frente in ("+z", "-z"):
        zf = z1 + 0.03 if frente == "+z" else z0 - 0.03
        px = x0 + w * 0.3
        V(a, px - 0.5, px + 0.5, 0, 2.0, zf - 0.03, zf + 0.03, "escuro")
        jx = x0 + w * 0.72
        V(a, jx - 0.45, jx + 0.45, 1.2, 1.9, zf - 0.04, zf + 0.04, "janela")
    else:
        xf = x1 + 0.03 if frente == "+x" else x0 - 0.03
        pz = z0 + d * 0.3
        V(a, xf - 0.03, xf + 0.03, 0, 2.0, pz - 0.5, pz + 0.5, "escuro")
        jz = z0 + d * 0.72
        V(a, xf - 0.04, xf + 0.04, 1.2, 1.9, jz - 0.45, jz + 0.45, "janela")
    if R.random() < 0.4 and w > 4 and d > 4:  # segundo andar
        h2 = h + 2.8
        B(a, x0 + 0.6, x1 - 1.2, h + 0.18, h2, z0 + 0.6, z1 - 1.0, R.choice(["chapa_azul", "chapa_verde", "madeira", "concreto"]))
        V(a, x0 + 0.4, x1 - 1.0, h2, h2 + 0.15, z0 + 0.4, z1 - 0.8, "ferrugem")


# ====================================================================== caverna (piso e passarelas)

def caverna() -> Area:
    a = Area("vila_cisterna", "Vila Cisterna", "subsolo", "vila", None, CX0, CX1)
    a.d["zonaPadrao"] = "vila"
    a.d["kits"] = ["r2_cisterna"]
    a.caixa((CX0, -2.0, CZ0 - 16.0), (CX1, TETO + 2.0, CZ1))

    # --- casca: piso com furos (acessos às Galerias e poço), paredes, teto
    laje(a, CX0, CX1, CZ0, CZ1, -LAJE, 0.0, FUROS_PISO, "chao")
    B(a, CX0 - 2, CX0, -LAJE, TETO, CZ0 - 2, CZ1 + 2, "rocha")
    B(a, CX1, CX1 + 2, -LAJE, TETO, CZ0 - 2, CZ1 + 2, "rocha")
    # parede norte com a boca do Duto Norte (x de -4 a 4, 5,5 m de altura; ver subsolo_duto.py)
    B(a, CX0, BOCA_DUTO[0], -LAJE, TETO, CZ1, CZ1 + 2, "rocha")
    B(a, BOCA_DUTO[1], CX1, -LAJE, TETO, CZ1, CZ1 + 2, "rocha")
    B(a, BOCA_DUTO[0], BOCA_DUTO[1], BOCA_DUTO[2], TETO, CZ1, CZ1 + 2, "rocha")
    # parede sul com a boca do Portão da Caravana (16 m de largura, 14 m de altura)
    B(a, CX0, -8.0, -LAJE, TETO, CZ0 - 2, CZ0, "rocha")
    B(a, 8.0, CX1, -LAJE, TETO, CZ0 - 2, CZ0, "rocha")
    B(a, -8.0, 8.0, 14.0, TETO, CZ0 - 2, CZ0, "rocha")
    B(a, CX0 - 2, CX1 + 2, TETO, TETO + 2, CZ0 - 2, CZ1 + 2, "rocha")

    # --- rochas irregulares nas paredes e estalactites (quebram a caixa)
    for _ in range(46):
        lado = R.choice(["o", "l", "n", "s"])
        w, h, d = R.uniform(3, 9), R.uniform(3, 14), R.uniform(3, 9)
        y0 = R.choice([0.0, 0.0, R.uniform(4, 18)])
        if lado == "o":
            cx, cz = CX0 + R.uniform(-1, 1.5), R.uniform(CZ0 + 4, CZ1 - 4)
        elif lado == "l":
            cx, cz = CX1 - R.uniform(-1, 1.5), R.uniform(CZ0 + 4, CZ1 - 4)
        elif lado == "n":
            cx, cz = R.uniform(CX0 + 4, CX1 - 4), CZ1 - R.uniform(-1, 1.5)
        else:
            cx, cz = R.choice([R.uniform(CX0 + 4, -16), R.uniform(16, CX1 - 4)]), CZ0 + R.uniform(-1, 1.5)
        q = dict(x=r3(cx), y=r3(y0 + h / 2), z=r3(cz), w=r3(w), h=r3(h), d=r3(d), mat="rocha", ry=R.randint(0, 89))
        if y0 > 0:
            q["semColisao"] = True
        if lado == "n" and abs(cx) - math.hypot(w, d) / 2 < BOCA_DUTO[1] + 1.5 and y0 < BOCA_DUTO[2] + 1.0:
            continue  # não tapa a boca do Duto Norte
        a.d["solidos"].append(q)
    for _ in range(34):
        cx, cz = R.uniform(CX0 + 3, CX1 - 3), R.uniform(CZ0 + 3, CZ1 - 3)
        h = R.uniform(1.5, 5.0)
        s = R.uniform(0.8, 2.4)
        a.d["solidos"].append(dict(x=r3(cx), y=r3(TETO - h / 2 + 0.2), z=r3(cz), w=r3(s), h=r3(h), d=r3(s),
                                   mat="rocha", ry=R.randint(0, 89), semColisao=True))

    # --- colunas do reservatório a cada 12 m (menos onde há buraco ou construção)
    for x, z in colunas_da_caverna():
        pe = (x - 0.6, x + 0.6, z - 0.6, z + 0.6)
        if any(sobrepoe(pe, f, 0.3) for f in FUROS_PISO + CONSTRUCOES + SEM_COLUNAS):
            continue
        B(a, x - 0.6, x + 0.6, 0, TETO, z - 0.6, z + 0.6, "concreto", invisivel=True)
        a.peca("coluna_reservatorio", x, 0.0, z)   # fuste, sapata, anéis, capitel e marca d'água antiga

    # --- Praça do Reservatório: mercado de lonas, bomba d'água, Muro dos Subidores, varais
    lonas = ["lona_vermelha", "lona_azul", "lona_amarela", "lona_verde"]
    bancas = [(-22, -14.5), (-15, -14.5), (-10, -14.5), (-22, -9.5), (-15, -9.5),
              (-22, 6.5), (-14, 6.5), (-22, 11.5), (-14, 11.5), (-10, 11.5)]
    for i, (bx, bz) in enumerate(bancas):
        B(a, bx - 1.3, bx + 1.3, 0, 0.95, bz - 0.5, bz + 0.5, "madeira", invisivel=True)  # balcão
        X(a, bx - 1.7, bx + 1.7, 2.55, 2.65, bz - 1.5, bz + 1.5, lonas[i % 4], rx=R.choice([-7, 7]))
        for k in range(3):                                                                 # mercadoria
            X(a, bx - 1.0 + k * 0.8, bx - 0.6 + k * 0.8, 0.95, 1.25, bz - 0.3, bz + 0.2, R.choice(["caixa", "pano", "lona_amarela"]))
        # banca com postes, balcão de tábuas, lona com franja e mercadoria; a lona cai para o lado da rua
        a.peca("banca_mercado_" + "abcd"[i % 4], bx, 0.0, bz, r=0 if bz < 0 else 180)
    # lonas grandes entre colunas (cobertura do mercado)
    for x0, z0, mat in ((-18, -6, "lona_vermelha"), (-18, 6, "lona_azul"), (6, 6, "lona_amarela")):
        X(a, x0 + 0.6, x0 + 11.4, 4.2, 4.3, z0 - 3, z0 + 3, mat, rz=R.choice([-4, 4]))
        a.peca("lona_mercado_" + {"lona_vermelha": "a", "lona_azul": "b", "lona_amarela": "c"}[mat], x0 + 6.0, 0.0, z0)
    # bomba d'água: tanque, casa da bomba, cano até o teto, cocho
    # (peça bomba_dagua do kit; os blocos ficam só com a colisão)
    B(a, 9.0, 15.0, 0, 1.0, -2.5, 2.5, "concreto", invisivel=True)
    B(a, 9.6, 14.4, 1.0, 3.6, -1.8, 1.8, "ferrugem", invisivel=True)
    B(a, 11.4, 12.6, 3.6, TETO, -0.6, 0.6, "metal", invisivel=True)
    B(a, 15.0, 17.5, 0, 0.7, -0.8, 0.8, "concreto", invisivel=True)
    B(a, 7.0, 8.4, 0, 1.1, -3.0, -1.6, "caixa", invisivel=True)                             # tambores
    B(a, 7.0, 8.4, 0, 1.1, 1.6, 3.0, "caixa", invisivel=True)
    a.peca("bomba_dagua", 12.0, 0.0, 0.0)
    # Muro dos Subidores: muro com placas e fotos, voltado para o sul
    B(a, 4.0, 16.0, 0, 3.4, 15.0, 15.7, "concreto")
    V(a, 3.8, 16.2, 3.4, 3.6, 14.8, 15.9, "ferrugem")
    for i in range(14):
        px = 4.6 + (i % 7) * 1.6
        py = 1.0 + (i // 7) * 1.1
        V(a, px - 0.4, px + 0.4, py, py + 0.7, 14.94, 15.0, R.choice(["pano", "chapa_clara", "madeira"]))
    for px in (5.5, 10.0, 14.5):
        V(a, px - 0.12, px + 0.12, 0, 0.4, 14.5, 14.8, "luz_ambar")                       # velas
    # varais entre colunas
    for (x0, z0), (x1, z1) in (((-18, -18), (-6, -18)), ((6, 6), (18, 6)), ((6, -18), (18, -18)), ((-30, -6), (-18, -6))):
        y = 3.4
        if z0 == z1:
            for i in range(7):
                px = x0 + 1.2 + i * 1.5
                X(a, px - 0.35, px + 0.35, y - 0.9, y, z0 - 0.02, z0 + 0.02, R.choice(lonas + ["pano", "pano"]))
            a.peca("varal_12", (x0 + x1) / 2, 0.0, z0)
    # boca do Duto Norte: pórtico de concreto, lâmpadas de serviço e trilhos desde a praça
    bx0, bx1, by = BOCA_DUTO
    B(a, bx0 - 0.8, bx0, 0, by + 0.8, CZ1 - 0.6, CZ1, "concreto")
    B(a, bx1, bx1 + 0.8, 0, by + 0.8, CZ1 - 0.6, CZ1, "concreto")
    B(a, bx0 - 0.8, bx1 + 0.8, by, by + 0.8, CZ1 - 0.6, CZ1, "concreto")
    V(a, -2.0, 2.0, by + 0.15, by + 0.6, CZ1 - 0.65, CZ1 - 0.6, "ferrugem")      # placa
    for tx in (bx0 - 0.4, bx1 + 0.4):
        V(a, tx - 0.15, tx + 0.15, by - 1.0, by - 0.6, CZ1 - 0.75, CZ1 - 0.6, "luz_ambar")
    for i in range(10):  # faixas de aviso no pórtico
        V(a, bx0 - 0.8, bx0 - 0.75, 0.3 + i * 0.6, 0.6 + i * 0.6, CZ1 - 0.6, CZ1, "lona_amarela" if i % 2 else "escuro")
    for tx in (-1.72, -0.28):
        V(a, tx - 0.04, tx + 0.04, 0.0, 0.08, 20.0, CZ1, "metal")
    # trilho do Portão até a praça
    for tx in (-0.8, 0.8):
        V(a, tx - 0.06, tx + 0.06, 0.0, 0.05, CZ0 - 12, -20.0, "metal")

    # --- Portão da Caravana: boca de túnel na parede sul, fechada por grade alta
    B(a, -10.0, -8.0, 0, 15.5, CZ0 - 0.5, CZ0 + 1.5, "concreto")      # pilares da boca
    B(a, 8.0, 10.0, 0, 15.5, CZ0 - 0.5, CZ0 + 1.5, "concreto")
    B(a, -10.0, 10.0, 14.0, 16.0, CZ0 - 0.5, CZ0 + 1.5, "concreto")   # verga
    V(a, -6.0, 6.0, 14.4, 15.6, CZ0 + 1.5, CZ0 + 1.6, "ferrugem")      # placa
    # túnel atrás da boca
    B(a, -8.5, -8.0, 0, 14.0, CZ0 - 14, CZ0, "concreto")
    B(a, 8.0, 8.5, 0, 14.0, CZ0 - 14, CZ0, "concreto")
    B(a, -8.5, 8.5, 14.0, 15.0, CZ0 - 14, CZ0, "concreto")
    B(a, -8.5, 8.5, -LAJE, 0, CZ0 - 14, CZ0, "chao")
    for i in range(4):  # cambotas do túnel
        z = CZ0 - 2.5 - i * 3
        V(a, -8.0, -7.4, 0, 14.0, z - 0.3, z + 0.3, "metal")
        V(a, 7.4, 8.0, 0, 14.0, z - 0.3, z + 0.3, "metal")
        V(a, -8.0, 8.0, 13.4, 14.0, z - 0.3, z + 0.3, "metal")
    # o portão em si: duas folhas de aço com faixas
    B(a, -8.0, 0.0, 0, 14.0, CZ0 - 13.5, CZ0 - 12.5, "metal")
    B(a, 0.0, 8.0, 0, 14.0, CZ0 - 13.5, CZ0 - 12.5, "metal")
    for y in (2.0, 5.5, 9.0, 12.5):
        V(a, -8.0, 8.0, y, y + 0.5, CZ0 - 12.5, CZ0 - 12.3, "ferrugem")
    # fresta entre as folhas e sob o portão: a luz das cidades profundas vaza do outro lado
    V(a, -0.12, 0.12, 0, 14.0, CZ0 - 12.5, CZ0 - 12.2, "luz_fria")
    V(a, -8.0, 8.0, 0, 0.12, CZ0 - 12.5, CZ0 - 12.2, "luz_fria")
    for tx in (-7.85, 7.85):  # contorno aceso do portão
        V(a, tx - 0.15, tx + 0.15, 0, 14.0, CZ0 - 12.4, CZ0 - 12.2, "luz_ambar")
    V(a, -8.0, 8.0, 13.7, 14.0, CZ0 - 12.4, CZ0 - 12.2, "luz_ambar")
    # grade alta na boca (4,5 m): impede a passagem e deixa ver o portão
    B(a, -8.0, 8.0, 0, 4.5, CZ0 + 0.6, CZ0 + 0.8, "grade", invisivel=True)
    for i in range(33):
        gx = -8.0 + i * 0.5
        V(a, gx - 0.03, gx + 0.03, 0, 4.5, CZ0 + 0.66, CZ0 + 0.74, "grade")
    for y in (0.3, 2.2, 4.4):
        V(a, -8.0, 8.0, y, y + 0.1, CZ0 + 0.62, CZ0 + 0.78, "grade")
    for tx in (-9.0, 9.0):  # lâmpadas de aviso e refletores na boca
        for ty in (4.0, 8.0, 12.0):
            V(a, tx - 0.5, tx + 0.5, ty, ty + 0.6, CZ0 + 1.5, CZ0 + 1.8, "vitral_vermelho" if ty == 12.0 else "luz_ambar")
    V(a, -9.0, 9.0, 13.4, 13.7, CZ0 + 1.5, CZ0 + 1.9, "luz_ambar")             # faixa acesa sob a verga
    for i in range(5):  # lâmpadas dentro do túnel, iluminando o portão
        z = CZ0 - 2.0 - i * 2.4
        V(a, -0.25, 0.25, 12.6, 13.0, z - 0.25, z + 0.25, "luz_ambar")
    V(a, -6.5, 6.5, 6.6, 7.4, CZ0 - 12.45, CZ0 - 12.35, "lona_amarela")       # faixa pintada no portão
    a.luz(0.0, 9.0, CZ0 - 6.0, AMBAR, 1.6, 22)
    for i in range(6):  # barricada de sacos e caixas diante da grade
        B(a, -7 + i * 2.6, -5.6 + i * 2.6, 0, R.uniform(0.6, 1.3), CZ0 + 1.0, CZ0 + 2.2, R.choice(["pano", "caixa"]))

    # --- sede do Conselho (oeste): prédio de 10 m com terraço ligado à passarela norte
    x0, x1, z0, z1 = CONSELHO
    B(a, x0, x1, 0, YP, z0, z1, "concreto")
    V(a, x0 - 0.2, x1 + 0.2, YP - 0.3, YP, z0 - 0.2, z1 + 0.2, "ferrugem")
    for y in (1.6, 4.8, 8.0):  # janelas nas faces leste e sul
        for z in (16.0, 19.0, 27.0, 30.0):
            V(a, x1 - 0.02, x1 + 0.06, y, y + 1.2, z - 0.6, z + 0.6, "janela")
        for x in (-57.0, -53.0, -49.0):
            V(a, x - 0.6, x + 0.6, y, y + 1.2, z0 - 0.06, z0 + 0.02, "janela")
    V(a, x1 - 0.02, x1 + 0.1, 0, 3.0, 22.0, 25.0, "escuro")  # portão do Conselho
    V(a, x1 + 0.1, x1 + 0.3, 3.3, 4.3, 21.5, 25.5, "lona_vermelha")  # faixa
    B(a, -58.0, -50.0, YP, YP + 3.4, 25.0, 31.0, "concreto")  # sala no terraço
    V(a, -50.04, -49.96, YP + 1.0, YP + 2.4, 26.5, 29.5, "janela")
    corrimao(a, "x", z0, x0, x1, YP, lado=0.1)
    corrimao(a, "x", z1, x0, x1, YP, lado=-0.1)
    corrimao(a, "z", x0, z0, z1, YP, lado=0.1)
    corrimao(a, "z", x1, z0, z1, YP, lacunas=[(P2[2], P2[3])], lado=-0.1)

    # --- escadaria da passarela norte (dois lances com patamar), sobe para +x junto à passarela
    ez0, ez1 = 19.0, 22.0
    lance(a, -38.0, -30.0, ez0, ez1, 0.0, 5.0, "+x")
    B(a, -30.0, -28.0, 0, 5.0, ez0, ez1, "concreto")
    lance(a, -28.0, -20.0, ez0, ez1, 5.0, YP, "+x")
    B(a, -20.0, -17.0, 0, YP, ez0, ez1, "concreto")
    for z in (ez0, ez1):  # guarda-corpo: parede invisível alta + corrimão inclinado visível
        dz = -0.05 if z == ez0 else 0.05
        xf = -17.0 if z == ez0 else -20.0  # o patamar de cima abre para a passarela norte
        B(a, -38.0, xf, 0, YP + CORRIMAO, z + dz - 0.05, z + dz + 0.05, "metal", invisivel=True, semCamera=True)
        ang = math.degrees(math.atan2(DEGRAU, PISADA))
        comp = 8.0 / math.cos(math.radians(ang))
        for xc, yc in ((-34.0, 2.5 + CORRIMAO), (-24.0, 7.5 + CORRIMAO)):
            a.d["solidos"].append(dict(x=xc, y=r3(yc), z=r3(z + dz), w=r3(comp), h=0.08, d=0.08, mat="ferrugem", rz=r3(ang), semColisao=True))
        V(a, -30.0, -28.0, 5.0 + CORRIMAO - 0.08, 5.0 + CORRIMAO, z + dz - 0.04, z + dz + 0.04, "ferrugem")
    V(a, -17.0, -16.9, YP, YP + CORRIMAO, ez0, ez1, "metal")
    B(a, -17.0, -16.9, YP, YP + CORRIMAO, ez0, ez1, "metal", invisivel=True, semCamera=True)

    # --- passarela norte a 10 m: Conselho -> Capela, apoiada em vigas entre colunas
    px0, px1, pz0, pz1 = P2
    B(a, px0, px1, YP - ESP, YP, pz0, pz1, "plataforma")
    for x in (-42, -30, -18, -6, 6, 18, 30, 42):
        V(a, x - 0.3, x + 0.3, YP - ESP - 0.6, YP - ESP, 18.0, 30.0, "ferrugem")
    for x in range(-40, 44, 8):  # tirantes até o teto
        for z in (pz0 + 0.1, pz1 - 0.1):
            V(a, x - 0.04, x + 0.04, YP, TETO, z - 0.04, z + 0.04, "metal")
    corrimao(a, "x", pz1, px0, px1, YP, lado=-0.1)
    corrimao(a, "x", pz0, px0, px1, YP, lacunas=[(-20.0, -17.0), (P4[0], P4[1])], lado=0.1)
    for x in (-32, -12, 12, 32):  # lâmpadas penduradas na passarela
        V(a, x - 0.15, x + 0.15, YP + 2.2, YP + 2.5, 23.35, 23.65, "luz_ambar")
        V(a, x - 0.02, x + 0.02, YP + 2.5, TETO, 23.48, 23.52, "escuro")

    # --- ponte sobre a praça a 8 m, com mirante para o Portão
    bx0, bx1 = P4
    for k in range(1, 9):  # degraus da passarela norte (10 m) até a ponte (8 m)
        topo = YP - DEGRAU * k
        B(a, bx0, bx1, topo - ESP, topo, pz0 - PISADA * k, pz0 - PISADA * (k - 1), "plataforma")
    zb1 = pz0 - PISADA * 8
    B(a, bx0, bx1, YP4 - ESP, YP4, -22.0, zb1, "plataforma")
    B(a, -5.0, 5.0, YP4 - ESP, YP4, -27.0, -22.0, "plataforma")          # mirante do Portão
    for z in (-18, -6, 6, 18):  # vigas entre as colunas x = -6 e x = 6
        V(a, -6.0, 6.0, YP4 - ESP - 0.5, YP4 - ESP, z - 0.25, z + 0.25, "ferrugem")
    for z in (-26.6, -22.4, -12.0, 0.0, 12.0):  # tirantes
        for x in (bx0 + 0.1, bx1 - 0.1):
            V(a, x - 0.04, x + 0.04, YP4, TETO, z - 0.04, z + 0.04, "metal")
    corrimao(a, "z", bx0, -22.0, pz0, YP4, lado=0.1)
    corrimao(a, "z", bx1, -22.0, pz0, YP4, lado=-0.1)
    corrimao(a, "x", -27.0, -5.0, 5.0, YP4, lado=0.1)
    corrimao(a, "z", -5.0, -27.0, -22.0, YP4, lado=0.1)
    corrimao(a, "z", 5.0, -27.0, -22.0, YP4, lado=-0.1)
    corrimao(a, "x", -22.0, -5.0, bx0, YP4, lado=-0.1)
    corrimao(a, "x", -22.0, bx1, 5.0, YP4, lado=-0.1)

    # --- Capela: base elevada (casa de máquinas embaixo) e sacada; o interior fica em vila_capela
    cx0, cx1, cz0, cz1 = CAPELA_PISO
    B(a, cx0, cx1, YP - 0.5, YP, cz0, cz1, "concreto")
    for x, z in ((44.6, 10.6), (44.6, 31.4), (63.4, 10.6), (63.4, 31.4), (54.0, 10.6), (54.0, 31.4), (44.6, 21.0), (63.4, 21.0)):
        B(a, x - 0.6, x + 0.6, 0, YP - 0.5, z - 0.6, z + 0.6, "concreto")
    # máquinas antigas sob a Capela
    B(a, 47.0, 53.0, 0, 4.5, 14.0, 19.0, "metal")
    B(a, 48.0, 52.0, 4.5, 6.0, 15.0, 18.0, "ferrugem")
    B(a, 56.0, 61.0, 0, 3.0, 24.0, 29.0, "ferrugem")
    for z in (15.5, 17.5):
        V(a, 53.0, 62.0, 3.6, 4.2, z - 0.3, z + 0.3, "metal")  # canos
    V(a, 57.7, 58.3, 3.0, YP - 0.5, 26.2, 26.8, "metal")
    B(a, 56.0, 60.0, 0, 2.2, 13.0, 16.0, "caixa")
    # sacada a oeste e ao sul
    corrimao(a, "z", cx0, cz0, cz1, YP, lacunas=[(P2[2], P2[3])], lado=0.1)
    corrimao(a, "x", cz0, cx0, cx1, YP, lacunas=[(P3[0], P3[1])], lado=0.1)
    corrimao(a, "x", cz1, cx0, CAPELA[0], YP, lado=-0.1)
    capela_geometria(a)

    # --- passarela leste a 10 m (Capela -> mirante sul a 12 m), com escada de mão desde o piso
    qx0, qx1, qz0, qz1 = P3
    B(a, qx0, qx1, YP - ESP, YP, qz0, qz1, "plataforma")
    for z in (-18, -6, 6):
        V(a, qx0, 54.0, YP - ESP - 0.5, YP - ESP, z - 0.25, z + 0.25, "ferrugem")
    B(a, 50.1, 51.7, 0, YP - ESP, -5.8, -4.2, "concreto")       # pilar da escada de mão
    a.d["escadas"].append(dict(ESCADA_P3))
    corrimao(a, "z", qx0, qz0, qz1, YP, lacunas=[(-5.9, -4.1)], lado=0.1)
    corrimao(a, "z", qx1, qz0, qz1, YP, lado=-0.1)
    lance(a, qx0, qx1, qz0 - 8 * PISADA, qz0, YP, YP + 2.0, "-z", base=YP - ESP)
    mz1 = qz0 - 8 * PISADA
    B(a, 48.0, 56.0, YP + 2.0 - ESP, YP + 2.0, -36.0, mz1, "plataforma")   # mirante a 12 m
    B(a, 50.0, 54.0, 0, YP + 2.0 - ESP, -35.0, -31.0, "concreto")          # torre do mirante
    B(a, qx0 - 0.1, qx0, YP, YP + 2.0 + CORRIMAO, mz1, qz0, "metal", invisivel=True, semCamera=True)
    B(a, qx1, qx1 + 0.1, YP, YP + 2.0 + CORRIMAO, mz1, qz0, "metal", invisivel=True, semCamera=True)
    y12 = YP + 2.0
    corrimao(a, "x", -36.0, 48.0, 56.0, y12, lado=0.1)
    corrimao(a, "z", 48.0, -36.0, mz1, y12, lado=0.1)
    corrimao(a, "z", 56.0, -36.0, mz1, y12, lado=-0.1)
    corrimao(a, "x", mz1, 48.0, qx0, y12, lado=-0.1)
    corrimao(a, "x", mz1, qx1, 56.0, y12, lado=-0.1)

    # --- guarda-corpo dos buracos no piso (acessos às Galerias e boca do poço)
    ax0, ax1, az0, az1 = ESC_A
    corrimao(a, "z", ax0, az0, az1, 0.0, lado=-0.1)
    corrimao(a, "x", az0, ax0, ax1, 0.0, lado=-0.1)
    corrimao(a, "x", az1, ax0, ax1, 0.0, lado=0.1)
    bx0_, bx1_, bz0, bz1 = ESC_B
    corrimao(a, "z", bx0_, bz0, bz1, 0.0, lado=0.1)
    corrimao(a, "x", bz0, bx0_, bx1_, 0.0, lado=-0.1)
    corrimao(a, "x", bz1, bx0_, bx1_, 0.0, lado=0.1)
    for (x0, x1, z0, z1) in (ESC_A, ESC_B):  # pórticos com lâmpada fria sobre as bocas
        xm = x1  # boca da escadaria (lado do piso da caverna)
        V(a, xm - 0.2, xm + 0.2, 0, 3.4, z0 - 0.6, z0 - 0.2, "metal")
        V(a, xm - 0.2, xm + 0.2, 0, 3.4, z1 + 0.2, z1 + 0.6, "metal")
        V(a, xm - 0.2, xm + 0.2, 3.2, 3.6, z0 - 0.6, z1 + 0.6, "metal")
        V(a, xm - 0.1, xm + 0.1, 2.9, 3.2, z0 + 0.4, z1 - 0.4, "luz_fria")
    ox0, ox1, oz0, oz1 = POCO
    corrimao(a, "x", oz1, ox0, ox1, 0.0, lacunas=[(-44.8, -43.2)], lado=0.1)
    corrimao(a, "x", oz0, ox0, ox1, 0.0, lado=-0.1)
    corrimao(a, "z", ox0, oz0, oz1, 0.0, lado=-0.1)
    corrimao(a, "z", ox1, oz0, oz1, 0.0, lado=0.1)
    # guincho sobre o poço
    V(a, ox0, ox1, 7.0, 7.4, -24.2, -23.8, "ferrugem")
    for x in (ox0 - 0.4, ox1 + 0.4):
        V(a, x - 0.2, x + 0.2, 0, 7.4, -24.2, -23.8, "ferrugem")
    V(a, -40.02, -39.98, -12.0, 7.0, -24.02, -23.98, "escuro")

    # --- casas espalhadas pelo piso, fora da praça, das ruas e das construções
    reservados = RUAS + CONSTRUCOES + [(-49.0, -31.0, -33.0, -15.0)]
    colunas = [(x - 0.6, x + 0.6, z - 0.6, z + 0.6) for x, z in colunas_da_caverna()]
    casas = []
    tentativas = 0
    while len(casas) < 58 and tentativas < 4000:
        tentativas += 1
        w, d = R.uniform(3.5, 6.5), R.uniform(3.5, 6.0)
        cx, cz = R.uniform(CX0 + 3, CX1 - 3 - w), R.uniform(CZ0 + 3, CZ1 - 3 - d)
        ret = (cx, cx + w, cz, cz + d)
        if any(sobrepoe(ret, r) for r in reservados) or any(sobrepoe(ret, c, 0.8) for c in colunas):
            continue
        if any(sobrepoe(ret, c, 1.6) for c in casas):
            continue
        casas.append(ret)
        mx, mz = cx + w / 2, cz + d / 2
        frente = ("+x" if mx < 0 else "-x") if abs(mx) / 70 > abs(mz) / 45 else ("+z" if mz < 0 else "-z")
        casa(a, *ret, R.uniform(2.6, 3.4), R.choice(["chapa_azul", "chapa_verde", "concreto", "madeira", "chapa_clara", "ferrugem"]), frente)

    # --- lâmpadas âmbar (luzes reais) e lâmpadas penduradas só visuais
    for lx, ly, lz, alc in ((-14, 6.5, -4, 26), (12, 6.5, 8, 26), (14, 6.5, -14, 24), (-16, 6.5, 14, 22),
                            (0, 11.0, -36, 30), (-30, 6.0, 20.5, 24), (30, 13.0, 23.5, 26), (-45, 5.0, -8, 22),
                            (40, 5.0, -5, 24), (52, 13.5, -20, 22), (-10, 13.0, 23.5, 24), (20, 5.0, 32, 24)):
        a.luz(lx, ly, lz, AMBAR, 1.25, alc)
        V(a, lx - 0.18, lx + 0.18, ly - 0.15, ly + 0.15, lz - 0.18, lz + 0.18, "luz_ambar")
        V(a, lx - 0.02, lx + 0.02, ly + 0.15, TETO, lz - 0.02, lz + 0.02, "escuro")
    for _ in range(40):  # cordões de lâmpadas pela vila
        lx, lz = R.uniform(CX0 + 6, CX1 - 6), R.uniform(CZ0 + 6, CZ1 - 6)
        ly = R.uniform(4.5, 7.5)
        V(a, lx - 0.12, lx + 0.12, ly - 0.12, ly + 0.12, lz - 0.12, lz + 0.12, "luz_ambar")
        V(a, lx - 0.015, lx + 0.015, ly + 0.12, TETO, lz - 0.015, lz + 0.015, "escuro")

    a.entrada("inicio", 0.0, 0.0)
    a.d["entradas"]["inicio"].update(z=-12.0, yaw=0)
    a.d["entradas"]["passarela"] = dict(x=-10.0, y=YP, z=23.5, yaw=90)
    return a


def praca_reservatorio() -> Area:
    """Só a caixa da praça (sobreposta à caverna), para o nome aparecer ao chegar."""
    a = Area("vila_praca", "Praça do Reservatório", "subsolo", "vila", None, -25.0, 25.0)
    a.d["zonaPadrao"] = "vila"
    a.caixa((-25.0, -2.0, -20.0), (25.0, 7.0, 20.0))
    # início do jogo pelo menu (Novo jogo): sul da praça, olhando para o norte (yaw em radianos, como as
    # demais entradas lidas por Jogo.teleportar), com o letreiro da rota sob a ponte e a vila à frente
    a.d["entradas"]["inicio"] = dict(x=INICIO_JOGO[0], y=0.0, z=INICIO_JOGO[1], yaw=INICIO_JOGO[2])
    return a


# ====================================================================== Capela da Vigília

def capela_vigilia() -> Area:
    """Caixa da Capela (sobreposta à caverna): o nome aparece ao entrar pela porta."""
    a = Area("vila_capela", "Capela da Vigília", "subsolo", "capela", None, CAPELA[0], CAPELA[1])
    a.d["zonaPadrao"] = "vila"
    x0, x1, z0, z1 = CAPELA
    a.caixa((x0 - 0.2, YP - 1.0, z0 - 0.2), (x1 + 0.2, YP + 7.0, z1 + 0.2))
    a.entrada("inicio", 50.0, YP)
    a.d["entradas"]["inicio"].update(z=23.5, yaw=90)
    return a


def capela_geometria(a: Area):
    """Casa de máquinas da Capela da Vigília sobre a base a 10 m. Fica na área da caverna, que está
    sempre carregada, para o facho ser visto de quase toda a vila."""
    x0, x1, z0, z1 = CAPELA
    yt = YP + 6.0  # teto da casa de máquinas
    t = 0.4
    porta_o = (P2[2], P2[3])       # porta oeste (passarela norte)
    porta_s = (P3[0], P3[1])       # porta sul (passarela leste)
    hp = YP + 3.0
    # paredes com portas
    B(a, x0, x0 + t, YP, yt, z0, porta_o[0], "chapa_clara")
    B(a, x0, x0 + t, YP, yt, porta_o[1], z1, "chapa_clara")
    B(a, x0, x0 + t, hp, yt, porta_o[0], porta_o[1], "chapa_clara")
    B(a, x0, porta_s[0], YP, yt, z0, z0 + t, "chapa_clara")
    B(a, porta_s[1], x1, YP, yt, z0, z0 + t, "chapa_clara")
    B(a, porta_s[0], porta_s[1], hp, yt, z0, z0 + t, "chapa_clara")
    B(a, x0, x1, YP, yt, z1 - t, z1, "chapa_clara")
    B(a, x1 - t, x1, YP, yt, z0, z1, "chapa_clara")
    a.d.setdefault("kits", [])
    a.d["kits"].append("r2_capela")
    # telhado com claraboia sobre o altar (por onde passa o facho)
    clara = (57.0, 60.0, 20.5, 23.5)
    laje(a, x0 - 0.3, x1 + 0.3, z0 - 0.3, z1 + 0.3, yt, yt + 0.4, [clara], "ferrugem")
    # vitrais nas paredes norte, sul e leste (dos dois lados)
    cores = ["vitral_azul", "vitral_vermelho", "vitral_verde", "vitral_azul", "vitral_vermelho"]
    # vitrais do kit (caixilho de chumbo e vidros de três cores), um em cada face da parede
    for i, x in enumerate((49.0, 52.5, 56.0, 59.5)):
        for zf in (z1 - t - 0.04, z1 + 0.04):
            a.peca("vitral_capela", x, YP + 2.4, zf)
        if not (porta_s[0] - 0.8 < x < porta_s[1] + 0.8):
            for zf in (z0 - 0.04, z0 + t + 0.04):
                a.peca("vitral_capela", x, YP + 2.4, zf)
    for z in (16.0, 28.0):
        for xf in (x1 - t - 0.04, x1 + 0.04):
            a.peca("vitral_capela", xf, YP + 2.4, z, r=90, e=[r3(1.8 / 1.4), r3(2.4 / 2.2), 1])
    # bancos de madeira reaproveitada, com corredor central da porta oeste ao altar
    for x in (49.5, 52.0, 54.5, 57.0):
        for (za, zb) in ((14.0, 19.0), (26.0, 30.5)):
            if za < 20 and porta_s[0] - 0.6 < x < porta_s[1] + 0.6:
                za = 15.5
            B(a, x - 0.3, x + 0.3, YP, YP + 0.45, za, zb, "madeira", invisivel=True)
            a.peca("banco_capela", x, YP, (za + zb) / 2, e=[1, 1, r3((zb - za) / 5.0)])   # tábuas e encosto (kit)
    # altar com fotos do céu
    B(a, 60.6, 62.4, YP, YP + 1.1, 20.2, 23.8, "madeira", invisivel=True)
    a.peca("altar_capela", 61.5, YP, 22.0)                               # toalha, velas e fotos do céu (kit)
    for i, z in enumerate((20.6, 21.6, 22.4, 23.4)):
        V(a, x1 - t - 0.04, x1 - t, YP + 1.6 + (i % 2) * 0.9, YP + 2.3 + (i % 2) * 0.9, z - 0.4, z + 0.4, "vitral_azul")
    V(a, x1 - t - 0.06, x1 - t, YP + 3.4, YP + 4.8, 21.2, 22.8, "luz_dourada")  # sol pintado
    # facho branco-dourado: coluna de luz da claraboia até o teto da caverna e até o altar
    V(a, 57.6, 59.4, YP + 1.18, TETO, 21.1, 22.9, "facho")
    V(a, 57.2, 59.8, yt + 0.4, yt + 0.7, 20.7, 23.3, "luz_dourada")
    a.luz(58.5, yt - 0.3, 22.0, DOURADO, 2.4, 14, tipo="foco")
    a.luz(52.0, YP + 4.5, 22.0, DOURADO, 0.9, 12)
    a.luz(58.5, TETO - 3.0, 22.0, DOURADO, 1.4, 22)


# ====================================================================== Galerias Secas

def galerias_secas() -> Area:
    a = Area("vila_galerias", "Galerias Secas", "subsolo", "galerias", None, -48.0, 39.0)
    a.d["zonaPadrao"] = "vila"
    a.caixa((-48.0, FUNDO - 2.0, -32.0), (39.0, -LAJE, 2.0))
    yt = -LAJE  # teto dos corredores = fundo da laje da caverna
    pw = 0.5    # espessura das paredes

    # --- corredor oeste G1 (de norte a sul até o poço)
    gx0, gx1, gz0, gz1 = G1
    B(a, gx0, gx1, YG - 0.5, YG, gz0, gz1, "chao")
    B(a, gx0 - pw, gx0, YG, yt, gz0, gz1 + pw, "rocha")
    B(a, gx1, gx1 + pw, YG, yt, gz0, G3[2], "rocha")
    B(a, gx1, gx1 + pw, YG, yt, G3[3], ESC_A[2], "rocha")
    B(a, gx0, gx1, YG, yt, gz1, gz1 + pw, "rocha")
    zona_tunel(a, gx0, gx1, YG - 0.5, yt, gz0, gz1)

    # --- escadaria do acesso oeste (desce do piso para -x até o G1)
    ax0, ax1, az0, az1 = ESC_A
    B(a, ax0, ax1, YG - 0.5, YG, az0, az1, "chao")
    lance(a, ax0, ax1, az0, az1, 0.0, YG + DEGRAU, "-x", base=YG)  # 19 degraus de 0,25 até -4,75
    B(a, ax0, ax1, YG, yt, az0 - pw, az0, "rocha")
    B(a, ax0, ax1, YG, yt, az1, az1 + pw, "rocha")
    zona_tunel(a, ax0, ax1 - 2.0, YG - 0.5, 0.0, az0, az1)

    # --- corredor G3 sob a praça e escadaria do acesso leste (sobe para +x)
    hx0, hx1, hz0, hz1 = G3
    B(a, hx0, hx1, YG - 0.5, YG, hz0, hz1, "chao")
    B(a, hx0, ESC_B[1], YG, yt, hz0 - pw, hz0, "rocha")
    B(a, hx0, ESC_B[1], YG, yt, hz1, hz1 + pw, "rocha")
    zona_tunel(a, hx0, hx1, YG - 0.5, yt, hz0, hz1)
    # fiação puxada no teto dos corredores (kit r2_gueto)
    a.d["kits"] = ["r2_gueto"]
    for fx in range(int(hx0) + 3, int(hx1) - 2, 6):
        a.peca("fiacao_6m", fx, yt - 0.05, (hz0 + hz1) / 2 + 0.6)
    for fz in range(int(G1[2]) + 3, int(G1[3]) - 2, 6):
        a.peca("fiacao_6m", (G1[0] + G1[1]) / 2 - 0.4, yt - 0.05, fz, r=90)
    bx0, bx1, bz0, bz1 = ESC_B
    B(a, bx0, bx1, YG - 0.5, YG, bz0, bz1, "chao")
    lance(a, bx0, bx1, bz0, bz1, YG, 0.0, "+x", base=YG)
    zona_tunel(a, bx0, bx1 - 2.0, YG - 0.5, 0.0, bz0, bz1)
    # nichos com barracos ao longo do G3 (alargamentos de 2 m)
    for nx in (-20.0, 4.0):
        B(a, nx, nx + 7.0, YG - 0.5, YG, hz1, hz1 + 2.5, "chao")
        B(a, nx, nx + 7.0, YG, yt, hz1 + 2.5, hz1 + 3.0, "rocha")
        B(a, nx - pw, nx, YG, yt, hz1, hz1 + 3.0, "rocha")
        B(a, nx + 7.0, nx + 7.0 + pw, YG, yt, hz1, hz1 + 3.0, "rocha")
    # recorta a parede norte do G3 nos nichos
    sol = a.d["solidos"]
    parede_n = next(s for s in sol if abs(s["z"] - (hz1 + pw / 2)) < 1e-3 and s["w"] > 50)
    sol.remove(parede_n)
    cortes = [hx0, -20.0, -13.0, 4.0, 11.0, ESC_B[1]]
    for i in range(0, len(cortes) - 1, 2):
        B(a, cortes[i], cortes[i + 1], YG, yt, hz1, hz1 + pw, "rocha")
    for nx in (-20.0, 4.0):
        B(a, nx + 0.4, nx + 3.4, YG, YG + 2.6, hz1 + 0.6, hz1 + 2.5, "chapa_azul")
        V(a, nx + 0.2, nx + 3.6, YG + 2.6, YG + 2.75, hz1 + 0.4, hz1 + 2.6, "ferrugem")
        V(a, nx + 1.0, nx + 1.9, YG, YG + 1.9, hz1 + 0.57, hz1 + 0.6, "escuro")
        V(a, nx + 4.2, nx + 6.6, YG, YG + 1.0, hz1 + 1.2, hz1 + 2.4, "pano")  # colchões
    # fiação, canos e pichações nos corredores
    V(a, hx0, ESC_B[0], yt - 0.35, yt - 0.25, hz0 + 0.2, hz0 + 0.45, "metal")
    V(a, hx0, ESC_B[0], yt - 0.2, yt - 0.17, hz1 - 0.3, hz1 - 0.27, "escuro")
    V(a, gx0 + 0.2, gx0 + 0.45, yt - 0.35, yt - 0.25, gz0, gz1, "metal")
    for i in range(12):
        px = R.uniform(hx0 + 2, ESC_B[0] - 3)
        z = hz0 + 0.02 if i % 2 else hz1 - 0.02
        V(a, px, px + R.uniform(0.8, 2.2), YG + R.uniform(0.6, 1.6), YG + R.uniform(1.8, 2.6), z - 0.02, z + 0.02,
          R.choice(["lona_vermelha", "lona_amarela", "lona_verde", "chapa_azul"]))
    for x in (-24.0, -6.0, 14.0):  # tubos fluorescentes
        V(a, x - 0.6, x + 0.6, yt - 0.12, yt - 0.04, hz0 + 1.6, hz0 + 1.75, "luz_fria")
    V(a, gx0 + 1.6, gx0 + 1.75, yt - 0.12, yt - 0.04, -8.6, -7.4, "luz_fria")

    # --- poço vertical de 20 m (de -5 a -25), aberto para a caverna
    ox0, ox1, oz0, oz1 = POCO
    pz = 1.0
    B(a, ox0 - pz, ox1 + pz, FUNDO - 1.0, yt, oz0 - pz, oz0, "rocha")                  # sul
    B(a, ox0 - pz, ox0, FUNDO - 1.0, yt, oz0, oz1, "rocha")                              # oeste
    B(a, ox1, ox1 + pz, FUNDO - 1.0, yt, oz0, oz1, "rocha")                              # leste
    B(a, ox0 - pz, gx0, FUNDO - 1.0, yt, oz1, oz1 + pz, "rocha")                         # norte, com a
    B(a, gx1, ox1 + pz, FUNDO - 1.0, yt, oz1, oz1 + pz, "rocha")                         # passagem do G1
    B(a, gx0, gx1, FUNDO - 1.0, YG, oz1, oz1 + pz, "rocha")
    # fundo com a grade sobre o poço profundo
    laje(a, ox0, ox1, oz0, oz1, FUNDO - 1.0, FUNDO, [BURACO], "chao")
    kx0, kx1, kz0, kz1 = BURACO
    B(a, kx0, kx1, FUNDO - 0.1, FUNDO, kz0, kz1, "grade", invisivel=True)
    for i in range(13):
        gx = kx0 + i * 0.5
        V(a, gx - 0.04, gx + 0.04, FUNDO - 0.12, FUNDO, kz0, kz1, "grade")
    for i in range(7):
        gz = kz0 + i * 1.0
        V(a, kx0, kx1, FUNDO - 0.15, FUNDO - 0.02, gz - 0.05, gz + 0.05, "grade")
    # poço profundo: paredes escuras e luzes fracas muito abaixo (só visual, inalcançável)
    fundo_prof = FUNDO - 55.0
    V(a, kx0 - 1, kx0, fundo_prof, FUNDO - 1.0, kz0 - 1, kz1 + 1, "rocha")
    V(a, kx1, kx1 + 1, fundo_prof, FUNDO - 1.0, kz0 - 1, kz1 + 1, "rocha")
    V(a, kx0, kx1, fundo_prof, FUNDO - 1.0, kz0 - 1, kz0, "rocha")
    V(a, kx0, kx1, fundo_prof, FUNDO - 1.0, kz1, kz1 + 1, "rocha")
    for _ in range(9):  # lâmpadas de outros moradores, dezenas de metros abaixo
        lx, lz, ly = R.uniform(kx0 + 0.4, kx1 - 0.4), R.uniform(kz0 + 0.4, kz1 - 0.4), FUNDO - R.uniform(15, 52)
        V(a, lx - 0.12, lx + 0.12, ly - 0.12, ly + 0.12, lz - 0.12, lz + 0.12, "luz_fraca")
    a.luz(-40.0, FUNDO - 30.0, -24.0, [1.0, 0.55, 0.25], 0.5, 24)

    # andares: cada um numa parede, como uma espiral; escada de mão encostada num barraco que
    # sustenta o andar de cima e sai em cima dele.
    ESP_A = 0.3
    andares = [
        (YG, (ox0, ox1, oz1 - 4.0, oz1)),               # -5  norte (entrada pelo G1)
        (YG - 5, (ox1 - 4.0, ox1, oz0, oz1)),           # -10 leste
        (YG - 10, (ox0, ox1, oz0, oz0 + 4.0)),          # -15 sul
        (YG - 15, (ox0, ox0 + 4.0, oz0, oz1)),          # -20 oeste
    ]
    for y, (x0, x1, z0, z1) in andares:
        B(a, x0, x1, y - ESP_A, y, z0, z1, "plataforma")
        V(a, x0, x1, y - ESP_A - 0.35, y - ESP_A, (z0 + z1) / 2 - 0.15, (z0 + z1) / 2 + 0.15, "ferrugem")
    # barracos-suporte (no andar de baixo, sob o canto do andar de cima)
    suportes = [
        ((ox1 - 4.0, ox1, oz1 - 4.0, oz1), YG - 5, YG - ESP_A, "chapa_azul"),
        ((ox1 - 4.0, ox1, oz0, oz0 + 4.0), YG - 10, YG - 5 - ESP_A, "chapa_verde"),
        ((ox0, ox0 + 4.0, oz0, oz0 + 4.0), YG - 15, YG - 10 - ESP_A, "ferrugem"),
        ((ox0, ox0 + 4.0, oz1 - 4.0, oz1), FUNDO, YG - 15 - ESP_A, "chapa_clara"),
    ]
    for (x0, x1, z0, z1), y0, y1, mat in suportes:
        B(a, x0, x1, y0, y1, z0, z1, mat)
    # janelas acesas e portas nos barracos-suporte
    V(a, -36.0, -35.2, YG - 8.6, YG - 7.8, oz1 - 4.04, oz1 - 4.0, "janela")
    V(a, -36.4, -36.0, YG - 13.0, YG - 11.4, oz0 + 2.0, oz0 + 3.0, "escuro")
    V(a, -44.0, -43.2, YG - 18.6, YG - 17.8, oz0 + 4.0, oz0 + 4.04, "janela")
    V(a, -43.04, -43.0, FUNDO + 1.0, FUNDO + 1.8, oz1 - 2.8, oz1 - 2.0, "janela")
    # escadas de mão entre os andares (yaw: para onde o jogador olha ao subir)
    escada_mao(a, -35.0, oz1 - 4.05, YG - 5, YG, 0)           # -10 -> -5  (leste -> norte)
    escada_mao(a, ox1 - 4.05, -29.0, YG - 10, YG - 5, 90)     # -15 -> -10 (sul -> leste)
    escada_mao(a, -45.0, oz0 + 4.05, YG - 15, YG - 10, 180)   # -20 -> -15 (oeste -> sul)
    escada_mao(a, ox0 + 4.05, -19.0, FUNDO, YG - 15, 270)     # -25 -> -20 (fundo -> oeste)
    escada_mao(a, -44.0, oz1 - 0.05, YG, 0.0, 0)              # -5 -> 0    (norte -> piso da caverna)
    # guarda-corpos nas bordas internas dos andares, com vão no topo de cada escada
    corrimao(a, "x", oz1 - 4.0, ox0, ox1, YG, lacunas=[(-35.9, -34.1)], lado=0.1)
    corrimao(a, "z", ox1 - 4.0, oz0, oz1 - 4.0, YG - 5, lacunas=[(-29.9, -28.1)], lado=0.1)
    corrimao(a, "x", oz0 + 4.0, ox0, ox1 - 4.0, YG - 10, lacunas=[(-45.9, -44.1)], lado=-0.1)
    corrimao(a, "z", ox0 + 4.0, oz0 + 4.0, oz1, YG - 15, lacunas=[(-19.9, -18.1)], lado=-0.1)
    # barracos de enfeite nos andares (fora dos caminhos)
    B(a, ox0, ox0 + 1.6, YG, YG + 2.5, oz1 - 3.6, oz1 - 1.4, "ferrugem")                # -5, canto oeste
    V(a, ox0 - 0.1, ox0 + 1.8, YG + 2.5, YG + 2.65, oz1 - 3.8, oz1 - 1.2, "chapa_clara")
    B(a, ox1 - 1.2, ox1, YG - 5, YG - 2.6, oz0 + 6.5, oz0 + 9.0, "madeira")              # -10, parede leste
    B(a, -42.0, -39.0, YG - 10, YG - 7.5, oz0, oz0 + 1.6, "chapa_azul")                 # -15, parede sul
    V(a, -41.2, -40.4, YG - 9.0, YG - 8.2, oz0 + 1.6, oz0 + 1.64, "janela")
    B(a, ox0, ox0 + 1.5, YG - 15, YG - 12.5, oz0 + 6.5, oz0 + 9.5, "chapa_verde")       # -20, parede oeste
    B(a, ox1 - 3.0, ox1, FUNDO, FUNDO + 2.4, oz0, oz0 + 2.5, "ferrugem")               # fundo
    V(a, ox1 - 2.0, ox1 - 1.2, FUNDO + 1.0, FUNDO + 1.8, oz0 + 2.5, oz0 + 2.54, "janela")
    # fachadas de barracos de chapa em todas as paredes do poço, andar sobre andar (só visual)
    paredes = [  # (eixo ao longo, posição da face, sentido da normal, início, fim)
        ("x", oz1, -1, ox0, ox1), ("x", oz0, 1, ox0, ox1), ("z", ox0, 1, oz0, oz1), ("z", ox1, -1, oz0, oz1)]
    chapas = ["chapa_azul", "chapa_verde", "ferrugem", "chapa_clara", "madeira"]
    for y in (FUNDO, YG - 15, YG - 10, YG - 5, YG):
        for eixo, face, nrm, ini, fim in paredes:
            u = ini + R.uniform(0.0, 0.6)
            while u < fim - 1.8:
                w = min(R.uniform(2.2, 3.4), fim - u)
                topo = min(y + R.uniform(2.6, 4.2), yt - 0.2)
                livre = not (eixo == "x" and face == oz1 and y == YG and u < gx1 and u + w > gx0)  # boca do G1
                livre = livre and not (eixo == "x" and face == oz1 and y == YG and u < -43.0 and u + w > -45.0)  # escada ao piso
                if livre:
                    f0, f1 = (face, face + 0.25 * nrm) if nrm > 0 else (face - 0.25, face)
                    fr = f1 if nrm > 0 else f0  # face de fora do painel
                    if eixo == "x":
                        V(a, u, u + w, y, topo, min(f0, f1), max(f0, f1), R.choice(chapas))
                        V(a, u + 0.3, u + 1.1, y, y + 1.9, fr - 0.03, fr + 0.03, "escuro")
                        if R.random() < 0.75:
                            V(a, u + 1.5, u + 2.1, y + 1.1, y + 1.7, fr - 0.04, fr + 0.04, "janela")
                        V(a, u - 0.1, u + w + 0.1, topo, topo + 0.12, min(f0, f1) - 0.2 * (nrm < 0), max(f0, f1) + 0.2 * (nrm > 0), "ferrugem")
                    else:
                        V(a, min(f0, f1), max(f0, f1), y, topo, u, u + w, R.choice(chapas))
                        V(a, fr - 0.03, fr + 0.03, y, y + 1.9, u + 0.3, u + 1.1, "escuro")
                        if R.random() < 0.75:
                            V(a, fr - 0.04, fr + 0.04, y + 1.1, y + 1.7, u + 1.5, u + 2.1, "janela")
                        V(a, min(f0, f1) - 0.2 * (nrm < 0), max(f0, f1) + 0.2 * (nrm > 0), topo, topo + 0.12, u - 0.1, u + w + 0.1, "ferrugem")
                u += w + R.uniform(0.1, 0.5)
    # cordões de lâmpadas cruzando o poço em diagonal
    for y in (YG + 2.5, YG - 4.0, YG - 9.5, YG - 14.5, YG - 19.0):
        xa, za, xb, zb = (ox0, oz0, ox1, oz1) if int(y) % 2 else (ox0, oz1, ox1, oz0)
        for i in range(1, 12):
            t = i / 12
            lx, lz = xa + (xb - xa) * t, za + (zb - za) * t
            ly = y - 0.8 * math.sin(math.pi * t)
            V(a, lx - 0.1, lx + 0.1, ly - 0.1, ly + 0.1, lz - 0.1, lz + 0.1, "luz_ambar")
    # varais e fios atravessando o poço
    for y in (YG - 3.0, YG - 9.0, YG - 14.0):
        V(a, ox0, ox1, y, y + 0.03, -23.0 + y * 0.1, -22.97 + y * 0.1, "escuro")
        for i in range(6):
            px = ox0 + 1.5 + i * 2.0
            V(a, px - 0.3, px + 0.3, y - 0.7, y, -23.0 + y * 0.1 - 0.01, -22.97 + y * 0.1 + 0.01, R.choice(["pano", "lona_vermelha", "lona_azul"]))
    # pichações nas paredes do poço
    for y in (YG - 2.0, YG - 12.0, FUNDO + 1.5):
        V(a, ox0 + 0.01, ox0 + 0.04, y, y + 1.2, -26.0, -23.5, R.choice(["lona_amarela", "lona_verde"]))
    # tubos fluorescentes frios (alguns falhando)
    V(a, -36.4, -35.2, YG + 2.6, YG + 2.7, oz1 - 0.3, oz1 - 0.15, "luz_fria")
    V(a, ox1 - 0.3, ox1 - 0.15, YG - 2.4, YG - 2.3, -26.0, -24.8, "luz_fria")
    V(a, -41.0, -39.8, YG - 7.4, YG - 7.3, oz0 + 0.15, oz0 + 0.3, "luz_fria")
    V(a, ox0 + 0.15, ox0 + 0.3, YG - 12.4, YG - 12.3, -24.0, -22.8, "luz_fria")

    # --- luzes: fluorescentes frias, poucas por trecho (limite de uniformes do WebGL2)
    a.luz(-35.75, YG + 3.0, -7.0, FRIA, 0.9, 13, piscar=True)
    a.luz(-14.0, YG + 3.0, -12.0, FRIA, 0.9, 14)
    a.luz(14.0, YG + 3.0, -12.0, FRIA, 0.9, 14, piscar=True)
    a.luz(-40.0, YG - 1.5, -21.0, FRIA, 1.1, 14)
    a.luz(-40.0, YG - 11.0, -26.0, FRIA, 1.0, 14, piscar=True)
    a.luz(-40.0, FUNDO + 3.0, -22.0, FRIA, 0.9, 12)

    a.entrada("inicio", -35.75, YG)
    a.d["entradas"]["inicio"].update(z=-5.0, yaw=180)
    a.d["entradas"]["fundo_poco"] = dict(x=-40.0, y=FUNDO, z=-19.0, yaw=180)
    return a


def todas():
    from sinalizacao import sinalizar
    return sinalizar([caverna(), praca_reservatorio(), capela_vigilia(), galerias_secas()])


if __name__ == "__main__":
    for area in todas():
        area.salvar()
