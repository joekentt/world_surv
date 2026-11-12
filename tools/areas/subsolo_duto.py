"""Duto Norte, Caverna da Fenda e Galeria dos Contrabandistas, em blocos (revisão 2, fase 2, tarefa 3).

Uso: python3 tools/areas/subsolo_duto.py   (grava content/areas/duto_*.json)

Seção 5.1 de docs/spec/05-mapa.md e seção 7 de docs/spec/07-arte-personagens-vila.md.
Mundo "subsolo", mesmos eixos da vila (Y para cima, norte em +Z, piso da vila em y = 0).

Traçado (300 m pelo eixo):
  - trecho norte: sai da parede norte da caverna da vila (z = 45, boca de x = -4 a 4) e segue para o
    norte até z = 209, descendo por duas rampas (0 -> -5 m e -5 -> -10 m);
  - curva para leste em (0, 205) e trecho leste até x = 140, descendo de -10 a -25 m por duas rampas;
  - no fim (x = 140, y = -25) a parede com o portão aberto para a Estação Aurora (tarefa 4, em
    tools/areas/subsolo_estacao.py, que grava estacao_aurora.json e boca_estacao.json).
Desvios:
  - Caverna da Fenda (leste do trecho norte, x 14..70, z 92..168): duas passagens a partir do duto
    (z = 103 e z = 155, y = -5) formam um circuito; abismo de 40 m (z 118..140) atravessado por uma
    ponte de corda em x = 40; mirante a 4 m sobre a borda norte;
  - Galeria dos Contrabandistas: passagem de 2,8 m que sai da curva para o norte até a base da
    Escotilha Oeste (escada de mão em (0, 319,45), de -7 a 1 m, até um alçapão fechado).
Correspondência com a superfície (seção 5.2): a Boca do Poço fica em (178, 205) do subsolo, dentro da
Estação Aurora; superfície = (x - 178, z - 205). A base da escada da Escotilha Oeste, (0, 319,1), cai em
(-178, 114,1), contra (-178, 115) da especificação.
Valores de src/config.ts: degraus de 0,25 a 0,30 m, rampas de 7 a 18 graus, corredores de 2,5 m ou mais.
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_areas import AMBAR, FRIA, MUSGO, Area, rad  # noqa: E402
from subsolo_vila import CORRIMAO, B, V, corrimao, r3, zona_tunel  # noqa: E402

R = random.Random(303)
VERMELHO = [1.0, 0.3, 0.15]

# ---------------------------------------------------------------- duto
ALT = 5.5            # altura livre do túnel
ESP_PISO = 0.5
ESP_TETO = 0.6
PW = 1.0             # espessura das paredes
NX0, NX1 = -4.0, 4.0          # interior do trecho norte
EZ0, EZ1 = 201.0, 209.0       # interior do trecho leste
Z_BOCA = 45.0                 # parede norte da caverna da vila
Z_NORTE = 209.0               # fim do trecho norte (parede norte da curva)
X_FIM = 140.0                 # parede do fim do duto, com o portão aberto para a Estação Aurora
PORTAO_FIM = (202.6, 207.4)   # vão do portão (z)
XT = -1.0                     # eixo do trilho no trecho norte
ZT = 204.0                    # eixo do trilho no trecho leste
BITOLA = 0.72                 # meia bitola
# perfil do piso: (coordenada ao longo do trecho, altura)
PERFIL_N = [(Z_BOCA, 0.0), (58.0, 0.0), (98.0, -5.0), (160.0, -5.0), (195.0, -10.0), (Z_NORTE, -10.0)]
PERFIL_E = [(NX1, -10.0), (30.0, -10.0), (90.0, -20.0), (118.0, -20.0), (133.0, -25.0), (X_FIM + 1.0, -25.0)]
# passagens para a Fenda na parede leste do trecho norte (z0, z1), piso a -5
PASSAGEM_A = (101.5, 104.5)
PASSAGEM_B = (153.5, 156.5)
ALT_PASSAGEM = 3.0
# plataforma de manutenção e destroços
PLAT_N = (1.5, NX1, 110.0, 144.0)      # x0, x1, z0, z1 (topo a +0,9 m do piso)
ENTULHO_N = (NX0, 1.5, 116.0, 132.0)   # desabamento que fecha o leito do trilho
VAGONETE = (-1.2, NX1, 172.5, 178.5)   # vagonete descarrilado na rampa
VAGAO = (97.0, 113.0, EZ0, 206.2)      # vagão tombado no trecho leste (sobra a faixa z 206,2..209)
PLAT_E = (8.0, 28.0, 206.5, EZ1)       # plataforma de manutenção do trecho leste
ESTACAO = (141.0, 200.0, 195.0, 215.0)
BOCA_DO_POCO = (178.0, 205.0)

# ---------------------------------------------------------------- Fenda
FX0, FX1, FZ0, FZ1 = 14.0, 70.0, 92.0, 168.0   # salão
YF = -5.0                                      # piso das bordas
TETO_F = 22.0
AZ0, AZ1 = 118.0, 140.0                        # abismo
FUNDO_F = YF - 40.0                            # fundo do abismo (-45)
PONTE_X = 40.0
PONTE_L = 0.9                                  # meia largura do tabuleiro
FLECHA = 0.7                                   # flecha da ponte no meio
MIRANTE = (54.0, 66.0, 134.0, 146.0)           # plataforma a YF + 4
Y_MIRANTE = YF + 4.0
Y_SOLIDO = -26.0   # base dos sólidos com colisão (o resto, abaixo, é só visual: o piso mínimo não desce)

# ---------------------------------------------------------------- Galeria
GL = 1.4                                       # meia largura (2,8 m)
Z_ESCADA = 319.45
Y_ALCAPAO = 3.6


def C(a: Area, cx, cy, cz, w, h, d, mat, **k):
    """Caixa pelo centro, com rotações opcionais (rx, ry, rz em graus)."""
    q = dict(x=r3(cx), y=r3(cy), z=r3(cz), w=r3(w), h=r3(h), d=r3(d), mat=mat)
    for eixo in ("rx", "ry", "rz"):
        v = k.pop(eixo, 0)
        if abs(v) > 1e-3:
            q[eixo] = r3(v)
    q.update(k)
    a.d["solidos"].append(q)


def interp(perfil, s):
    if s <= perfil[0][0]:
        return perfil[0][1]
    for (s0, y0), (s1, y1) in zip(perfil, perfil[1:]):
        if s <= s1:
            return y0 + (y1 - y0) * (s - s0) / (s1 - s0)
    return perfil[-1][1]


def inclinacao(perfil, s):
    """Ângulo (graus) do trecho do perfil em s; positivo quando desce no sentido crescente."""
    for (s0, y0), (s1, y1) in zip(perfil, perfil[1:]):
        if s0 <= s <= s1:
            return math.degrees(math.atan2(y0 - y1, s1 - s0))
    return 0.0


def faixa_z(a, x0, x1, z0, z1, y0, y1, esp, mat, teto=False, **k):
    """Laje cuja face de cima (piso) ou de baixo (teto) vai de (z0, y0) a (z1, y1)."""
    dz, dy = z1 - z0, y1 - y0
    ang = math.atan2(-dy, dz)
    comp = math.hypot(dz, dy) + (0.4 if abs(dy) > 1e-6 else 0.0)
    c, s = math.cos(ang), math.sin(ang)
    sinal = 1 if teto else -1
    C(a, (x0 + x1) / 2, (y0 + y1) / 2 + sinal * c * esp / 2, (z0 + z1) / 2 + sinal * s * esp / 2,
      x1 - x0, esp, comp, mat, rx=math.degrees(ang), **k)


def faixa_x(a, x0, x1, z0, z1, y0, y1, esp, mat, teto=False, **k):
    """Como faixa_z, ao longo de x."""
    dx, dy = x1 - x0, y1 - y0
    ang = math.atan2(dy, dx)
    comp = math.hypot(dx, dy) + (0.4 if abs(dy) > 1e-6 else 0.0)
    c, s = math.cos(ang), math.sin(ang)
    sinal = 1 if teto else -1
    C(a, (x0 + x1) / 2 + sinal * (-s) * esp / 2, (y0 + y1) / 2 + sinal * c * esp / 2, (z0 + z1) / 2,
      comp, esp, z1 - z0, mat, rz=math.degrees(ang), **k)


def parede_ao_longo(a, eixo, f0, f1, ini, fim, perfil, furos=(), mat="concreto_escuro"):
    """Parede vertical que acompanha o perfil do piso. eixo 'z': parede em x de f0 a f1, de z = ini a fim;
    eixo 'x': parede em z de f0 a f1. furos: (s0, s1, y_topo) abertos do piso até y_topo."""
    cortes = {ini, fim}
    cortes |= {s for s, _ in perfil if ini < s < fim}
    for s0, s1, _ in furos:
        cortes |= {s for s in (s0, s1) if ini < s < fim}
    cortes = sorted(cortes)
    for s0, s1 in zip(cortes, cortes[1:]):
        ya, yb = interp(perfil, s0), interp(perfil, s1)
        lo, hi = min(ya, yb) - ESP_PISO - 0.1, max(ya, yb) + ALT + ESP_TETO
        meio = (s0 + s1) / 2
        furo = next((f for f in furos if f[0] <= meio <= f[1]), None)
        if furo:
            lo = furo[2]
        if eixo == "z":
            B(a, f0, f1, lo, hi, s0, s1, mat)
        else:
            B(a, s0, s1, lo, hi, f0, f1, mat)


def degraus(a, x0, x1, z0, z1, y0, y1, sentido, mat="concreto", pisada=0.4, base=None):
    """Lance que sobe de y0 a y1 no sentido indicado ('+x', '-x', '+z', '-z'), degraus de até 0,30 m.
    O degrau mais alto encosta na borda de chegada (x1 em '+x', x0 em '-x', z1 em '+z', z0 em '-z')."""
    n = max(1, math.ceil(abs(y1 - y0) / 0.3 - 1e-6))
    h = (y1 - y0) / n
    base = y0 - 0.3 if base is None else base
    for i in range(n):
        topo = y0 + h * (i + 1)
        k = n - 1 - i  # distância (em degraus) até a borda de chegada
        if sentido == "+x":
            B(a, x1 - pisada * (k + 1), x1 - pisada * k, base, topo, z0, z1, mat)
        elif sentido == "-x":
            B(a, x0 + pisada * k, x0 + pisada * (k + 1), base, topo, z0, z1, mat)
        elif sentido == "+z":
            B(a, x0, x1, base, topo, z1 - pisada * (k + 1), z1 - pisada * k, mat)
        else:
            B(a, x0, x1, base, topo, z0 + pisada * k, z0 + pisada * (k + 1), mat)
    return n * pisada


def mancha(a, plano, eixo, normal, s, y, mat="musgo", tam=1.0):
    """Mancha (musgo, umidade) rente a uma face: eixo 'x' = face em x = plano; 'z' = face em z = plano.
    normal = +1/-1 para que lado a face olha. Um núcleo e alguns pingos em volta."""
    for i in range(R.randint(2, 4)):
        w = R.uniform(0.25, 0.9) * tam * (1.0 if i == 0 else 0.5)
        h = R.uniform(0.15, 0.6) * tam * (1.0 if i == 0 else 0.5)
        ds = 0 if i == 0 else R.uniform(-0.9, 0.9) * tam
        dy = 0 if i == 0 else R.uniform(-0.5, 0.5) * tam
        e = 0.03 + 0.02 * i
        p0, p1 = (plano, plano + e) if normal > 0 else (plano - e, plano)
        if eixo == "x":
            V(a, p0, p1, y + dy - h / 2, y + dy + h / 2, s + ds - w / 2, s + ds + w / 2, mat)
        else:
            V(a, s + ds - w / 2, s + ds + w / 2, y + dy - h / 2, y + dy + h / 2, p0, p1, mat)


def rocha(a, cx, cy, cz, w, h, d, colisao=True, mat="rocha"):
    k = {} if colisao else {"semColisao": True}
    C(a, cx, cy, cz, w, h, d, mat, ry=R.randint(0, 89), rx=R.uniform(-8, 8), rz=R.uniform(-8, 8), **k)


# ====================================================================== Duto Norte

def duto_tunel() -> Area:
    a = Area("duto_tunel", "Duto Norte", "subsolo", "duto", None, NX0 - PW, X_FIM + PW)
    a.d["zonaPadrao"] = "tunel"
    a.d["kits"] = ["r2_tunel"]
    a.caixa((NX0 - PW, -27.0, Z_BOCA), (X_FIM + PW, 7.0, Z_NORTE + PW))
    zona_tunel(a, NX0, NX1, -11.0, 6.5, Z_BOCA - 1.0, Z_NORTE)
    zona_tunel(a, NX1, X_FIM, -26.0, -3.5, EZ0, EZ1)

    # --- trecho norte: piso, teto e paredes
    for (z0, y0), (z1, y1) in zip(PERFIL_N, PERFIL_N[1:]):
        faixa_z(a, NX0 - PW, NX1 + PW, z0, z1, y0, y1, ESP_PISO, "chao")
        faixa_z(a, NX0 - PW, NX1 + PW, z0, z1, y0 + ALT, y1 + ALT, ESP_TETO, "concreto_escuro", teto=True)
    parede_ao_longo(a, "z", NX0 - PW, NX0, Z_BOCA, Z_NORTE + PW, PERFIL_N)
    parede_ao_longo(a, "z", NX1, NX1 + PW, Z_BOCA, EZ0, PERFIL_N,
                    furos=[(PASSAGEM_A[0], PASSAGEM_A[1], YF + ALT_PASSAGEM), (PASSAGEM_B[0], PASSAGEM_B[1], YF + ALT_PASSAGEM)])
    # --- trecho leste
    for (x0, y0), (x1, y1) in zip(PERFIL_E, PERFIL_E[1:]):
        faixa_x(a, x0, x1, EZ0 - PW, EZ1 + PW, y0, y1, ESP_PISO, "chao")
        faixa_x(a, x0, x1, EZ0 - PW, EZ1 + PW, y0 + ALT, y1 + ALT, ESP_TETO, "concreto_escuro", teto=True)
    parede_ao_longo(a, "x", EZ0 - PW, EZ0, NX1, X_FIM + PW, PERFIL_E)
    # parede norte da curva e do trecho leste, com a boca da Galeria dos Contrabandistas
    B(a, NX0 - PW, -GL, -10.6, -10.0 + ALT + ESP_TETO, EZ1, EZ1 + PW, "concreto_escuro")
    B(a, -GL, GL, -7.2, -10.0 + ALT + ESP_TETO, EZ1, EZ1 + PW, "concreto_escuro")
    B(a, GL, NX1, -10.6, -10.0 + ALT + ESP_TETO, EZ1, EZ1 + PW, "concreto_escuro")
    parede_ao_longo(a, "x", EZ1, EZ1 + PW, NX1, X_FIM + PW, PERFIL_E)

    trilhos(a)
    cambotas_e_detalhes(a)
    destrocos(a)
    fim_do_duto(a)
    agua_e_musgo(a)

    # --- luzes reais: lâmpadas de serviço, poucas e fracas (o resto é lanterna e emissivos)
    for lx, lz, cor, i, alc, pisca in ((XT, 62.0, FRIA, 0.7, 14, False), (2.75, 112.0, AMBAR, 0.8, 14, True),
                                       (XT, 140.0, FRIA, 0.55, 12, False), (-2.5, 176.0, AMBAR, 0.7, 12, True),
                                       (0.0, 205.0, FRIA, 0.7, 14, False)):
        a.luz(lx, r3(interp(PERFIL_N, lz) + 4.6), lz, cor, i, alc, **({"piscar": True} if pisca else {}))
    for lx, lz, cor, i, alc, pisca in ((45.0, 205.0, FRIA, 0.6, 14, False), (105.0, 207.6, AMBAR, 0.8, 14, True),
                                       (136.0, 205.0, VERMELHO, 0.8, 12, False)):
        a.luz(lx, r3(interp(PERFIL_E, lx) + 4.6), lz, cor, i, alc, **({"piscar": True} if pisca else {}))

    a.entrada("inicio", XT, 0.0)
    a.d["entradas"]["inicio"].update(z=50.0, yaw=rad(0))
    a.d["entradas"]["curva"] = dict(x=0.0, y=-10.0, z=205.0, yaw=rad(90))
    a.d["entradas"]["fim"] = dict(x=137.0, y=-25.0, z=205.0, yaw=rad(90))
    return a


def vias(a: Area, perfil, s_ini, s_fim, eixo):
    """Trechos de via de 6 m do kit r2_tunel (lastro, dormentes e trilhos) num trecho reto do perfil, inclinados
    com a rampa; o último encosta no fim do trecho (pequena sobreposição)."""
    for (s0, y0), (s1, y1) in zip(perfil, perfil[1:]):
        a0, a1 = max(s0, s_ini), min(s1, s_fim)
        if a1 - a0 < 0.5:
            continue
        ya, yb = interp(perfil, a0), interp(perfil, a1)
        comp = math.hypot(a1 - a0, yb - ya)
        n = max(1, math.ceil(comp / 6.0))
        inc = inclinacao(perfil, (a0 + a1) / 2)
        for i in range(n):
            t = (i + 0.5) / n
            sc = a0 + (a1 - a0) * t
            if eixo == "z":
                a.d["pecas"].append(dict(m="via_6m", x=XT, y=r3(interp(perfil, sc)), z=r3(sc), rx=r3(inc)))
            else:
                a.d["pecas"].append(dict(m="via_6m", x=r3(sc), y=r3(interp(perfil, sc)), z=ZT, r=90, rx=r3(inc)))


def trilhos(a: Area):
    """Lastro, dormentes e trilhos, acompanhando as rampas; curva de raio 8 m ligando os dois trechos.
    Nos trechos retos, a via é a peça via_6m do kit r2_tunel; na curva, blocos."""
    z_curva = 196.0
    # trecho norte
    vias(a, PERFIL_N, Z_BOCA, z_curva, "z")
    # curva (centro em (XT + 8, 196), de 180 a 90 graus)
    raio, cx, cz = 8.0, XT + 8.0, z_curva
    n = 10
    for i in range(n):
        t0 = math.pi - (math.pi / 2) * i / n
        t1 = math.pi - (math.pi / 2) * (i + 1) / n
        for rr in (raio - BITOLA, raio + BITOLA, raio):
            xa, za = cx + rr * math.cos(t0), cz + rr * math.sin(t0)
            xb, zb = cx + rr * math.cos(t1), cz + rr * math.sin(t1)
            ry = math.degrees(math.atan2(xb - xa, zb - za))
            comp = math.hypot(xb - xa, zb - za) + 0.05
            if rr == raio:
                C(a, (xa + xb) / 2, -10.0 + 0.01, (za + zb) / 2, 2.8, 0.06, comp, "rocha", ry=ry, semColisao=True)
            else:
                C(a, (xa + xb) / 2, -10.0 + 0.24, (za + zb) / 2, 0.08, 0.12, comp, "metal", ry=ry, semColisao=True)
        for k in range(2):
            t = t0 + (t1 - t0) * (0.25 + 0.5 * k)
            ry = math.degrees(math.atan2(-math.sin(t), math.cos(t)))  # tangente
            C(a, cx + raio * math.cos(t), -10.0 + 0.07, cz + raio * math.sin(t), 2.4, 0.1, 0.24, "madeira_escura", ry=ry, semColisao=True)
    # trecho leste
    x_ini = XT + raio
    vias(a, PERFIL_E, x_ini, X_FIM - 0.5, "x")


def cambotas_e_detalhes(a: Area):
    """Cambotas metálicas a cada 5 m, cabos, canos, luminárias apagadas e nichos de refúgio."""
    furos_leste = [PASSAGEM_A, PASSAGEM_B]
    z = Z_BOCA + 2.5
    k = 0
    while z < Z_NORTE - 1.0:
        y = interp(PERFIL_N, z)
        if z < EZ0 - 0.5:
            if not any(f0 - 0.6 < z < f1 + 0.6 for f0, f1 in furos_leste):
                a.peca("cambota", 0.0, y, z)
            else:
                V(a, NX0, NX0 + 0.22, y, y + ALT, z - 0.15, z + 0.15, "metal")
                V(a, NX0, NX1, y + ALT - 0.25, y + ALT, z - 0.15, z + 0.15, "metal")
        # luminárias no teto (quase todas apagadas)
        if k % 2 == 0:
            acesa = k % 6 == 0
            V(a, -0.6, 0.6, y + ALT - 0.4, y + ALT - 0.28, z + 2.5 - 0.15, z + 2.5 + 0.15, "luz_fria" if acesa else "escuro")
        # nichos de refúgio na parede oeste, com lâmpada vermelha de sinalização
        if k % 5 == 2:
            V(a, NX0, NX0 + 0.03, y, y + 2.1, z + 1.0, z + 2.4, "escuro")
            V(a, NX0, NX0 + 0.06, y + 2.3, y + 2.5, z + 1.6, z + 1.8, "vitral_vermelho")
            V(a, NX0, NX0 + 0.04, y + 0.8, y + 1.0, z + 1.0, z + 2.4, "lona_amarela")
        z += 5.0
        k += 1
    x = NX1 + 3.0
    k = 0
    while x < X_FIM - 1.0:
        y = interp(PERFIL_E, x)
        a.peca("cambota", x, y, (EZ0 + EZ1) / 2, r=90)
        if k % 2 == 0:
            acesa = k % 6 == 3
            V(a, x + 2.5 - 0.15, x + 2.5 + 0.15, y + ALT - 0.4, y + ALT - 0.28, ZT + 0.4, ZT + 1.6, "luz_fria" if acesa else "escuro")
        if k % 5 == 1:
            V(a, x + 1.0, x + 2.4, y, y + 2.1, EZ0, EZ0 + 0.03, "escuro")
            V(a, x + 1.6, x + 1.8, y + 2.3, y + 2.5, EZ0, EZ0 + 0.06, "vitral_vermelho")
            V(a, x + 1.0, x + 2.4, y + 0.8, y + 1.0, EZ0, EZ0 + 0.04, "lona_amarela")
        x += 5.0
        k += 1
    # cabos na parede oeste / sul e cano na parede leste / norte, acompanhando as rampas
    for (z0, y0), (z1, y1) in zip(PERFIL_N, PERFIL_N[1:]):
        n = max(1, math.ceil(math.hypot(z1 - z0, y1 - y0) / 6.0))
        for i in range(n):
            zc = z0 + (z1 - z0) * (i + 0.5) / n
            a.d["pecas"].append(dict(m="cabos_6m", x=NX0 + 0.22, y=r3(interp(PERFIL_N, zc) + 0.6), z=r3(zc),
                                     rx=r3(inclinacao(PERFIL_N, zc))))
        z1c = min(z1, EZ0)
        if z1c > z0:
            y1c = interp(PERFIL_N, z1c)
            faixa_z(a, NX1 - 0.5, NX1 - 0.25, z0, z1c, y0 + 4.6, y1c + 4.6, 0.25, "ferrugem", semColisao=True)
    for (x0, y0), (x1, y1) in zip(PERFIL_E, PERFIL_E[1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / 6.0))
        for i in range(n):
            xc = x0 + (x1 - x0) * (i + 0.5) / n
            a.d["pecas"].append(dict(m="cabos_6m", x=r3(xc), y=r3(interp(PERFIL_E, xc) + 0.6), z=EZ0 + 0.22, r=-90,
                                     rx=r3(-inclinacao(PERFIL_E, xc))))
        faixa_x(a, x0, x1, EZ1 - 0.5, EZ1 - 0.25, y0 + 4.6, y1 + 4.6, 0.25, "ferrugem", semColisao=True)
    # caixas elétricas e placas de quilometragem
    for z in (66.0, 121.0, 149.0, 186.0):
        y = interp(PERFIL_N, z)
        V(a, NX0, NX0 + 0.35, y + 1.2, y + 2.3, z - 0.5, z + 0.5, "metal")
        V(a, NX0 + 0.35, NX0 + 0.38, y + 1.9, y + 2.1, z - 0.3, z + 0.3, "ferrugem")
    for x in (40.0, 70.0, 124.0):
        y = interp(PERFIL_E, x)
        V(a, x - 0.5, x + 0.5, y + 1.2, y + 2.3, EZ0, EZ0 + 0.35, "metal")
    # pórticos nas bocas das passagens da Fenda (vigas de madeira e uma marca pintada)
    for f0, f1 in (PASSAGEM_A, PASSAGEM_B):
        V(a, NX1 - 0.25, NX1 + 0.05, YF, YF + ALT_PASSAGEM, f0 - 0.25, f0, "madeira")
        V(a, NX1 - 0.25, NX1 + 0.05, YF, YF + ALT_PASSAGEM, f1, f1 + 0.25, "madeira")
        V(a, NX1 - 0.25, NX1 + 0.05, YF + ALT_PASSAGEM - 0.25, YF + ALT_PASSAGEM, f0 - 0.25, f1 + 0.25, "madeira")
        V(a, NX1 - 0.02, NX1, YF + 1.4, YF + 1.9, f0 - 0.9, f0 - 0.4, "musgo")


def destrocos(a: Area):
    """Desabamento (desvio pela plataforma), vagonete descarrilado e vagão tombado."""
    # --- plataforma de manutenção do trecho norte (+0,9 m), com degraus nas pontas
    px0, px1, pz0, pz1 = PLAT_N
    yp = YF + 0.9
    B(a, px0, px1, YF - 0.3, yp, pz0, pz1, "concreto_escuro")
    V(a, px0 - 0.02, px0 + 0.15, yp - 0.02, yp + 0.01, pz0, pz1, "lona_amarela")
    degraus(a, px0, px1, pz0 - 1.2, pz0, YF, yp, "+z", mat="concreto_escuro")
    degraus(a, px0, px1, pz1, pz1 + 1.2, YF, yp, "-z", mat="concreto_escuro")
    for z in (pz0 + 6.0, pz0 + 20.0):  # armários de ferramentas encostados na parede (sem invadir a faixa)
        V(a, NX1 - 0.3, NX1, yp, yp + 1.8, z, z + 0.9, "chapa_verde")

    # --- desabamento: núcleo com colisão invisível (2,8 m, alto demais para pular) coberto por blocos
    # soltos girados, mais altos no meio do monte
    ex0, ex1, ez0, ez1 = ENTULHO_N
    B(a, ex0, ex1, YF - 0.3, YF + 2.8, ez0 + 1.0, ez1 - 1.0, "rocha_escura", invisivel=True)
    B(a, ex0, ex1 - 1.0, YF - 0.3, YF + 1.6, ez0, ez1, "rocha_escura", invisivel=True)
    V(a, ex0, ex1 - 0.3, YF, YF + 1.2, ez0 + 0.6, ez1 - 0.6, "rocha_escura")
    cxm, czm = (ex0 + ex1) / 2 - 0.5, (ez0 + ez1) / 2
    for _ in range(70):
        cx = R.uniform(ex0 + 0.2, ex1 - 0.2)
        cz = R.uniform(ez0 + 0.2, ez1 - 0.2)
        k = min(1.0, ((cx - cxm) / ((ex1 - ex0) / 2 + 0.6)) ** 2 + ((cz - czm) / ((ez1 - ez0) / 2 + 0.6)) ** 2)
        topo = YF + 0.5 + 3.0 * (1 - k)
        tam = R.uniform(0.6, 2.0)
        rocha(a, cx, topo - tam * 0.45, cz, tam * R.uniform(0.8, 1.6), tam, tam * R.uniform(0.8, 1.6), colisao=False,
              mat=R.choice(["rocha_escura", "rocha_escura", "concreto_escuro", "rocha"]))
    for _ in range(5):  # vergalhões retorcidos saindo do monte
        C(a, R.uniform(ex0 + 1, ex1 - 1), YF + R.uniform(2.0, 3.2), R.uniform(ez0 + 3, ez1 - 3), 0.05, R.uniform(1.2, 2.4), 0.05,
          "ferrugem", rx=R.uniform(-40, 40), rz=R.uniform(-40, 40), semColisao=True)
    # laje do teto caída, inclinada sobre o monte, e o buraco escuro no teto
    C(a, -1.2, YF + 3.2, 124.0, 5.0, 0.4, 6.0, "concreto_escuro", rx=24, rz=-9, semColisao=True)
    V(a, ex0 + 0.4, ex1 - 0.6, YF + ALT - 0.02, YF + ALT + 0.01, ez0 + 3.0, ez1 - 4.0, "escuro")
    for _ in range(6):  # pedras espalhadas no leito, antes e depois do monte
        z = R.choice([R.uniform(111.0, 115.5), R.uniform(132.5, 137.0)])
        rocha(a, R.uniform(NX0 + 0.4, 0.8), YF + 0.15, z, R.uniform(0.3, 0.7), 0.3, R.uniform(0.3, 0.7), colisao=False)
    # cavaletes de aviso
    for z in (113.0, 135.0):
        V(a, -2.6, 0.6, YF + 0.9, YF + 1.15, z - 0.05, z + 0.05, "lona_amarela")
        for x in (-2.4, 0.4):
            V(a, x - 0.05, x + 0.05, YF, YF + 1.0, z - 0.05, z + 0.05, "metal")

    # --- vagonete descarrilado na rampa (sobra a faixa oeste de 2,8 m)
    vx0, vx1, vz0, vz1 = VAGONETE
    yb, yt = interp(PERFIL_N, vz1) - 0.3, interp(PERFIL_N, vz0) + 1.3
    B(a, vx0, vx1, yb, yt, vz0, vz1, "ferrugem")
    ym = interp(PERFIL_N, (vz0 + vz1) / 2)
    C(a, (vx0 + vx1) / 2, ym + 1.8, (vz0 + vz1) / 2, vx1 - vx0 - 0.4, 0.15, vz1 - vz0 - 0.3, "metal", ry=6, semColisao=True)
    for x, z in ((vx0 + 0.6, vz0 + 1.0), (vx1 - 0.6, vz0 + 1.2), (vx0 + 0.6, vz1 - 1.0), (vx1 - 0.6, vz1 - 1.2)):
        V(a, x - 0.35, x + 0.35, interp(PERFIL_N, z), interp(PERFIL_N, z) + 0.7, z - 0.35, z + 0.35, "escuro")
    for i in range(4):  # carga de caixas e um tambor caído
        cx = vx0 + 0.8 + i * 1.1
        V(a, cx - 0.45, cx + 0.45, ym + 1.9, ym + 2.6 + 0.2 * (i % 2), vz0 + 1.0, vz0 + 2.0, "caixa")
    C(a, -0.6, interp(PERFIL_N, 181.0) + 0.35, 181.0, 0.7, 0.7, 1.0, "ferrugem", ry=35, semColisao=True)

    # --- plataforma de manutenção do trecho leste
    qx0, qx1, qz0, qz1 = PLAT_E
    yq = -10.0 + 0.9
    B(a, qx0, qx1, -10.3, yq, qz0, qz1, "concreto_escuro")
    V(a, qx0, qx1, yq - 0.02, yq + 0.01, qz0 - 0.02, qz0 + 0.15, "lona_amarela")
    degraus(a, qx0 - 1.2, qx0, qz0, qz1, -10.0, yq, "+x")
    degraus(a, qx1, qx1 + 1.2, qz0, qz1, -10.0, yq, "-x")
    V(a, 14.0, 15.2, yq, yq + 1.6, EZ1 - 0.5, EZ1, "chapa_verde")

    # --- vagão de metrô tombado de lado (sobra a faixa norte, z 206,2..209)
    gx0, gx1, gz0, gz1 = VAGAO
    yv = -20.0
    B(a, gx0, gx1, yv - 0.3, yv + 2.9, gz0 + 0.2, 204.8, "chapa_azul")            # caixa do vagão
    B(a, gx0 + 2.0, gx1 - 1.0, yv - 0.3, yv + 1.6, 204.8, gz1, "rocha_escura")            # entulho junto ao teto do vagão
    V(a, gx0, gx1, yv + 2.9, yv + 2.95, gz0 + 0.5, 204.5, "metal")                 # lateral de cima
    for i in range(7):  # janelas (agora voltadas para cima) e portas
        wx = gx0 + 1.0 + i * 2.1
        V(a, wx, wx + 1.4, yv + 2.95, yv + 2.98, gz0 + 1.6, gz0 + 2.8, "escuro")
    V(a, gx0, gx1, yv + 0.3, yv + 2.6, 204.8, 204.85, "metal")                    # teto do vagão, virado para o norte
    for x in (gx0 + 2.5, gx1 - 2.5):                                               # truques virados para o sul
        V(a, x - 1.2, x + 1.2, yv + 0.4, yv + 2.5, gz0 - 0.02, gz0 + 0.2, "escuro")
    V(a, gx0 - 0.05, gx0, yv, yv + 2.9, gz0 + 0.2, 204.8, "lona_amarela")
    for _ in range(9):
        rocha(a, R.uniform(gx0 + 2.5, gx1 - 1.5), yv + R.uniform(1.4, 2.4), R.uniform(205.0, 206.0),
              R.uniform(0.6, 1.4), R.uniform(0.5, 1.1), R.uniform(0.5, 1.0), colisao=False)
    # trilhos arrancados e retorcidos
    C(a, 94.0, yv + 0.3, 203.0, 7.0, 0.12, 0.08, "metal", ry=14, rz=4, semColisao=True)
    C(a, 116.0, yv + 0.25, 205.8, 6.0, 0.12, 0.08, "metal", ry=-11, semColisao=True)


def fim_do_duto(a: Area):
    """Parede do fim do duto com o portão aberto para a Estação Aurora (tarefa 4, subsolo_estacao.py).
    As folhas abertas ficam do lado da estação."""
    y = -25.0
    topo = y + ALT + ESP_TETO
    p0, p1 = PORTAO_FIM
    B(a, X_FIM, X_FIM + PW, y - 0.6, topo, EZ0 - PW, p0, "concreto")
    B(a, X_FIM, X_FIM + PW, y - 0.6, topo, p1, EZ1 + PW, "concreto")
    B(a, X_FIM, X_FIM + PW, y + 4.2, topo, p0, p1, "concreto")
    # moldura do vão, placa da estação e lâmpadas de aviso
    V(a, X_FIM - 0.5, X_FIM, y, y + 4.5, p0 - 0.4, p0, "ferrugem")
    V(a, X_FIM - 0.5, X_FIM, y, y + 4.5, p1, p1 + 0.4, "ferrugem")
    V(a, X_FIM - 0.5, X_FIM, y + 4.2, y + 4.6, p0 - 0.4, p1 + 0.4, "ferrugem")
    V(a, X_FIM - 0.4, X_FIM - 0.3, y + 4.75, y + 5.05, 203.6, 206.4, "chapa_clara")   # placa da estação
    V(a, X_FIM - 0.45, X_FIM - 0.3, y + 4.7, y + 4.85, 202.4, 202.7, "vitral_vermelho")
    V(a, X_FIM - 0.45, X_FIM - 0.3, y + 4.7, y + 4.85, 207.3, 207.6, "vitral_vermelho")
    # para-choque no fim dos trilhos e barreira de sacos diante do portão
    V(a, X_FIM - 1.0, X_FIM - 0.5, y, y + 0.9, ZT - 1.0, ZT + 1.0, "lona_amarela")
    V(a, X_FIM - 1.02, X_FIM - 0.98, y + 0.3, y + 0.6, ZT - 1.0, ZT + 1.0, "escuro")
    for z in (202.0, 208.0):
        B(a, X_FIM - 2.0, X_FIM - 1.2, y, y + 0.7, z - 0.8, z + 0.8, "pano")


def agua_e_musgo(a: Area):
    """Filetes de água escorrendo pelas paredes, poças e musgo luminoso perto da umidade."""
    def filete(eixo, plano, normal, s, y):
        if eixo == "x":
            x0, x1 = (plano, plano + 0.03) if normal > 0 else (plano - 0.03, plano)
            V(a, x0, x1, y, y + ALT, s - 0.12, s + 0.12, "agua")
            V(a, x0, x1, y, y + ALT * 0.6, s + 0.25, s + 0.33, "agua")
            px0, px1 = (plano, plano + 1.6) if normal > 0 else (plano - 1.6, plano)
            V(a, px0, px1, y + 0.005, y + 0.02, s - 0.9, s + 0.7, "agua")
        else:
            z0, z1 = (plano, plano + 0.03) if normal > 0 else (plano - 0.03, plano)
            V(a, s - 0.12, s + 0.12, y, y + ALT, z0, z1, "agua")
            V(a, s + 0.25, s + 0.33, y, y + ALT * 0.6, z0, z1, "agua")
            pz0, pz1 = (plano, plano + 1.6) if normal > 0 else (plano - 1.6, plano)
            V(a, s - 0.9, s + 0.7, y + 0.005, y + 0.02, pz0, pz1, "agua")

    for z in (52.0, 79.0, 92.0, 107.0, 139.0, 151.0, 167.0, 189.0, 199.0):
        y = interp(PERFIL_N, z)
        lado = R.choice([-1, 1]) if z < EZ0 - 2 else -1
        if lado > 0 and (PLAT_N[2] - 1.5 < z < PLAT_N[3] + 1.5 or any(f0 - 1 < z < f1 + 1 for f0, f1 in (PASSAGEM_A, PASSAGEM_B))):
            lado = -1
        plano = NX0 if lado < 0 else NX1
        filete("x", plano, -lado, z, y)
        for _ in range(3):
            mancha(a, plano, "x", -lado, z + R.uniform(-1.5, 1.5), y + R.uniform(0.2, 2.5), "musgo", 0.8)
    for x in (12.0, 36.0, 58.0, 77.0, 93.0, 121.0, 131.0):
        y = interp(PERFIL_E, x)
        lado = R.choice([-1, 1]) if not (PLAT_E[0] - 2 < x < PLAT_E[1] + 2) else -1
        plano = EZ0 if lado < 0 else EZ1
        filete("z", plano, -lado, x, y)
        for _ in range(3):
            mancha(a, plano, "z", -lado, x + R.uniform(-1.5, 1.5), y + R.uniform(0.2, 2.5), "musgo", 0.8)
    # gotejamento: pingos no teto e poças no leito
    for _ in range(26):
        z = R.uniform(Z_BOCA + 3, EZ0 - 2)
        y = interp(PERFIL_N, z)
        x = R.uniform(NX0 + 0.5, NX1 - 0.5)
        V(a, x - 0.6, x + 0.6, y + 0.01, y + 0.025, z - 0.8, z + 0.8, "agua")
    for _ in range(20):
        x = R.uniform(NX1 + 4, X_FIM - 3)
        y = interp(PERFIL_E, x)
        z = R.uniform(EZ0 + 0.5, EZ1 - 0.5)
        V(a, x - 0.8, x + 0.8, y + 0.01, y + 0.025, z - 0.6, z + 0.6, "agua")


# ====================================================================== Caverna da Fenda

def ponte_y(z):
    """Altura do tabuleiro da ponte (parábola com flecha FLECHA no meio)."""
    m, h = (AZ0 + AZ1) / 2, (AZ1 - AZ0) / 2
    return YF - FLECHA * (1 - ((z - m) / h) ** 2)


def caverna_fenda() -> Area:
    a = Area("duto_fenda", "Caverna da Fenda", "subsolo", "fenda", None, NX1 + 0.5, FX1 + 1.0)
    a.d["zonaPadrao"] = "vila"
    a.caixa((NX1 + 0.5, FUNDO_F - 1.0, FZ0 - 1.0), (FX1 + 1.0, TETO_F + 1.5, FZ1 + 1.0))

    # --- passagens do duto até o salão (compressão antes do alívio)
    for f0, f1 in (PASSAGEM_A, PASSAGEM_B):
        B(a, NX1 + PW, FX0, YF - ESP_PISO, YF, f0 - 0.6, f1 + 0.6, "chao")
        B(a, NX1 + PW, FX0, YF, YF + ALT_PASSAGEM + 0.8, f0 - 0.8, f0, "rocha")
        B(a, NX1 + PW, FX0, YF, YF + ALT_PASSAGEM + 0.8, f1, f1 + 0.8, "rocha")
        B(a, NX1 + PW, FX0, YF + ALT_PASSAGEM, YF + ALT_PASSAGEM + 0.8, f0, f1, "rocha")
        zona_tunel(a, NX1, FX0, YF - 1.0, YF + ALT_PASSAGEM, f0, f1)
        for x in (6.5, 9.0, 11.5):  # escoras de madeira
            V(a, x - 0.12, x + 0.12, YF, YF + ALT_PASSAGEM, f0, f0 + 0.2, "madeira")
            V(a, x - 0.12, x + 0.12, YF, YF + ALT_PASSAGEM, f1 - 0.2, f1, "madeira")
            V(a, x - 0.15, x + 0.15, YF + ALT_PASSAGEM - 0.25, YF + ALT_PASSAGEM, f0, f1, "madeira")
        for _ in range(5):
            mancha(a, f0, "z", 1, R.uniform(7.0, FX0), YF + R.uniform(0.4, 2.4), "musgo", 0.7)
            mancha(a, f1, "z", -1, R.uniform(7.0, FX0), YF + R.uniform(0.4, 2.4), "musgo", 0.7)

    # --- casca do salão: bordas (colisão até Y_SOLIDO, o resto visual), paredes e teto
    for z0, z1 in ((FZ0, AZ0), (AZ1, FZ1)):
        B(a, FX0, FX1, Y_SOLIDO, YF, z0, z1, "rocha")
        V(a, FX0, FX1, FUNDO_F, Y_SOLIDO, z0, z1, "rocha")
    furos = [(PASSAGEM_A[0], PASSAGEM_A[1]), (PASSAGEM_B[0], PASSAGEM_B[1])]
    zs = [FZ0 - 1.0] + [c for f in furos for c in f] + [FZ1 + 1.0]
    for i in range(0, len(zs) - 1, 2):
        B(a, FX0 - 1.0, FX0, Y_SOLIDO, TETO_F, zs[i], zs[i + 1], "rocha")
    for f0, f1 in furos:
        B(a, FX0 - 1.0, FX0, YF + ALT_PASSAGEM, TETO_F, f0, f1, "rocha")
        B(a, FX0 - 1.0, FX0, Y_SOLIDO, YF, f0, f1, "rocha")
    B(a, FX1, FX1 + 1.0, Y_SOLIDO, TETO_F, FZ0 - 1.0, FZ1 + 1.0, "rocha")
    B(a, FX0, FX1, Y_SOLIDO, TETO_F, FZ0 - 1.0, FZ0, "rocha")
    B(a, FX0, FX1, Y_SOLIDO, TETO_F, FZ1, FZ1 + 1.0, "rocha")
    B(a, FX0 - 1.0, FX1 + 1.0, TETO_F, TETO_F + 1.5, FZ0 - 1.0, FZ1 + 1.0, "rocha")
    # paredes do abismo abaixo do piso mínimo e fundo (só visuais)
    V(a, FX0 - 1.0, FX0, FUNDO_F - 1.0, Y_SOLIDO, AZ0, AZ1, "rocha")
    V(a, FX1, FX1 + 1.0, FUNDO_F - 1.0, Y_SOLIDO, AZ0, AZ1, "rocha")
    V(a, FX0, FX1, FUNDO_F - 1.0, FUNDO_F, AZ0, AZ1, "rocha")
    V(a, FX0 + 2, FX1 - 2, FUNDO_F + 0.01, FUNDO_F + 0.04, AZ0 + 6, AZ1 - 7, "agua")   # filete no fundo
    for _ in range(18):  # blocos caídos no fundo
        rocha(a, R.uniform(FX0 + 2, FX1 - 2), FUNDO_F + R.uniform(0.3, 1.5), R.uniform(AZ0 + 1.5, AZ1 - 1.5),
              R.uniform(1.5, 5.0), R.uniform(1.0, 3.0), R.uniform(1.5, 4.0), colisao=False)

    # --- faces irregulares do abismo: saliências em várias profundidades (dão a escala dos 40 m)
    for face, normal in ((AZ0, 1), (AZ1, -1)):
        for _ in range(26):
            x = R.uniform(FX0 + 1, FX1 - 1)
            if abs(x - PONTE_X) < 3.0:
                continue
            y = R.uniform(FUNDO_F + 2, YF - 1.5)
            w, h, d = R.uniform(2, 7), R.uniform(1.5, 6), R.uniform(0.8, 2.6)
            rocha(a, x, y, face + normal * d * 0.35, w, h, d, colisao=False)
        for i in range(70):  # musgo nas faces em toda a altura: mais apagado quanto mais fundo
            y = R.uniform(FUNDO_F + 1.0, YF - 0.8)
            mat = "musgo" if y > YF - 22 else "musgo_fraco"
            mancha(a, face, "z", normal, R.uniform(FX0 + 1, FX1 - 1), y, mat, R.uniform(0.6, 1.5))
        for _ in range(26):  # raízes e cortinas de musgo pendendo da borda (escala vertical)
            x = R.uniform(FX0 + 1, FX1 - 1)
            if abs(x - PONTE_X) < 2.0:
                continue
            comp = R.uniform(3.0, 16.0)
            p0, p1 = (face, face + normal * 0.05)
            V(a, x - 0.04, x + 0.04, YF - comp, YF + 0.05, min(p0, p1), max(p0, p1), "musgo_fraco")
            V(a, x - 0.12, x + 0.12, YF - comp - 0.3, YF - comp, min(p0, p1) - 0.03, max(p0, p1) + 0.03, "musgo")
        for _ in range(30):  # borda: tufos de musgo marcando o lábio do abismo
            x = R.uniform(FX0 + 1, FX1 - 1)
            if abs(x - PONTE_X) < 2.0:
                continue
            w = R.uniform(0.4, 1.2)
            z0, z1 = (face - 0.3, face) if normal > 0 else (face, face + 0.3)
            V(a, x - w / 2, x + w / 2, YF, YF + 0.05, z0, z1, "musgo")
            V(a, x - w / 2, x + w / 2, YF - R.uniform(0.4, 1.2), YF, min(face, face + normal * 0.04), max(face, face + normal * 0.04), "musgo")
    for plano, normal in ((FX0, 1), (FX1, -1)):  # paredes das pontas do abismo
        for _ in range(30):
            y = R.uniform(FUNDO_F + 1.0, YF - 0.8)
            mancha(a, plano, "x", normal, R.uniform(AZ0 + 1, AZ1 - 1), y, "musgo" if y > YF - 22 else "musgo_fraco", R.uniform(0.6, 1.4))
    for _ in range(40):  # fungos brilhando no fundo, 40 m abaixo
        x, z = R.uniform(FX0 + 1.5, FX1 - 1.5), R.uniform(AZ0 + 1.0, AZ1 - 1.0)
        s_ = R.uniform(0.15, 0.45)
        V(a, x - s_, x + s_, FUNDO_F, FUNDO_F + s_ * 0.8, z - s_, z + s_, R.choice(["luz_fraca", "musgo", "musgo"]))
    # acampamento abandonado numa saliência, 20 m abaixo, na face norte (visível e inalcançável)
    cx, cy = 26.0, YF - 20.0
    V(a, cx - 3.0, cx + 3.0, cy - 1.5, cy, AZ1 - 2.5, AZ1, "rocha")
    V(a, cx - 1.8, cx + 0.2, cy, cy + 1.2, AZ1 - 2.1, AZ1 - 0.6, "lona_azul")
    V(a, cx + 0.8, cx + 1.1, cy, cy + 0.35, AZ1 - 1.6, AZ1 - 1.3, "luz_ambar")
    V(a, cx + 1.6, cx + 2.4, cy, cy + 0.5, AZ1 - 1.8, AZ1 - 1.0, "caixa")
    V(a, cx + 2.6, cx + 2.65, cy, YF, AZ1 - 0.25, AZ1 - 0.2, "madeira")   # corda pendurada da borda
    # cascata fina caindo de uma fenda na parede leste até o fundo
    V(a, FX1 - 0.35, FX1, FUNDO_F, 9.0, 128.6, 129.4, "agua")
    V(a, FX1 - 0.25, FX1, FUNDO_F, 9.0, 130.0, 130.25, "agua")
    V(a, FX1 - 6.0, FX1, FUNDO_F + 0.05, FUNDO_F + 0.1, 126.0, 132.0, "agua")
    for y in range(6, -44, -6):
        mancha(a, FX1, "x", -1, 127.5 + R.uniform(-1.0, 1.0), y, "musgo", 1.4)

    # --- rochas grandes contra as paredes, estalagmites e estalactites (fora dos caminhos)
    caminhos = [(FX0, 44.0, 99.0, 108.0), (35.0, 45.0, 99.0, AZ0), (FX0, 46.0, 150.0, 160.0), (35.0, 45.0, AZ1, 160.0),
                (44.0, 67.0, 132.0, 148.5), (FX0, 18.0, 92.0, 168.0)]
    def livre(x, z, r):
        return not any(x0 - r < x < x1 + r and z0 - r < z < z1 + r for x0, x1, z0, z1 in caminhos)
    for _ in range(60):
        lado = R.choice(["l", "n", "s", "s", "n"])
        w, h, d = R.uniform(3, 8), R.uniform(3, 12), R.uniform(3, 8)
        if lado == "l":
            x, z = FX1 - R.uniform(0, 2), R.uniform(FZ0 + 3, FZ1 - 3)
        elif lado == "n":
            x, z = R.uniform(FX0 + 6, FX1 - 4), FZ1 - R.uniform(0, 2)
        else:
            x, z = R.uniform(FX0 + 6, FX1 - 4), FZ0 + R.uniform(0, 2)
        if AZ0 - 2 < z < AZ1 + 2 or not livre(x, z, max(w, d) / 2 + 0.5):
            continue
        y0 = R.choice([YF, YF, R.uniform(2, 14)])
        rocha(a, x, y0 + h / 2, z, w, h, d, colisao=y0 == YF)
        if R.random() < 0.6:
            mancha(a, z - d / 2 if lado != "s" else z + d / 2, "z", -1 if lado != "s" else 1, x, y0 + R.uniform(0.5, h - 0.5), "musgo", 1.0)
    for _ in range(26):  # estalagmites nas bordas
        x, z = R.uniform(FX0 + 4, FX1 - 2), R.choice([R.uniform(FZ0 + 2, AZ0 - 2), R.uniform(AZ1 + 2, FZ1 - 2)])
        h = R.uniform(0.8, 3.5)
        if livre(x, z, 1.2):
            rocha(a, x, YF + h / 2, z, R.uniform(0.6, 1.4), h, R.uniform(0.6, 1.4))
    for _ in range(50):  # estalactites
        x, z = R.uniform(FX0 + 2, FX1 - 2), R.uniform(FZ0 + 2, FZ1 - 2)
        h = R.uniform(2.0, 8.0)
        s = R.uniform(0.8, 2.6)
        rocha(a, x, TETO_F - h / 2 + 0.3, z, s, h, s, colisao=False)
    for _ in range(40):  # musgo nas paredes do salão e cortinas penduradas do teto
        lado = R.choice(["o", "l", "n", "s"])
        y = R.uniform(YF + 0.3, 12.0)
        if lado == "o":
            z = R.uniform(FZ0 + 1, FZ1 - 1)
            if not any(f0 - 0.5 < z < f1 + 0.5 for f0, f1 in furos):
                mancha(a, FX0, "x", 1, z, y, "musgo", 0.9)
        elif lado == "l":
            mancha(a, FX1, "x", -1, R.uniform(FZ0 + 1, FZ1 - 1), y, "musgo", 0.9)
        elif lado == "n":
            mancha(a, FZ1, "z", -1, R.uniform(FX0 + 1, FX1 - 1), y, "musgo", 0.9)
        else:
            mancha(a, FZ0, "z", 1, R.uniform(FX0 + 1, FX1 - 1), y, "musgo", 0.9)
    for _ in range(30):
        x, z = R.uniform(FX0 + 3, FX1 - 3), R.uniform(FZ0 + 3, FZ1 - 3)
        h = R.uniform(1.5, 7.0)
        V(a, x - 0.03, x + 0.03, TETO_F - h, TETO_F, z - 0.03, z + 0.03, "musgo_fraco")
        V(a, x - 0.08, x + 0.08, TETO_F - h - 0.12, TETO_F - h, z - 0.08, z + 0.08, "musgo")
    for _ in range(36):  # tufos no chão das bordas
        x, z = R.uniform(FX0 + 1, FX1 - 1), R.choice([R.uniform(FZ0 + 1, AZ0 - 0.5), R.uniform(AZ1 + 0.5, FZ1 - 1)])
        s = R.uniform(0.2, 0.6)
        V(a, x - s, x + s, YF, YF + 0.04, z - s * 0.7, z + s * 0.7, "musgo_fraco")

    ponte(a)
    mirante(a)

    # --- luzes reais: musgo esverdeado, lanternas nas cabeceiras da ponte e o brilho do fundo
    a.luz(26.0, YF + 3.5, 104.0, MUSGO, 0.7, 18)
    a.luz(PONTE_X + 1.6, YF + 2.2, AZ0 - 1.0, AMBAR, 0.8, 13)
    a.luz(60.0, Y_MIRANTE + 3.0, 140.0, MUSGO, 0.8, 22)
    a.luz(PONTE_X, FUNDO_F + 14.0, 129.0, MUSGO, 0.45, 24)
    a.luz(26.0, YF + 3.5, 155.0, MUSGO, 0.6, 16)

    a.entrada("inicio", 20.0, YF)
    a.d["entradas"]["inicio"].update(z=103.0, yaw=rad(90))
    a.d["entradas"]["mirante"] = dict(x=60.0, y=Y_MIRANTE, z=140.0, yaw=rad(-120))
    return a


def ponte(a: Area):
    """Ponte de corda: tabuleiro com colisão em segmentos inclinados, tábuas e cordas só visuais,
    guarda-corpo invisível dos dois lados."""
    x0, x1 = PONTE_X - PONTE_L, PONTE_X + PONTE_L
    n = 8
    zs = [AZ0 - 0.4 + (AZ1 - AZ0 + 0.8) * i / n for i in range(n + 1)]
    for za, zb in zip(zs, zs[1:]):
        faixa_z(a, x0, x1, za, zb, ponte_y(za), ponte_y(zb), 0.12, "madeira", invisivel=True)
    # tábuas
    z = AZ0 + 0.1
    while z < AZ1 - 0.1:
        y = ponte_y(z)
        incl = math.degrees(math.atan2(ponte_y(z - 0.2) - ponte_y(z + 0.2), 0.4))
        falta = R.random() < 0.05
        if not falta:
            C(a, PONTE_X + R.uniform(-0.05, 0.05), y - 0.05, z, 2 * PONTE_L + R.uniform(-0.1, 0.2), 0.08, 0.24,
              R.choice(["madeira", "madeira", "caixa"]), rx=incl, ry=R.uniform(-3, 3), semColisao=True)
        z += 0.3
    # longarinas de corda sob as tábuas
    for x in (x0 + 0.1, x1 - 0.1):
        for za, zb in zip(zs, zs[1:]):
            faixa_z(a, x - 0.03, x + 0.03, za, zb, ponte_y(za) - 0.09, ponte_y(zb) - 0.09, 0.05, "pano", semColisao=True)
    # corrimãos de corda (mais frouxos) e tirantes verticais
    def corda_y(zz):
        return ponte_y(zz) + 1.05 + 0.25 * (1 - ((zz - (AZ0 + AZ1) / 2) / ((AZ1 - AZ0) / 2)) ** 2) * -1
    for x in (x0 - 0.05, x1 + 0.05):
        for za, zb in zip(zs, zs[1:]):
            faixa_z(a, x - 0.03, x + 0.03, za, zb, corda_y(za), corda_y(zb), 0.05, "pano", semColisao=True)
            faixa_z(a, x - 0.02, x + 0.02, za, zb, corda_y(za) - 0.5, corda_y(zb) - 0.5, 0.03, "pano", semColisao=True)
        z = AZ0 + 0.6
        while z < AZ1:
            V(a, x - 0.02, x + 0.02, ponte_y(z) - 0.1, corda_y(z), z - 0.02, z + 0.02, "pano")
            z += 1.2
        # guarda-corpo invisível (não barra a câmera)
        lado = -0.06 if x < PONTE_X else 0.06
        B(a, x + lado - 0.05, x + lado + 0.05, YF - FLECHA - 0.4, YF + 1.25, AZ0 - 0.4, AZ1 + 0.4, "pano", invisivel=True, semCamera=True)
    # lanternas a óleo penduradas nas cordas a cada 5 m (a ponte se recorta no escuro, vista do mirante)
    for i, zl in enumerate((AZ0 + 3.0, AZ0 + 8.0, AZ0 + 13.0, AZ0 + 18.0)):
        xl = x1 + 0.12 if i % 2 == 0 else x0 - 0.12
        yl = corda_y(zl) - 0.35
        V(a, xl - 0.01, xl + 0.01, yl + 0.18, corda_y(zl), zl - 0.01, zl + 0.01, "escuro")
        V(a, xl - 0.09, xl + 0.09, yl, yl + 0.2, zl - 0.09, zl + 0.09, "luz_ambar")
    # cabeceiras: postes de madeira, estacas e lanternas
    for zc in (AZ0, AZ1):
        dz = -0.6 if zc == AZ0 else 0.6
        for x in (x0 - 0.3, x1 + 0.3):
            B(a, x - 0.15, x + 0.15, YF, YF + 1.6, zc + dz - 0.15, zc + dz + 0.15, "madeira")
            C(a, x, YF + 0.9, zc + dz * 2.2, 0.06, 1.9, 0.06, "pano", rx=50 * (1 if zc == AZ0 else -1), semColisao=True)
        V(a, x1 + 0.15, x1 + 0.45, YF + 1.6, YF + 1.95, zc + dz - 0.15, zc + dz + 0.15, "luz_ambar")
    # sob a ponte, nas cabeceiras: vigas de apoio cravadas na rocha
    for zc in (AZ0, AZ1):
        dz = 1 if zc == AZ0 else -1
        C(a, PONTE_X, YF - 1.2, zc + dz * 0.6, 2.4, 0.3, 0.3, "madeira", rx=40 * dz, semColisao=True)


def mirante(a: Area):
    """Mirante sobre a borda norte, 4 m acima, avançando 6 m sobre o abismo."""
    mx0, mx1, mz0, mz1 = MIRANTE
    y = Y_MIRANTE
    B(a, mx0, mx1, Y_SOLIDO, y, AZ1, mz1, "rocha")                  # rochedo
    B(a, mx0, mx1, y - 0.5, y, mz0, AZ1, "rocha")                   # laje em balanço
    V(a, mx0 + 1.0, mx1 - 1.5, y - 3.0, y - 0.5, mz0 + 1.0, AZ1, "rocha")
    for x in (mx0 + 1.5, mx1 - 1.5):                                 # escoras de ferro sob o balanço
        C(a, x, y - 2.0, AZ1 - 2.0, 0.2, 4.4, 0.2, "ferrugem", rx=-45, semColisao=True)
    # escadaria esculpida na rocha (sobe para +x até o mirante)
    sz0, sz1 = 142.5, 145.5
    comp = degraus(a, mx0 - 8.0, mx0, sz0, sz1, YF, y, "+x", mat="rocha")
    # guarda-corpos
    corrimao(a, "x", mz0, mx0, mx1, y, lado=0.1)
    corrimao(a, "z", mx1, mz0, mz1, y, lado=-0.1)
    corrimao(a, "x", mz1, mx0, mx1, y, lado=-0.1)
    corrimao(a, "z", mx0, mz0, mz1, y, lacunas=[(sz0, sz1)], lado=0.1)
    B(a, mx0 - comp - 0.4, mx0, YF, y + CORRIMAO, sz0 - 0.1, sz0, "metal", invisivel=True, semCamera=True)
    # luminária de musgo cultivado num balde e um banco de pedra
    V(a, mx1 - 1.2, mx1 - 0.6, y, y + 0.5, mz1 - 1.2, mz1 - 0.6, "ferrugem")
    V(a, mx1 - 1.15, mx1 - 0.65, y + 0.5, y + 0.6, mz1 - 1.15, mz1 - 0.65, "musgo")
    B(a, mx0 + 3.0, mx0 + 5.5, y, y + 0.45, mz1 - 1.4, mz1 - 0.6, "rocha")


# ====================================================================== Galeria dos Contrabandistas

def galeria_contrabandistas() -> Area:
    a = Area("duto_contrabandistas", "Galeria dos Contrabandistas", "subsolo", "contrabandistas", None, -4.5, 4.5)
    a.d["zonaPadrao"] = "tunel"
    a.caixa((-4.5, -11.0, EZ1 + PW), (4.5, 4.5, 323.5))
    z_ini = EZ1 + PW  # 210
    # trechos: (z0, z1, piso, teto, meia largura)
    trechos = [(EZ1, 250.0, -10.0, -7.2, GL), (252.4, 282.0, -8.5, -5.7, GL), (282.0, 292.0, -8.5, -5.0, 4.0),
               (292.0, 300.0, -8.5, -5.7, GL), (302.4, 314.0, -7.0, -4.2, GL)]
    for z0, z1, yp, yt, hl in trechos:
        B(a, -hl, hl, yp - 0.5, yp, z0, z1, "chao")
        B(a, -hl - 1.0, -hl, yp - 0.5, yt + 0.6, z0, z1, "rocha_escura")
        B(a, hl, hl + 1.0, yp - 0.5, yt + 0.6, z0, z1, "rocha_escura")
        B(a, -hl - 1.0, hl + 1.0, yt, yt + 0.6, z0, z1, "rocha_escura")
    # degraus (0,25 m) entre os trechos, com teto e paredes por cima
    for z0, ya, yb, yt in ((250.0, -10.0, -8.5, -5.7), (300.0, -8.5, -7.0, -4.2)):
        n = 6
        for i in range(n):
            B(a, -GL, GL, ya - 0.5, ya + 0.25 * (i + 1), z0 + 0.4 * i, z0 + 0.4 * (i + 1), "concreto")
        B(a, -GL - 1.0, -GL, ya - 0.5, yt + 0.6, z0, z0 + 2.4, "rocha_escura")
        B(a, GL, GL + 1.0, ya - 0.5, yt + 0.6, z0, z0 + 2.4, "rocha_escura")
        B(a, -GL - 1.0, GL + 1.0, yt, yt + 0.6, z0, z0 + 2.4, "rocha_escura")
    # paredes dos degraus de largura no depósito (z 282 e 292, de 1,4 a 4 m)
    for zf in (282.0, 292.0):
        dz = -1.0 if zf == 282.0 else 0.0
        B(a, -5.0, -GL, -9.0, -4.4, zf + dz, zf + dz + 1.0, "rocha_escura")
        B(a, GL, 5.0, -9.0, -4.4, zf + dz, zf + dz + 1.0, "rocha_escura")
        B(a, -GL, GL, -5.1, -4.4, zf + dz * 0.5, zf + dz * 0.5 + 0.5, "rocha_escura")   # tampa entre os tetos
    # tampas entre o teto baixo e o teto mais alto depois de cada lance
    B(a, -GL - 1.0, GL + 1.0, -6.6, -5.1, 249.4, 250.0, "rocha_escura")
    B(a, -GL - 1.0, GL + 1.0, -5.1, -3.6, 299.4, 300.0, "rocha_escura")
    zona_tunel(a, -4.0, 4.0, -11.0, 4.2, z_ini, 323.0)

    # --- câmara da escotilha: poço de 2,5 m com a escada de mão e o patamar sob o alçapão
    y0, y1 = -7.0, 1.0
    B(a, -2.0, 2.0, y0 - 0.5, y0, 314.0, 322.0, "chao")
    B(a, -3.0, -2.0, y0 - 0.5, Y_ALCAPAO + 0.6, 314.0, 323.0, "rocha_escura")
    B(a, 2.0, 3.0, y0 - 0.5, Y_ALCAPAO + 0.6, 314.0, 323.0, "rocha_escura")
    B(a, -3.0, 3.0, y0 - 0.5, Y_ALCAPAO + 0.6, 322.0, 323.0, "rocha_escura")
    B(a, -3.0, 3.0, -4.2, Y_ALCAPAO + 0.6, 316.0, 317.0, "rocha_escura")         # face sul do poço, acima da galeria
    B(a, -2.0, 2.0, -4.2, -3.6, 314.0, 316.0, "rocha_escura")                  # teto da entrada da câmara
    B(a, -2.0, 2.0, y0, y1, Z_ESCADA + 0.05, 322.0, "concreto")           # patamar (face sul para a escada)
    B(a, -3.0, 3.0, Y_ALCAPAO, Y_ALCAPAO + 0.6, 316.0, 323.0, "rocha_escura")    # teto do poço
    a.d["escadas"].append(dict(x=0.0, z=Z_ESCADA, y0=y0, y1=y1, tipo="escada", yaw=0))
    corrimao(a, "x", Z_ESCADA + 0.05, -2.0, 2.0, y1, lacunas=[(-0.5, 0.5)], lado=0.1)
    # o alçapão fechado: tampa de aço com volante, moldura e trava
    V(a, -0.8, 0.8, Y_ALCAPAO - 0.12, Y_ALCAPAO, 320.0, 321.6, "metal")
    V(a, -0.95, 0.95, Y_ALCAPAO - 0.06, Y_ALCAPAO, 319.85, 321.75, "ferrugem")
    V(a, -0.3, 0.3, Y_ALCAPAO - 0.22, Y_ALCAPAO - 0.12, 320.5, 321.1, "escuro")
    V(a, 0.6, 0.75, Y_ALCAPAO - 0.35, Y_ALCAPAO - 0.12, 320.6, 321.0, "lona_amarela")
    V(a, -1.95, -1.9, y1 + 0.4, Y_ALCAPAO - 0.2, 320.7, 320.8, "metal")   # cano de ventilação
    V(a, 1.9, 1.98, y1 + 1.6, y1 + 1.85, 320.5, 320.8, "vitral_vermelho")  # lâmpada de aviso
    V(a, -1.5, 1.5, y1 + 1.0, y1 + 1.3, 321.95, 322.0, "lona_amarela")
    V(a, -1.98, -1.95, y0 + 0.5, y0 + 2.5, 315.0, 316.5, "chapa_clara")   # mapa colado na parede
    for _ in range(5):
        mancha(a, 322.0, "z", -1, R.uniform(-1.6, 1.6), R.uniform(y0 + 0.5, y1 - 0.5), "agua", 0.7)

    # --- escoras, lâmpadas de gambiarra, marcas e esconderijos
    z = z_ini + 1.5
    while z < 314.0:
        if 282.0 <= z <= 292.0 or 249.5 <= z <= 252.9 or 299.5 <= z <= 302.9:
            z += 3.0
            continue
        yp = -10.0 if z < 250 else (-8.5 if z < 302 else -7.0)
        yt = -7.2 if z < 250 else (-5.7 if z < 300 else -4.2)
        V(a, -GL, -GL + 0.2, yp, yt, z - 0.1, z + 0.1, "madeira_escura")
        V(a, GL - 0.2, GL, yp, yt, z - 0.1, z + 0.1, "madeira_escura")
        V(a, -GL, GL, yt - 0.22, yt, z - 0.11, z + 0.11, "madeira_escura")
        z += 3.0
    for z0, z1, yp in ((z_ini, 249.5, -10.0), (253.0, 281.5, -8.5), (292.5, 299.5, -8.5), (303.0, 313.5, -7.0)):
        z = z0
        while z < z1 - 1.0:  # tábuas de contenção atrás das escoras, com falhas mostrando a rocha
            for lado in (-1, 1):
                for k in range(R.randint(2, 5)):
                    yy = yp + 0.3 + k * 0.42 + R.uniform(-0.05, 0.05)
                    xf = lado * GL
                    V(a, min(xf, xf - lado * 0.06), max(xf, xf - lado * 0.06), yy, yy + 0.3, z + 0.15, z + 2.85, R.choice(["madeira_escura", "madeira_escura", "madeira"]))
            z += 3.0
    V(a, -GL + 0.25, -GL + 0.28, -10.0 + 2.4, -10.0 + 2.43, z_ini, 250.0, "escuro")     # fio da gambiarra
    V(a, -GL + 0.25, -GL + 0.28, -8.5 + 2.4, -8.5 + 2.43, 252.4, 300.0, "escuro")
    for zl, yl in ((224.0, -10.0 + 2.2), (238.0, -10.0 + 2.2), (266.0, -8.5 + 2.2), (296.0, -8.5 + 2.2), (309.0, -7.0 + 2.2)):
        V(a, -GL + 0.18, -GL + 0.38, yl, yl + 0.18, zl - 0.1, zl + 0.1, "luz_ambar")
    for zl, yp in ((218.0, -10.0), (247.0, -10.0), (275.0, -8.5), (306.0, -7.0)):  # setas pintadas
        V(a, GL - 0.03, GL, yp + 1.2, yp + 1.5, zl - 0.6, zl + 0.6, "lona_amarela")
        V(a, GL - 0.03, GL, yp + 1.05, yp + 1.65, zl + 0.5, zl + 0.8, "lona_amarela")
    for zc, yp in ((231.0, -10.0), (259.0, -8.5), (271.0, -8.5), (296.5, -8.5)):     # caixotes encostados (deixam 2,5 m)
        B(a, GL - 0.3, GL, yp, yp + 0.8, zc - 0.5, zc + 0.5, "caixa")
    # depósito dos contrabandistas: prateleiras, mesa, rede e caixotes
    yp = -8.5
    B(a, -4.0, -3.2, yp, yp + 2.6, 283.0, 291.0, "madeira_escura")
    for yy in (0.8, 1.6, 2.4):
        V(a, -3.25, -3.2, yp + yy, yp + yy + 0.06, 283.0, 291.0, "madeira_escura")
    for i in range(6):
        V(a, -3.2, -2.85, yp + 0.86 + 0.8 * (i % 3), yp + 1.2 + 0.8 * (i % 3), 283.5 + i * 1.2, 284.3 + i * 1.2,
          R.choice(["caixa", "pano", "lona_vermelha", "metal"]))
    B(a, 2.2, 3.8, yp, yp + 0.8, 284.0, 286.5, "madeira_escura")                    # mesa
    V(a, 2.6, 3.0, yp + 0.8, yp + 1.05, 284.6, 285.0, "luz_ambar")          # lampião
    V(a, 2.4, 3.6, yp + 0.8, yp + 0.83, 285.4, 286.2, "chapa_clara")         # papéis
    for zc in (288.0, 289.4):
        B(a, 2.6, 3.9, yp, yp + 1.2, zc - 0.6, zc + 0.6, "caixa")
    V(a, 2.95, 3.85, yp + 1.2, yp + 1.9, 288.2, 289.0, "caixa")
    V(a, -3.0, 0.5, yp + 1.4, yp + 1.5, 290.6, 291.0, "pano")                # rede
    zona_tunel(a, -4.0, 4.0, -9.0, -5.0, 282.0, 292.0)

    a.luz(0.0, -10.0 + 2.3, 230.0, AMBAR, 0.6, 12, piscar=True)
    a.luz(1.5, yp + 2.6, 286.0, AMBAR, 0.8, 12)
    a.luz(0.0, y1 + 1.8, 320.8, VERMELHO, 0.7, 10)
    a.entrada("inicio", 0.0, -10.0)
    a.d["entradas"]["inicio"].update(z=212.0, yaw=rad(0))
    a.d["entradas"]["escotilha"] = dict(x=0.0, y=y1, z=320.6, yaw=rad(0))
    return a


def todas():
    from sinalizacao import sinalizar
    return sinalizar([duto_tunel(), caverna_fenda(), galeria_contrabandistas()])


if __name__ == "__main__":
    for area in todas():
        area.salvar()
