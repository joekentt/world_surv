"""Estação Aurora e Boca do Poço, em blocos (revisão 2, fase 2, tarefa 4).

Uso: python3 tools/areas/subsolo_estacao.py   (grava content/areas/estacao_aurora.json e boca_estacao.json)

Seção 5.1 de docs/spec/05-mapa.md e seção 7 de docs/spec/07-arte-personagens-vila.md.
Mundo "subsolo", mesmos eixos da vila e do duto (Y para cima, norte em +Z).

Estação Aurora (caixa x 141..202, z 194..216, y -27..-12):
  - salão de 60 x 20 m (x 141..201, z 195..215), plataforma central (ilha, z 199..211) em y = -25, no
    nível do piso do duto, e duas valas de trilhos (z 195..199 e 211..215) 1 m abaixo, com degraus de
    saída nas pontas; um trem abandonado na vala norte;
  - o Duto Norte entra pelo portão aberto em x = 140 (z 202,6..207,4), direto na ilha;
  - duas escadas rolantes paradas (degraus de 0,25 m) sobem de x = 158,4 a 168 até o mezanino em y = -19,
    que cobre a ilha de x = 168 a 201 e serve de ponto de descanso (bancos, bilheteria, saída antiga
    soterrada, acampamento);
  - painéis de horário apagados, azulejos (blocos de cor), luz fria e esparsa, poeira suspensa.
Boca do Poço (caixa x 171..185, z 198..222, y -12..4,5; o fundo do poço fica dentro do salão):
  - poço de ventilação de 25 m, interior x 175,5..180,5, z 202,5..207,5, de y = -25 (porta para a ilha,
    na face sul) a y = 0; centro em (178, 205), a Boca do Poço combinada (superfície = x - 178, z - 205);
  - escada de mão em quatro lances de 6,25 m, em zigue-zague em volta de uma coluna central (z 204,8..205,2),
    com patamares em -18,75, -12,5 e -6,25; elevador de carga parado no fundo (só visual), no lado leste;
  - no topo (y = 0): casa do poço com armários de EPI, descontaminação com chuveiros e névoa (z 210,5..216),
    eclusa com duas portas (câmara z 216,5..220,5). A porta externa (z = 220,5) é a saída do tipo "eclusa"
    para a área `superficie_boca` (entrada "boca"); a volta da superfície chega na entrada "superficie".
Valores de src/config.ts: degraus de 0,25 m, corredores de 2,5 m ou mais, cápsula de 0,3 x 1,7 m.
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_areas import DESTINO, FRIA, Area, rad  # noqa: E402
from subsolo_duto import C, degraus, faixa_x  # noqa: E402
from subsolo_vila import B, V, corrimao, laje, lance, r3, zona_tunel  # noqa: E402

R = random.Random(404)
# área descartável: recebe as placas genéricas substituídas por peças, para o sorteio (R) seguir igual
LIXO = Area("lixo", "", "", "", None, 0.0, 1.0)
VERMELHA = [1.0, 0.16, 0.08]
FRIA_FRACA = [0.6, 0.85, 1.0]

# ---------------------------------------------------------------- salão
Y0 = -25.0                     # piso da ilha (= piso do fim do duto)
YV = -25.9                     # fundo das valas (0,9 m abaixo da ilha)
Y_BASE = -26.0                 # base dos sólidos com colisão (piso mínimo do subsolo, ver docs/decisoes.md)
HX0, HX1, HZ0, HZ1 = 141.0, 201.0, 195.0, 215.0
YT = -13.0                     # teto do salão
W = 1.0                        # espessura das paredes
ILHA = (199.0, 211.0)
VALAS = ((195.0, 199.0), (211.0, 215.0))
PORTAO = (202.6, 207.4)        # vão do portão do duto em x = 140
TOPO_PAREDE_DUTO = -18.9       # topo da parede do fim do duto (subsolo_duto.fim_do_duto)
TREM = (146.0, 171.0)          # trem abandonado na vala norte

# escadas rolantes: 24 degraus de 0,25 x 0,4 m, de y = -25 a -19
N_DEG, DEG, PIS = 24, 0.25, 0.4
ESC_X0 = 158.4
ESC_X1 = ESC_X0 + N_DEG * PIS  # 168,0
YM = Y0 + N_DEG * DEG          # -19: mezanino
FAIXAS = ((202.95, 204.75), (205.25, 207.05))                   # pistas (1,8 m)
BALAUSTRES = ((202.55, 202.95), (204.75, 205.25), (207.05, 207.45))
MEZ_X0 = ESC_X1

# ---------------------------------------------------------------- poço
BOCA = (178.0, 205.0)
PX0, PX1, PZ0, PZ1 = 175.5, 180.5, 202.5, 207.5   # interior
PE = 0.5                                          # paredes
POCO_EXT = (PX0 - PE, PX1 + PE, PZ0 - PE, PZ1 + PE)
LADO = 178.3                   # divisa entre o lado da escada (oeste) e o do elevador (leste)
ESP_Z = (204.8, 205.2)         # coluna central (espinha) do lado da escada
XA, XB = 176.2, 177.6          # eixos das escadas de mão (A e C ao sul da espinha, B e D ao norte)
PATAMARES = (-18.75, -12.5, -6.25)
PORTA_POCO = (175.6, 178.1)    # porta na face sul do poço, no nível da ilha
YP = 0.0                       # topo do poço, piso da eclusa

# ---------------------------------------------------------------- topo
SALA = (172.0, 184.0, 199.0, 210.0)       # casa do poço
DESC = (175.0, 181.0, 210.5, 216.0)       # descontaminação
ECL = (175.0, 181.0, 216.5, 220.5)        # câmara da eclusa
ALT_T = 3.5                               # pé-direito do topo
SAIDA_ECLUSA = (178.0, 219.6)
ENTRADA_SUPERFICIE = (178.0, 217.6)


def placa(a: Area, x0, x1, y0, y1, plano, normal, eixo="x", mat="chapa_clara", letras=True):
    """Placa rente a uma face (eixo 'x': face em z = plano; 'z': face em x = plano) com 'letras' escuras."""
    e0, e1 = (plano, plano + 0.05 * normal) if normal > 0 else (plano + 0.05 * normal, plano)
    f0, f1 = min(e0, e1), max(e0, e1)
    if eixo == "x":
        V(a, x0, x1, y0, y1, f0, f1, mat)
    else:
        V(a, f0, f1, y0, y1, x0, x1, mat)
    if not letras:
        return
    n = max(3, int((x1 - x0) / 0.32))
    passo = (x1 - x0 - 0.3) / n
    g0, g1 = (f1, f1 + 0.02) if normal > 0 else (f0 - 0.02, f0)
    for i in range(n):
        u = x0 + 0.15 + i * passo
        h = (y1 - y0) * R.choice((0.45, 0.5, 0.55))
        ym = (y0 + y1) / 2
        if eixo == "x":
            V(a, u + 0.03, u + passo - 0.05, ym - h / 2, ym + h / 2, g0, g1, "escuro")
        else:
            V(a, g0, g1, ym - h / 2, ym + h / 2, u + 0.03, u + passo - 0.05, "escuro")


def azulejos(a: Area, eixo, plano, normal, ini, fim, y0, y1, base="azulejo_creme", faixa="azulejo_verde", falhas=6):
    """Parede de azulejos: painel de base, faixa colorida no alto, rodapé e falhas (azulejos caídos)."""
    def caixa(u0, u1, v0, v1, esp, mat):
        p0, p1 = (plano, plano + esp) if normal > 0 else (plano - esp, plano)
        if eixo == "x":
            V(a, u0, u1, v0, v1, p0, p1, mat)
        else:
            V(a, p0, p1, v0, v1, u0, u1, mat)
    # painéis de azulejo com textura (kit r2_estacao, 4 x 1 m, os últimos encolhidos) no lugar do bloco de base
    r = {("x", 1): 180, ("x", -1): 0, ("z", 1): -90, ("z", -1): 90}[(eixo, normal)]
    p = plano + 0.031 * normal
    u = ini
    while u < fim - 0.05:
        w = min(4.0, fim - u)
        v = y0
        while v < y1 - 0.05:
            h = min(1.0, y1 - v)
            cu = u + w / 2
            x, z = (cu, p) if eixo == "x" else (p, cu)
            peca = dict(m=base, x=r3(x), y=r3(v), z=r3(z), r=r)
            if w < 3.99 or h < 0.99:
                peca["e"] = [r3(w / 4.0), r3(h), 1]
            a.d["pecas"].append(peca)
            v += 1.0
        u += 4.0
    caixa(ini, fim, y1 - 0.5, y1 - 0.2, 0.045, faixa)
    caixa(ini, fim, y0, y0 + 0.15, 0.045, "concreto_escuro")
    for _ in range(falhas):
        u = R.uniform(ini + 0.5, fim - 1.5)
        v = R.uniform(y0 + 0.4, y1 - 1.0)
        caixa(u, u + R.choice((0.3, 0.6, 0.9)), v, v + R.choice((0.3, 0.6)), 0.05, "concreto_escuro")


# ====================================================================== Estação Aurora

def estacao() -> Area:
    a = Area("estacao_aurora", "Estação Aurora", "subsolo", "estacao", None, HX0, HX1 + W)
    a.d["zonaPadrao"] = "vila"
    a.d["kits"] = ["r2_estacao"]
    a.caixa((HX0, -27.0, HZ0 - W), (HX1 + W, -12.0, HZ1 + W))
    a.d["bocaDoPoco"] = dict(x=BOCA[0], y=Y0, z=BOCA[1])

    # --- piso: ilha no nível do duto e valas de trilhos 1 m abaixo
    B(a, HX0, HX1, Y_BASE, Y0, ILHA[0], ILHA[1], "chao")
    for z0, z1 in VALAS:
        B(a, HX0, HX1, Y_BASE, YV, z0, z1, "chao")
        # saída das valas: 3 degraus de 0,30 m nas duas pontas (o mais alto encosta na parede do fim)
        degraus(a, HX1 - 3 * 0.4, HX1, z0, z1, YV, Y0, "+x", base=YV)
        degraus(a, HX0, HX0 + 3 * 0.4, z0, z1, YV, Y0, "-x", base=YV)
    # faixas amarelas na borda da ilha e piso mais claro no meio
    V(a, HX0, HX1, Y0, Y0 + 0.02, ILHA[0] + 0.15, ILHA[0] + 0.45, "lona_amarela")
    V(a, HX0, HX1, Y0, Y0 + 0.02, ILHA[1] - 0.45, ILHA[1] - 0.15, "lona_amarela")
    V(a, HX0, HX1, YV - 0.02, Y0 - 0.02, ILHA[0] - 0.02, ILHA[0], "concreto_escuro")
    V(a, HX0, HX1, YV - 0.02, Y0 - 0.02, ILHA[1], ILHA[1] + 0.02, "concreto_escuro")

    # --- paredes e teto
    B(a, HX0 - W, HX1 + W, Y_BASE, YT + 0.6, HZ0 - W, HZ0, "concreto_escuro")
    B(a, HX0 - W, HX1 + W, Y_BASE, YT + 0.6, HZ1, HZ1 + W, "concreto_escuro")
    B(a, HX1, HX1 + W, Y_BASE, YT + 0.6, HZ0, HZ1, "concreto_escuro")
    # parede oeste: o trecho z 200..210 abaixo de -18,9 é a parede do fim do duto (com o portão)
    B(a, HX0 - W, HX0, Y_BASE, YT + 0.6, HZ0, 200.0, "concreto_escuro")
    B(a, HX0 - W, HX0, Y_BASE, YT + 0.6, 210.0, HZ1, "concreto_escuro")
    B(a, HX0 - W, HX0, TOPO_PAREDE_DUTO, YT + 0.6, 200.0, 210.0, "concreto_escuro")
    laje(a, HX0 - W, HX1 + W, HZ0 - W, HZ1 + W, YT, YT + 0.6, furos=[POCO_EXT], mat="concreto_escuro")
    # cambotas do teto e calhas de luz fluorescente (poucas acesas: luz fria e esparsa)
    x = HX0 + 3.0
    while x < HX1:
        V(a, x - 0.2, x + 0.2, YT - 0.5, YT, HZ0, HZ1, "concreto")
        x += 6.0
    for zl in (201.0, 209.0):
        x = HX0 + 6.0
        while x < HX1 - 2:
            if not (POCO_EXT[0] - 1 < x < POCO_EXT[1] + 1):
                acesa = R.random() < 0.22
                V(a, x - 0.75, x + 0.75, YT - 0.14, YT - 0.04, zl - 0.12, zl + 0.12, "luz_fria" if acesa else "escuro")
                V(a, x - 0.8, x + 0.8, YT - 0.05, YT, zl - 0.18, zl + 0.18, "metal")
            x += 6.0
    # uma calha caída, pendurada por um fio
    C(a, 150.6, YT - 1.6, 209.0, 1.5, 0.1, 0.24, "escuro", rz=38, semColisao=True)
    V(a, 150.0, 150.03, YT - 1.4, YT, 208.98, 209.02, "escuro")

    # --- azulejos nas paredes das valas (sul e norte) e na parede leste, placas com o nome da estação
    azulejos(a, "x", HZ0, +1, HX0, HX1, YV, YV + 4.2, falhas=14)
    azulejos(a, "x", HZ1, -1, HX0, HX1, YV, YV + 4.2, falhas=14)
    azulejos(a, "z", HX1, -1, ILHA[0], ILHA[1], Y0, Y0 + 3.2, base="azulejo_creme", falhas=4)
    for xp in (150.0, 166.0, 186.0):
        placa(LIXO, xp - 1.8, xp + 1.8, YV + 2.3, YV + 3.0, HZ0 + 0.04, +1)
        a.peca("placa_aurora", xp, YV + 2.3, HZ0 + 0.1, r=180)
    for xp in (178.0, 194.0):
        placa(LIXO, xp - 1.8, xp + 1.8, YV + 2.3, YV + 3.0, HZ1 - 0.04, -1)
        a.peca("placa_aurora", xp, YV + 2.3, HZ1 - 0.1)
    # painéis de horário apagados pendurados sob o mezanino, de frente para quem anda pela ilha
    for xp in (171.5, 190.0):
        a.peca("painel_horarios", xp, YM - 0.4 - 2.2, (ILHA[0] + ILHA[1]) / 2, r=90)
    # mapa da linha (desbotado) na parede leste
    V(a, HX1 - 0.05, HX1 - 0.02, Y0 + 1.2, Y0 + 2.4, 203.0, 207.0, "chapa_clara")
    V(a, HX1 - 0.07, HX1 - 0.05, Y0 + 1.75, Y0 + 1.85, 203.3, 206.7, "lona_vermelha")
    for zz in (203.6, 204.6, 205.6, 206.4):
        V(a, HX1 - 0.08, HX1 - 0.05, Y0 + 1.7, Y0 + 1.9, zz - 0.06, zz + 0.06, "escuro")

    trilhos(a)
    trem(a)
    escadas_rolantes(a)
    mezanino(a)
    detalhes_da_ilha(a)

    # --- luzes reais: poucas e frias (o resto são emissivos e a lanterna); vermelha na porta do poço
    a.luz(151.0, YT - 3.0, 205.0, FRIA_FRACA, 0.9, 22)
    a.luz(165.0, YT - 2.5, 205.0, FRIA, 0.9, 20, piscar=True)
    a.luz(191.0, YM + 3.8, 205.0, FRIA_FRACA, 0.8, 16)
    a.luz(176.85, Y0 + 3.4, 201.2, VERMELHA, 0.9, 9)

    a.entrada("inicio", 146.0, Y0)
    a.d["entradas"]["inicio"].update(z=205.0, yaw=rad(90))
    a.d["entradas"]["duto"] = dict(x=137.0, y=Y0, z=205.0, yaw=rad(90))
    a.d["entradas"]["mezanino"] = dict(x=190.0, y=YM, z=205.0, yaw=rad(270))
    a.d["entradas"]["poco"] = dict(x=XA, y=Y0, z=203.6, yaw=rad(0))
    return a


def trilhos(a: Area):
    """Lastro, dormentes e trilhos nas duas valas; poças."""
    for z0, z1 in VALAS:
        zc = (z0 + z1) / 2
        x_fim = TREM[0] - 0.5 if z0 > 205 else HX1 - 1.8
        V(a, HX0 + 1.8, x_fim, YV, YV + 0.06, zc - 1.4, zc + 1.4, "rocha")
        x = HX0 + 2.1
        while x < x_fim - 0.2:
            V(a, x - 0.12, x + 0.12, YV + 0.06, YV + 0.16, zc - 1.2, zc + 1.2, "madeira_escura")
            x += 0.75
        for dz in (-0.72, 0.72):
            V(a, HX0 + 1.8, x_fim, YV + 0.16, YV + 0.3, zc + dz - 0.04, zc + dz + 0.04, "metal")
        # trilho de energia (morto) junto à parede e para-choque no fim da vala
        zt = z0 + 0.35 if z0 < 205 else z1 - 0.35
        V(a, HX0 + 1.8, x_fim, YV + 0.2, YV + 0.32, zt - 0.08, zt + 0.08, "ferrugem")
        V(a, HX1 - 2.6, HX1 - 1.8, YV, YV + 0.9, zc - 1.0, zc + 1.0, "lona_amarela")
        V(a, HX1 - 2.62, HX1 - 2.58, YV + 0.3, YV + 0.6, zc - 1.0, zc + 1.0, "escuro")
    for xp, zp in ((156.0, 197.2), (183.0, 196.6), (192.0, 213.0)):
        V(a, xp - 1.2, xp + 1.5, YV + 0.07, YV + 0.08, zp - 0.6, zp + 0.8, "agua")


def trem(a: Area):
    """Trem abandonado na vala norte: caixa de metal com faixa, janelas escuras e portas emperradas."""
    x0, x1 = TREM
    z0, z1 = 211.45, 214.55
    yb = YV + 0.35
    B(a, x0, x1, yb, yb + 3.4, z0, z1, "metal")
    V(a, x0 - 0.02, x1 + 0.02, yb + 3.4, yb + 3.55, z0 + 0.2, z1 - 0.2, "concreto")       # teto
    V(a, x0, x1, yb + 1.05, yb + 1.35, z0 - 0.03, z0, "chapa_azul")                      # faixa
    V(a, x0 + 0.5, x1 - 0.5, yb - 0.35, yb, z0 + 0.4, z1 - 0.4, "escuro")                 # truques
    for x in (x0 + 2.0, x1 - 2.0):
        V(a, x - 1.2, x + 1.2, YV, yb + 0.1, z0 + 0.2, z1 - 0.2, "escuro")
    # janelas e portas na face da plataforma
    x = x0 + 1.2
    i = 0
    while x < x1 - 1.4:
        if i % 3 == 1:
            V(a, x, x + 1.4, yb + 0.3, yb + 2.6, z0 - 0.03, z0, "chapa_clara")      # porta
            V(a, x + 0.68, x + 0.72, yb + 0.3, yb + 2.6, z0 - 0.05, z0, "escuro")
            V(a, x + 0.15, x + 0.6, yb + 1.6, yb + 2.3, z0 - 0.05, z0, "escuro")
            V(a, x + 0.8, x + 1.25, yb + 1.6, yb + 2.3, z0 - 0.05, z0, "escuro")
        else:
            V(a, x, x + 1.4, yb + 1.55, yb + 2.5, z0 - 0.04, z0, "escuro")
        x += 1.8
        i += 1
    # cabine voltada para o oeste e o vidro quebrado
    V(a, x0 - 0.04, x0, yb + 1.6, yb + 2.7, z0 + 0.4, z1 - 0.4, "escuro")
    V(a, x0 - 0.06, x0, yb + 0.5, yb + 0.8, z0 + 0.5, z0 + 0.9, "vitral_vermelho")
    V(a, x0 - 0.06, x0, yb + 0.5, yb + 0.8, z1 - 0.9, z1 - 0.5, "vitral_vermelho")
    V(a, x1, x1 + 0.6, yb + 0.3, yb + 0.6, 212.6, 213.4, "metal")                       # engate


def escadas_rolantes(a: Area):
    """Duas escadas rolantes paradas, lado a lado, subindo para +x até o mezanino."""
    for z0, z1 in FAIXAS:
        V(a, ESC_X0 - 1.4, ESC_X0, Y0, Y0 + 0.03, z0, z1, "metal")                       # placa de piso
        V(a, ESC_X0 - 1.4, ESC_X0 - 1.32, Y0 + 0.03, Y0 + 0.05, z0, z1, "lona_amarela")
        for i in range(N_DEG):
            x = ESC_X0 + PIS * i
            topo = Y0 + DEG * (i + 1)
            B(a, x, x + PIS, Y0, topo, z0, z1, "metal")
            V(a, x, x + 0.05, topo, topo + 0.012, z0 + 0.03, z1 - 0.03, "lona_amarela")   # pente
            V(a, x + 0.1, x + 0.12, topo, topo + 0.01, z0 + 0.1, z1 - 0.1, "escuro")      # ranhuras
            V(a, x + 0.24, x + 0.26, topo, topo + 0.01, z0 + 0.1, z1 - 0.1, "escuro")
        V(a, ESC_X1, ESC_X1 + 1.2, YM, YM + 0.03, z0, z1, "metal")
    # balaustradas: painel lateral (blocos até perto dos degraus) e parapeito inclinado com corrimão.
    # Colisão só para o personagem (a câmera passa por cima).
    inc = DEG / PIS
    y_ini = Y0 + DEG + 1.0                       # topo do parapeito sobre o bico do primeiro degrau
    y_fim = y_ini + (ESC_X1 - ESC_X0) * inc
    for i, (z0, z1) in enumerate(BALAUSTRES):
        for k in range(N_DEG):
            x = ESC_X0 + PIS * k
            B(a, x, x + PIS, Y0, Y0 + DEG * (k + 1) - 0.2, z0, z1, "chapa_clara", semCamera=True, invisivel=True)
        faixa_x(a, ESC_X0, ESC_X1, z0, z1, y_ini, y_fim, 1.6, "chapa_clara", semCamera=True, invisivel=True)
        B(a, ESC_X0 - 0.8, ESC_X0, Y0, Y0 + 1.0, z0, z1, "chapa_clara", semCamera=True, invisivel=True)     # pé
        B(a, ESC_X1, ESC_X1 + 0.8, YM, YM + 1.0, z0, z1, "chapa_clara", semCamera=True, invisivel=True)     # cabeça
        # painel de inox, corrimão de borracha com as voltas e faixa de luz apagada (kit r2_estacao)
        a.peca("balaustrada_rolante", ESC_X0, Y0, (z0 + z1) / 2, e=[1, 1, r3((z1 - z0) / 0.34)])
    # placa "fora de serviço" e fita zebrada na boca de uma das escadas
    V(a, ESC_X0 - 1.0, ESC_X0 - 0.95, Y0 + 0.6, Y0 + 0.9, FAIXAS[1][0] + 0.1, FAIXAS[1][1] - 0.1, "lona_amarela")
    placa(a, FAIXAS[0][0] + 0.2, FAIXAS[0][1] - 0.2, Y0 + 1.5, Y0 + 1.9, ESC_X0 - 0.8, -1, eixo="z", mat="lona_vermelha", letras=False)


def mezanino(a: Area):
    """Mezanino em y = -19 sobre a ilha (x 168..201): ponto de descanso antes da subida."""
    z0, z1 = ILHA
    laje(a, MEZ_X0, HX1, z0, z1, YM - 0.4, YM, furos=[POCO_EXT], mat="chao")
    V(a, MEZ_X0, HX1, YM - 0.9, YM - 0.4, z0, z0 + 0.4, "concreto")       # vigas de borda
    V(a, MEZ_X0, HX1, YM - 0.9, YM - 0.4, z1 - 0.4, z1, "concreto")
    V(a, MEZ_X0, MEZ_X0 + 0.4, YM - 0.9, YM - 0.4, z0, z1, "concreto")
    for xc in (MEZ_X0 + 0.6, 186.0, 195.0):
        for zc in (z0 + 0.3, z1 - 0.3):
            B(a, xc - 0.3, xc + 0.3, Y0, YM - 0.4, zc - 0.3, zc + 0.3, "concreto")
            V(a, xc - 0.34, xc + 0.34, Y0, Y0 + 2.2, zc - 0.34, zc + 0.34, "azulejo_azul")
    corrimao(a, "x", z0, MEZ_X0, HX1, YM, lado=0.1)
    corrimao(a, "x", z1, MEZ_X0, HX1, YM, lado=-0.1)
    corrimao(a, "z", MEZ_X0, z0, z1, YM, lacunas=[(BALAUSTRES[0][0], BALAUSTRES[2][1])], lado=0.1)

    # bilheteria (cabine de chapa com guichês) e catracas
    B(a, 189.5, 194.5, YM, YM + 2.8, 202.0, 205.0, "chapa_azul")
    V(a, 189.48, 189.5, YM + 1.1, YM + 2.0, 202.4, 204.6, "escuro")
    V(a, 189.4, 189.5, YM + 1.0, YM + 1.1, 202.3, 204.7, "metal")
    V(a, 189.3, 194.7, YM + 2.8, YM + 3.1, 201.8, 205.2, "chapa_clara")
    placa(a, 190.0, 194.0, YM + 2.85, YM + 3.05, 201.78, -1)
    for zc in (206.2, 207.4, 208.6, 209.8):
        B(a, 186.3, 186.8, YM, YM + 1.0, zc - 0.15, zc + 0.15, "metal", semCamera=True)
        V(a, 186.35, 186.75, YM + 0.85, YM + 0.9, zc + 0.15, zc + 0.6, "escuro")          # braço da catraca
    # saída antiga para a rua: escadaria soterrada atrás de uma grade
    lance(a, 196.2, HX1, 205.5, 209.6, YM, YM + 3.0, "+x", base=YM)
    B(a, 195.6, 195.7, YM, YM + 2.2, 205.5, 209.6, "grade")
    V(a, 195.55, 195.6, YM + 1.0, YM + 1.2, 205.5, 209.6, "lona_amarela")
    V(a, 195.55, 195.6, YM + 1.6, YM + 1.8, 205.5, 209.6, "lona_amarela")
    for _ in range(14):
        cx, cz = R.uniform(197.5, 200.6), R.uniform(205.8, 209.3)
        cy = YM + (cx - 196.2) * 0.62 + R.uniform(0.2, 1.4)
        C(a, cx, cy, cz, R.uniform(0.6, 1.5), R.uniform(0.5, 1.2), R.uniform(0.6, 1.4), "rocha",
          ry=R.randint(0, 89), rx=R.uniform(-10, 10), rz=R.uniform(-10, 10), semColisao=True)
    V(a, 196.0, HX1, YM + 3.0, YT, 205.5, 209.6, "rocha_escura")
    placa(a, 196.4, 199.6, YM + 3.3, YM + 3.7, 205.48, -1, mat="chapa_clara")

    # bancos (ponto de descanso) e o acampamento de quem desce e sobe
    for xb, zb, frente in ((182.5, 209.9, -1), (185.5, 199.6, 1), (197.0, 199.6, 1), (191.0, 210.0, -1)):
        za, zf = (zb, zb + 0.5) if frente > 0 else (zb - 0.5, zb)
        B(a, xb, xb + 2.2, YM, YM + 0.45, za, zf, "madeira")
        encosto = (zf - 0.08, zf) if frente < 0 else (za, za + 0.08)
        V(a, xb, xb + 2.2, YM + 0.45, YM + 1.0, encosto[0], encosto[1], "madeira")
        for xp in (xb + 0.15, xb + 2.0):
            V(a, xp - 0.04, xp + 0.04, YM, YM + 0.45, za + 0.05, zf - 0.05, "metal")
    V(a, 186.0, 187.9, YM, YM + 0.12, 207.2, 208.1, "pano")                 # colchonete
    V(a, 186.1, 186.6, YM + 0.12, YM + 0.3, 207.3, 207.9, "lona_verde")     # mochila
    B(a, 188.4, 189.2, YM, YM + 0.6, 207.3, 208.1, "caixa")                 # caixote
    V(a, 188.65, 188.95, YM + 0.6, YM + 0.88, 207.55, 207.85, "luz_ambar")  # lampião
    B(a, 183.0, 183.7, YM, YM + 0.95, 206.4, 207.1, "chapa_azul")           # tambor de água
    V(a, 182.95, 183.75, YM + 0.95, YM + 1.0, 206.35, 207.15, "metal")
    V(a, 189.4, 190.6, YM, YM + 0.02, 206.9, 207.7, "escuro")               # cinzas da fogueira

    # painéis de horário apagados: pendurados no teto (mezanino e plataforma) e na parede do poço
    for xp, yp in ((183.0, YM + 3.3), (150.0, Y0 + 3.6), (163.0, Y0 + 3.6)):
        z = 205.0
        V(a, xp - 1.6, xp + 1.6, yp, yp + 0.8, z - 0.09, z + 0.09, "metal")
        V(a, xp - 1.5, xp + 1.5, yp + 0.08, yp + 0.72, z - 0.11, z + 0.11, "escuro")
        for k in range(3):
            V(a, xp - 1.35, xp - 0.1 - 0.25 * k, yp + 0.55 - 0.2 * k, yp + 0.6 - 0.2 * k, z - 0.12, z + 0.12, "concreto_escuro")
        for xx in (xp - 1.2, xp + 1.2):
            V(a, xx - 0.02, xx + 0.02, yp + 0.8, YT, z - 0.02, z + 0.02, "metal")


def detalhes_da_ilha(a: Area):
    """Colunas, bancos e entulho na plataforma; folhas do portão aberto; porta do poço."""
    z0, z1 = ILHA
    for xc in (147.0, 153.0):
        for zc in (z0 + 0.35, z1 - 0.35):
            B(a, xc - 0.35, xc + 0.35, Y0, YT, zc - 0.35, zc + 0.35, "concreto")
            V(a, xc - 0.39, xc + 0.39, Y0, Y0 + 2.2, zc - 0.39, zc + 0.39, "azulejo_azul")
            V(a, xc - 0.4, xc + 0.4, Y0 + 2.0, Y0 + 2.2, zc - 0.4, zc + 0.4, "azulejo_verde")
    # folhas do portão do duto, abertas para dentro da estação
    for zf in (PORTAO[0] - 0.15, PORTAO[1]):
        B(a, HX0, HX0 + 2.4, Y0, Y0 + 4.2, zf, zf + 0.15, "metal")
        for yy in (0.8, 2.2, 3.6):
            V(a, HX0, HX0 + 2.4, Y0 + yy, Y0 + yy + 0.25, zf - 0.02, zf + 0.17, "lona_amarela")
    placa(a, PORTAO[0] - 0.2, PORTAO[1] + 0.2, Y0 + 4.4, Y0 + 5.0, HX0 + 0.02, +1, eixo="z")
    # bancos da plataforma (um tombado) e entulho do teto
    for xb, zb in ((156.0, 199.8), (171.0, 210.0)):
        B(a, xb, xb + 2.2, Y0, Y0 + 0.45, zb, zb + 0.45, "madeira")
        V(a, xb, xb + 2.2, Y0 + 0.45, Y0 + 1.0, zb + (0.37 if zb < 205 else 0.0), zb + (0.45 if zb < 205 else 0.08), "madeira")
    C(a, 151.0, Y0 + 0.25, 207.6, 2.2, 0.45, 0.5, "madeira", ry=24, rz=80)
    for _ in range(7):
        C(a, R.uniform(143.5, 146.0), Y0 + R.uniform(0.15, 0.4), R.uniform(208.6, 210.3),
          R.uniform(0.4, 1.0), R.uniform(0.3, 0.7), R.uniform(0.4, 0.9), "rocha",
          ry=R.randint(0, 89), rx=R.uniform(-8, 8), rz=R.uniform(-8, 8))
    V(a, 145.0, 145.6, YT - 0.02, YT, 209.0, 209.9, "rocha_escura")       # buraco no teto acima
    V(a, 161.0, 163.2, Y0, Y0 + 0.012, 200.0, 201.5, "agua")
    V(a, 186.0, 188.5, Y0, Y0 + 0.012, 208.8, 210.4, "agua")
    # máquina de bilhetes e lixeira
    B(a, 143.2, 144.2, Y0, Y0 + 1.8, 199.1, 199.8, "chapa_verde")
    V(a, 143.4, 144.0, Y0 + 1.1, Y0 + 1.5, 199.78, 199.82, "escuro")
    B(a, 160.0, 160.5, Y0, Y0 + 0.8, 210.2, 210.7, "metal")
    # parede do poço vista do salão: azulejos azuis, painel de horário na face oeste e a porta (face sul)
    px0, px1, pz0, pz1 = POCO_EXT
    for eixo, plano, nrm, ini, fim in (("z", px0, -1, pz0, pz1), ("z", px1, 1, pz0, pz1), ("x", pz1, 1, px0, px1)):
        azulejos(a, eixo, plano, nrm, ini, fim, Y0, Y0 + 2.6, base="azulejo_azul", faixa="azulejo_creme", falhas=2)
        azulejos(a, eixo, plano, nrm, ini, fim, YM, YM + 2.6, base="azulejo_azul", faixa="azulejo_creme", falhas=1)
    azulejos(a, "x", pz0, -1, px0, PORTA_POCO[0], Y0, Y0 + 2.6, base="azulejo_azul", faixa="azulejo_creme", falhas=0)
    azulejos(a, "x", pz0, -1, PORTA_POCO[1], px1, Y0, Y0 + 2.6, base="azulejo_azul", faixa="azulejo_creme", falhas=1)
    azulejos(a, "x", pz0, -1, px0, px1, YM, YM + 2.6, base="azulejo_azul", faixa="azulejo_creme", falhas=1)
    V(a, px0 - 0.12, px0 - 0.02, Y0 + 2.7, Y0 + 3.5, 203.4, 206.6, "escuro")            # painel apagado
    V(a, px0 - 0.14, px0 - 0.12, Y0 + 2.65, Y0 + 3.55, 203.35, 206.65, "metal")
    # moldura da porta do poço, faixas de alerta e luz vermelha
    d0, d1 = PORTA_POCO
    V(a, d0 - 0.2, d0, Y0, Y0 + 2.8, pz0 - 0.1, pz0, "ferrugem")
    V(a, d1, d1 + 0.2, Y0, Y0 + 2.8, pz0 - 0.1, pz0, "ferrugem")
    V(a, d0 - 0.2, d1 + 0.2, Y0 + 2.6, Y0 + 2.8, pz0 - 0.1, pz0, "ferrugem")
    for k in range(6):
        u = d0 - 0.2 + k * (d1 - d0 + 0.4) / 6
        V(a, u, u + 0.2, Y0 + 2.62, Y0 + 2.78, pz0 - 0.12, pz0 - 0.1, "lona_amarela")
    V(a, (d0 + d1) / 2 - 0.15, (d0 + d1) / 2 + 0.15, Y0 + 2.95, Y0 + 3.2, pz0 - 0.2, pz0, "luz_alerta")
    placa(a, d0, d1, Y0 + 3.3, Y0 + 3.8, pz0, -1)
    V(a, d0 - 0.05, d1 + 0.05, Y0, Y0 + 0.012, pz0 - 1.2, pz0, "lona_amarela")


# ====================================================================== Boca do Poço

def boca() -> Area:
    a = Area("boca_estacao", "Boca do Poço", "subsolo", "boca", None, 171.0, 185.0)
    a.d["zonaPadrao"] = "vila"
    a.d["kits"] = ["r2_estacao", "r2_eclusa"]
    a.caixa((171.0, -12.0, 198.0), (185.0, 4.5, 222.0))
    poco(a)
    topo(a)
    a.entrada("inicio", XB, YP)
    a.d["entradas"]["inicio"].update(z=203.6, yaw=rad(270))
    a.d["entradas"]["superficie"] = dict(x=ENTRADA_SUPERFICIE[0], y=YP, z=ENTRADA_SUPERFICIE[1], yaw=rad(180))
    a.d["saidas"].append(dict(x=SAIDA_ECLUSA[0], y=YP, z=SAIDA_ECLUSA[1], destino="superficie_boca", entrada="boca",
                              rotulo="Abrir a eclusa", tipo="eclusa"))
    return a


def poco(a: Area):
    """Poço de 25 m: paredes, escada de mão em zigue-zague, patamares e o elevador de carga parado."""
    px0, px1, pz0, pz1 = POCO_EXT
    y_top = YP - 0.3
    d0, d1 = PORTA_POCO
    # paredes (a sul tem a porta para a ilha)
    B(a, px0, d0, Y0, y_top, pz0, PZ0, "concreto")
    B(a, d1, px1, Y0, y_top, pz0, PZ0, "concreto")
    B(a, d0, d1, Y0 + 2.6, y_top, pz0, PZ0, "concreto")
    B(a, px0, px1, Y0, y_top, PZ1, pz1, "concreto")
    B(a, px0, PX0, Y0, y_top, PZ0, PZ1, "concreto")
    B(a, PX1, px1, Y0, y_top, PZ0, PZ1, "concreto")
    zona_tunel(a, PX0, PX1, Y0 - 0.5, YP + 0.5, PZ0, PZ1)
    V(a, PX0, PX1, Y0, Y0 + 0.012, PZ0, PZ1, "concreto_escuro")         # mancha de óleo no fundo
    # lâmpadas de serviço gradeadas (frias) a cada 5 m na parede oeste e faixas vermelhas no fundo
    for yl in (Y0 + 3.2, -16.0, -9.5, -3.2):
        V(a, PX0, PX0 + 0.14, yl, yl + 0.35, 203.3, 203.5, "luz_fria")
        V(a, PX0, PX0 + 0.18, yl - 0.05, yl + 0.4, 203.25, 203.27, "grade")
    V(a, PX1 - 0.06, PX1, Y0 + 2.7, Y0 + 2.85, PZ0 + 0.3, PZ1 - 0.3, "luz_alerta")

    # espinha (coluna central) em trechos: cada escada se apoia nela e sai por cima no patamar
    s0, s1 = ESP_Z
    xm = (XA + XB) / 2
    B(a, PX0, xm, Y0, PATAMARES[0], s0, s1, "concreto")                  # A
    B(a, xm, LADO, Y0, PATAMARES[1], s0, s1, "concreto")                 # sustenta o patamar 1 e B
    B(a, PX0, xm, PATAMARES[1], PATAMARES[2], s0, s1, "concreto")        # C
    B(a, xm, LADO, PATAMARES[2], y_top, s0, s1, "concreto")              # D
    # patamares alternados: norte (1 e 3) e sul (2); o topo cobre a metade sul
    e = 0.3
    for y, (z0, z1) in zip(PATAMARES, ((s0, PZ1), (PZ0, s1), (s0, PZ1))):
        B(a, PX0, LADO, y - e, y, z0, z1, "plataforma")
        V(a, PX0, LADO, y - e - 0.3, y - e, (z0 + z1) / 2 - 0.12, (z0 + z1) / 2 + 0.12, "ferrugem")
        corrimao(a, "z", LADO, z0, z1, y, lado=-0.1)
        V(a, PX0, PX0 + 0.06, y + 2.3, y + 2.45, z0 + 0.3, z1 - 0.3, "luz_alerta")   # faixa de alerta
        V(a, PX0 + 0.4, LADO - 0.4, y + 2.3, y + 2.45, (PZ1 - 0.06) if z1 == PZ1 else PZ0, PZ1 if z1 == PZ1 else (PZ0 + 0.06), "luz_alerta")
    # escadas de mão (yaw: para onde o jogador olha ao subir)
    ys = (Y0,) + PATAMARES + (YP,)
    for i in range(4):
        if i % 2 == 0:
            a.d["escadas"].append(dict(x=XA, z=r3(s0 - 0.05), y0=ys[i], y1=ys[i + 1], tipo="escada", yaw=0))
        else:
            a.d["escadas"].append(dict(x=XB, z=r3(s1 + 0.05), y0=ys[i], y1=ys[i + 1], tipo="escada", yaw=180))
    # placas com a altura em cada patamar
    for y, zc in zip(PATAMARES, (PZ1, PZ0, PZ1)):
        nrm = -1 if zc == PZ1 else 1
        placa(a, PX0 + 0.3, PX0 + 1.2, y + 1.4, y + 1.8, zc, nrm, mat="lona_amarela")

    # canos, eletrodutos e grampos nas paredes
    for xc, mat in ((175.8, "metal"), (176.1, "ferrugem")):
        V(a, xc - 0.06, xc + 0.06, Y0, YP + 3.0, PZ1 - 0.16, PZ1 - 0.04, mat)
    V(a, PX0 + 0.02, PX0 + 0.12, Y0, YP + 3.0, 203.0, 203.08, "escuro")
    y = Y0 + 1.5
    while y < YP:
        V(a, 175.6, 176.3, y, y + 0.05, PZ1 - 0.2, PZ1 - 0.02, "ferrugem")
        y += 2.5

    # elevador de carga (lado leste), parado no fundo: gaiola fechada, trilhos-guia, cabos e contrapeso
    gx0, gx1, gz0, gz1 = LADO + 0.2, PX1 - 0.2, PZ0 + 0.4, PZ1 - 0.4
    B(a, gx0, gx1, Y0, Y0 + 0.2, gz0, gz1, "grade")
    for xx in (gx0, gx1 - 0.1):
        for zz in (gz0, gz1 - 0.1):
            V(a, xx, xx + 0.1, Y0 + 0.2, Y0 + 2.6, zz, zz + 0.1, "ferrugem")
    B(a, gx0, gx0 + 0.06, Y0 + 0.2, Y0 + 2.5, gz0, gz1, "grade")         # porta pantográfica
    B(a, gx0, gx1, Y0 + 0.2, Y0 + 2.5, gz0, gz0 + 0.06, "grade")
    B(a, gx0, gx1, Y0 + 0.2, Y0 + 2.5, gz1 - 0.06, gz1, "grade")
    V(a, gx0, gx1, Y0 + 2.5, Y0 + 2.65, gz0, gz1, "ferrugem")            # teto da gaiola
    for k in range(5):
        V(a, gx0 - 0.03, gx0, Y0 + 0.2 + k * 0.55, Y0 + 0.3 + k * 0.55, gz0, gz1, "lona_amarela")
    V(a, gx0 + 0.5, gx1 - 0.5, Y0 + 0.2, Y0 + 1.0, gz0 + 0.4, gz0 + 1.4, "caixa")   # carga esquecida
    for zz in (gz0 + 0.3, gz1 - 0.4):
        V(a, PX1 - 0.12, PX1, Y0, YP + 3.1, zz, zz + 0.1, "metal")         # trilhos-guia
    xc = (gx0 + gx1) / 2
    for dz in (-0.12, 0.12):
        V(a, xc - 0.02, xc + 0.02, Y0 + 2.65, YP + 3.0, BOCA[1] + dz - 0.02, BOCA[1] + dz + 0.02, "escuro")
    V(a, PX1 - 0.5, PX1 - 0.15, -9.0, -7.6, PZ1 - 0.9, PZ1 - 0.3, "concreto_escuro")   # contrapeso
    V(a, PX1 - 0.34, PX1 - 0.31, -7.6, YP + 3.0, PZ1 - 0.62, PZ1 - 0.58, "escuro")
    # botoeira no fundo (apagada) e aviso
    V(a, PX0 + 0.02, PX0 + 0.1, Y0 + 1.1, Y0 + 1.6, 203.6, 203.9, "chapa_clara")
    V(a, PX0 + 0.1, PX0 + 0.12, Y0 + 1.4, Y0 + 1.5, 203.7, 203.8, "vitral_vermelho")
    a.luz(176.9, -12.5 + 2.6, 206.6, VERMELHA, 0.8, 14)


def topo(a: Area):
    """Topo do poço (y = 0): casa do poço, descontaminação e eclusa com duas portas."""
    sx0, sx1, sz0, sz1 = SALA
    dx0, dx1, dz0, dz1 = DESC
    ex0, ex1, ez0, ez1 = ECL
    # descontaminação e câmara da eclusa: 6 m de largura e 3,5 m de pé-direito, câmera de túnel
    zona_tunel(a, dx0, dx1, YP - 0.5, YP + ALT_T, dz0 - 0.5, ez1 + 0.5)
    pe = 0.5
    # piso com o vão do poço (metade norte do lado da escada e todo o lado do elevador)
    furos = [(PX0, LADO, ESP_Z[1], PZ1), (LADO, PX1, PZ0, PZ1)]
    laje(a, sx0 - pe, sx1 + pe, sz0 - pe, sz1 + pe, YP - 0.3, YP, furos=furos, mat="chao")
    B(a, dx0 - pe, dx1 + pe, YP - 0.3, YP, sz1 + pe, ez1 + 1.0, "chao")
    # paredes da casa do poço
    h = YP + ALT_T
    B(a, sx0 - pe, sx1 + pe, YP, h, sz0 - pe, sz0, "concreto")
    B(a, sx0 - pe, sx0, YP, h, sz0, sz1 + pe, "concreto")
    B(a, sx1, sx1 + pe, YP, h, sz0, sz1 + pe, "concreto")
    B(a, sx0, 176.5, YP, h, sz1, sz1 + pe, "concreto")
    B(a, 179.5, sx1, YP, h, sz1, sz1 + pe, "concreto")
    B(a, 176.5, 179.5, YP + 2.8, h, sz1, sz1 + pe, "concreto")
    # descontaminação e eclusa
    B(a, dx0 - pe, dx0, YP, h, dz0, ez1, "concreto")
    B(a, dx1, dx1 + pe, YP, h, dz0, ez1, "concreto")
    B(a, dx0 - pe, 176.7, YP, h, dz1, ez0, "concreto")                   # porta interna da eclusa
    B(a, 179.3, dx1 + pe, YP, h, dz1, ez0, "concreto")
    B(a, 176.7, 179.3, YP + 2.6, h, dz1, ez0, "concreto")
    B(a, dx0 - pe, dx1 + pe, YP - 0.3, h, ez1, ez1 + 1.0, "concreto")    # porta externa (fechada)
    a.peca("porta_eclusa_r2", (dx0 + dx1) / 2, YP, ez1)                   # porta redonda com volante (kit)
    # teto
    B(a, sx0 - pe, sx1 + pe, h, h + 0.4, sz0 - pe, sz1 + pe, "concreto_escuro")
    B(a, dx0 - pe, dx1 + pe, h, h + 0.4, sz1 + pe, ez1 + 1.0, "concreto_escuro")

    # guarda-corpos em volta do vão do poço (vão no topo da escada D)
    corrimao(a, "x", ESP_Z[1], PX0, LADO, YP, lacunas=[(XB - 0.5, XB + 0.5)], lado=-0.1)
    corrimao(a, "z", LADO, PZ0, ESP_Z[1], YP, lado=-0.1)
    corrimao(a, "x", PZ0, LADO, PX1, YP, lado=-0.1)
    corrimao(a, "x", PZ1, PX0, PX1, YP, lado=0.1)
    corrimao(a, "z", PX0, ESP_Z[1], PZ1, YP, lado=-0.1)
    corrimao(a, "z", PX1, PZ0, PZ1, YP, lado=0.1)
    V(a, PX0 - 0.3, PX1 + 0.3, YP, YP + 0.02, PZ1, PZ1 + 0.3, "lona_amarela")
    V(a, PX1, PX1 + 0.3, YP, YP + 0.02, PZ0 - 0.3, PZ1 + 0.3, "lona_amarela")
    # guincho do elevador: viga sobre o vão, polia e motor
    V(a, LADO, PX1 + 0.5, h - 0.4, h - 0.1, BOCA[1] - 0.15, BOCA[1] + 0.15, "ferrugem")
    V(a, 179.1, 179.7, h - 0.9, h - 0.4, BOCA[1] - 0.3, BOCA[1] + 0.3, "metal")
    B(a, 181.4, 183.6, YP, YP + 1.3, 203.4, 205.6, "chapa_verde")
    V(a, 181.6, 183.4, YP + 1.3, YP + 1.6, 204.0, 205.0, "metal")
    V(a, 180.5, 181.4, YP + 1.2, YP + 1.26, BOCA[1] - 0.03, BOCA[1] + 0.03, "escuro")
    V(a, 183.55, 183.6, YP + 0.7, YP + 0.9, 204.2, 204.4, "vitral_vermelho")

    # armários de EPI na parede oeste (um aberto, com a roupa e a máscara) e bancos
    for i in range(6):
        z = 202.8 + i * 1.0
        B(a, sx0, sx0 + 0.6, YP, YP + 2.1, z, z + 0.95, "chapa_verde" if i % 2 else "chapa_azul", invisivel=True)
        # armário do kit (respiros, puxador; o terceiro aberto, com a roupa de EPI e a máscara)
        nome = "armario_epi_aberto" if i == 2 else ("armario_epi_verde" if i % 2 else "armario_epi_azul")
        a.peca(nome, sx0 + 0.3, YP, z + 0.475, r=-90)
    B(a, 176.0, 181.0, YP, YP + 0.45, sz0 + 0.1, sz0 + 0.6, "madeira")                     # banco
    for xp in (176.2, 180.8):
        V(a, xp - 0.04, xp + 0.04, YP, YP + 0.45, sz0 + 0.15, sz0 + 0.55, "metal")
    # suporte de máscaras e filtros na parede leste
    for k in range(4):
        zc = 206.6 + k * 0.8
        V(a, sx1 - 0.25, sx1, YP + 1.55, YP + 1.62, zc - 0.03, zc + 0.03, "metal")
        V(a, sx1 - 0.35, sx1 - 0.1, YP + 1.2, YP + 1.55, zc - 0.18, zc + 0.18, "escuro")
        V(a, sx1 - 0.3, sx1 - 0.15, YP + 1.0, YP + 1.2, zc - 0.08, zc + 0.08, "lona_amarela")
    placa(a, 173.5, 176.0, YP + 2.5, YP + 2.9, sz0, +1, mat="lona_vermelha")
    placa(a, 180.5, 183.5, YP + 2.5, YP + 2.9, sz0, +1)
    # porta da descontaminação: moldura, faixas e giroflex
    V(a, 176.3, 176.5, YP, YP + 3.0, sz1 - 0.1, sz1, "ferrugem")
    V(a, 179.5, 179.7, YP, YP + 3.0, sz1 - 0.1, sz1, "ferrugem")
    V(a, 176.3, 179.7, YP + 2.8, YP + 3.0, sz1 - 0.1, sz1, "ferrugem")
    V(a, 177.8, 178.2, YP + 3.05, YP + 3.3, sz1 - 0.25, sz1, "luz_alerta")
    placa(a, 180.0, 182.4, YP + 1.8, YP + 2.3, sz1, -1, mat="lona_amarela")

    # descontaminação: azulejos claros, chuveiros nas duas paredes, ralos e névoa
    azulejos(a, "z", dx0, +1, dz0, dz1, YP, YP + 2.4, falhas=2)
    azulejos(a, "z", dx1, -1, dz0, dz1, YP, YP + 2.4, falhas=2)
    for xw, s in ((dx0, 1), (dx1, -1)):
        V(a, min(xw, xw + 0.12 * s), max(xw, xw + 0.12 * s), YP + 2.7, YP + 2.82, dz0 + 0.1, dz1 - 0.1, "metal")
        for zc in (211.6, 213.25, 214.9):
            a.peca("chuveiro_r2", xw, YP, zc, r=-90 if s > 0 else 90)        # cano, crivo e registro (kit)
        V(a, min(xw, xw + 0.04 * s), max(xw, xw + 0.04 * s), YP + 2.95, YP + 3.05, dz0 + 0.5, dz1 - 0.5, "luz_alerta")
    for zc in (211.6, 213.25, 214.9):
        V(a, 177.4, 178.6, YP, YP + 0.015, zc - 0.4, zc + 0.4, "grade")
    V(a, dx0, dx1, YP, YP + 0.01, dz0, dz1, "azulejo_creme")
    for k, y in enumerate((0.35, 1.1)):
        V(a, dx0 + 0.05, dx1 - 0.05, YP + 0.02, YP + y, dz0 + 0.4 + 0.4 * k, dz1 - 0.3 - 0.4 * k, "nevoa")

    # eclusa: câmara com a porta interna aberta (folha recolhida) e a externa fechada
    V(a, 179.3, 179.75, YP, YP + 2.6, dz1 + 0.1, ez0 - 0.1, "metal")                 # folha interna recolhida
    for xx in (176.5, 179.3):
        V(a, xx, xx + 0.2, YP, YP + 2.8, ez0, ez0 + 0.1, "ferrugem")
    V(a, 176.5, 179.5, YP + 2.6, YP + 2.8, ez0, ez0 + 0.1, "ferrugem")
    for k in range(7):
        u = 176.5 + k * 0.43
        V(a, u, u + 0.22, YP + 2.62, YP + 2.78, ez0 + 0.1, ez0 + 0.12, "lona_amarela")
    zf = ez1
    V(a, 176.0, 180.0, YP, YP + 3.1, zf - 0.2, zf, "ferrugem")                       # moldura
    V(a, 176.4, 179.6, YP + 0.1, YP + 2.8, zf - 0.32, zf - 0.2, "metal")              # folha
    V(a, 177.6, 178.4, YP + 1.1, YP + 1.9, zf - 0.42, zf - 0.32, "escuro")            # volante
    V(a, 177.96, 178.04, YP + 0.95, YP + 2.05, zf - 0.45, zf - 0.42, "ferrugem")
    V(a, 177.45, 178.55, YP + 1.46, YP + 1.54, zf - 0.45, zf - 0.42, "ferrugem")
    for k in range(8):
        u = 176.4 + k * 0.4
        V(a, u, u + 0.2, YP + 0.1, YP + 0.4, zf - 0.34, zf - 0.32, "lona_amarela")
        V(a, u + 0.2, u + 0.4, YP + 0.1, YP + 0.4, zf - 0.34, zf - 0.32, "escuro")
    V(a, 177.7, 178.3, YP + 3.15, YP + 3.4, zf - 0.3, zf, "luz_alerta")               # giroflex
    V(a, ex1 - 0.1, ex1, YP + 1.0, YP + 1.8, 218.6, 219.4, "chapa_clara")              # painel de comando
    V(a, ex1 - 0.13, ex1 - 0.1, YP + 1.55, YP + 1.65, 218.8, 218.95, "vitral_verde")
    V(a, ex1 - 0.13, ex1 - 0.1, YP + 1.55, YP + 1.65, 219.05, 219.2, "vitral_vermelho")
    placa(a, 217.0, 218.6, YP + 1.8, YP + 2.3, ex0, +1, eixo="z", mat="lona_amarela")
    V(a, ex0 + 0.5, ex1 - 0.5, YP, YP + 0.012, zf - 1.3, zf - 0.5, "lona_amarela")
    V(a, ex0 + 0.05, ex1 - 0.05, YP + 0.02, YP + 0.45, ez0 + 0.3, ez1 - 0.6, "nevoa")

    # luzes reais: vermelhas de alerta (sala, chuveiros, eclusa)
    a.luz(178.0, h - 0.5, 200.6, VERMELHA, 0.8, 12)
    a.luz(178.0, h - 0.5, 213.2, VERMELHA, 0.9, 10)
    a.luz(178.0, h - 0.6, 218.4, VERMELHA, 1.0, 9, piscar=True)


# ====================================================================== superfície provisória

def superficie_provisoria():
    """Stub de `superficie_boca` (mundo "superficie_aberta") só se o arquivo ainda não existir: a tarefa
    da superfície (fase 2, tarefa 5) o substitui. Chão de 40 x 40 m, entrada "boca" e a eclusa de volta."""
    caminho = os.path.join(DESTINO, "superficie_boca.json")
    if os.path.exists(caminho):
        return None
    a = Area("superficie_boca", "Boca do Poço", "superficie_aberta", "superficie", None, -20.0, 20.0, superficie=True)
    a.d["zonaPadrao"] = "superficie"
    a.caixa((-20.0, -2.0, -20.0), (20.0, 10.0, 20.0))
    B(a, -20.0, 20.0, -0.5, 0.0, -20.0, 20.0, "chao")
    B(a, -2.0, 2.0, 0.0, 2.6, -3.0, -0.6, "concreto")          # casa da eclusa (provisória)
    V(a, -0.9, 0.9, 0.0, 2.2, -0.62, -0.58, "metal")
    a.entrada("boca", 0.0, 0.0)
    a.d["entradas"]["boca"].update(z=3.0, yaw=rad(0))
    a.d["saidas"].append(dict(x=0.0, y=0.0, z=0.4, destino="boca_estacao", entrada="superficie",
                              rotulo="Entrar na eclusa", tipo="eclusa"))
    return a


def todas():
    lista = [estacao(), boca()]
    stub = superficie_provisoria()
    if stub:
        lista.append(stub)
    from sinalizacao import sinalizar
    return sinalizar(lista)


if __name__ == "__main__":
    for area in todas():
        area.salvar()
