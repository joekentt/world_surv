"""Kits de decoração da revisão 2: um GLB por estética em public/assets/kits/r2_<estetica>.glb.

Uso: /opt/bpyenv/bin/python tools/blender/kits/kits_r2.py [r2_cisterna ...]   (sem argumentos gera todos)

As peças vestem a geometria de blocos das áreas 3D (tools/areas/subsolo_*.py e superficie.py): os geradores
das áreas colocam cada módulo pelo nome (campo `pecas`, com `kits` na área) e deixam invisíveis os blocos que
a peça substitui, mantendo a colisão. Elementos de identidade da seção 7 de docs/spec/07-arte-personagens-vila.md.

Eixos no Blender: X = X do jogo, Y = Z do jogo (norte), Z = para cima. Origem de cada módulo no chão, salvo
indicação. Triângulos moderados (o jogo instancia as peças: uma chamada de desenho por malha-fonte).
Utilidades (novo, fechar, juntar, mat, texto) vêm de gerar_kits.py, o gerador dos kits da revisão 1.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy  # noqa: E402  (antes de bmesh no módulo bpy do PyPI)
import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

import comum  # noqa: E402
from gerar_kits import M, SAIDA, fechar, juntar, novo, texto  # noqa: E402
from gerar_kits import mat as _mat  # noqa: E402

R = comum.semente(2026)


# ------------------------------------------------------------------ utilidades

def mat(nome, cor, rug=0.8, metal=0.0, emissao=None, forca=0.0, alfa=1.0):
    """Material com metalicidade baixa: o jogo não tem mapa de ambiente, e metal puro sem reflexo fica preto."""
    return _mat(nome, cor, max(0.5, rug), min(metal, 0.15), emissao, forca, alfa)


def girar(bm, verts, ang, eixo, centro=(0, 0, 0)):
    bmesh.ops.rotate(bm, verts=verts, cent=centro, matrix=Matrix.Rotation(ang, 3, eixo))


def pano(nome, largura, prof, nx, ny, altura, caimento, inclinacao=0.0, ondas=0.03, material=None, franja=0.0):
    """Lona ou tecido: grade em XY na altura dada, com barriga no meio (caimento), inclinada para -Y e
    uma franja caída na borda da frente."""
    _, bm = novo(nome)
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5, matrix=Matrix.Diagonal((largura, prof, 1, 1)))
    for v in bm.verts:
        u, w = v.co.x / largura + 0.5, v.co.y / prof + 0.5
        v.co.z = altura - caimento * math.sin(math.pi * u) * math.sin(math.pi * w) - inclinacao * (0.5 - w) * 2 \
            + ondas * noise.noise(Vector((v.co.x * 1.7, v.co.y * 1.7, 0.3)))
    if franja:
        borda = [e for e in bm.edges if all(abs(v.co.y + prof / 2) < 1e-4 for v in e.verts)]
        ext = bmesh.ops.extrude_edge_only(bm, edges=borda)
        novos = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in novos:
            v.co.z -= franja
            v.co.y -= 0.03
    return fechar(nome, bm, material, oclusao=0, forca_sujeira=0.5, suave=60)


def viga_i(bm, centro, comp, eixo="Z", alt=0.24, larg=0.16, alma=0.02, aba=0.02):
    """Perfil I: duas abas e a alma, ao longo do eixo dado (comprimento comp)."""
    cx, cy, cz = centro
    if eixo == "Z":
        comum.caixa(bm, (cx, cy - alt / 2 + aba / 2, cz), (larg, aba, comp))
        comum.caixa(bm, (cx, cy + alt / 2 - aba / 2, cz), (larg, aba, comp))
        comum.caixa(bm, (cx, cy, cz), (alma, alt, comp))
    elif eixo == "X":
        comum.caixa(bm, (cx, cy, cz - alt / 2 + aba / 2), (comp, larg, aba))
        comum.caixa(bm, (cx, cy, cz + alt / 2 - aba / 2), (comp, larg, aba))
        comum.caixa(bm, (cx, cy, cz), (comp, alma, alt))
    else:
        comum.caixa(bm, (cx, cy, cz - alt / 2 + aba / 2), (larg, comp, aba))
        comum.caixa(bm, (cx, cy, cz + alt / 2 - aba / 2), (larg, comp, aba))
        comum.caixa(bm, (cx, cy, cz), (alma, comp, alt))


def tubo(bm, a, b, raio, seg=8):
    """Cilindro de a até b."""
    va, vb = Vector(a), Vector(b)
    d = vb - va
    verts = comum.cilindro(bm, (0, 0, 0), raio, d.length, seg)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bmesh.ops.transform(bm, verts=verts, matrix=Matrix.Translation((va + vb) / 2) @ rot)
    return verts


def catenaria(bm, x0, x1, y, z, flecha, raio, n=12):
    pts = [(x0 + (x1 - x0) * i / n, y, z - flecha * (1 - (2 * i / n - 1) ** 2)) for i in range(n + 1)]
    for p, q in zip(pts, pts[1:]):
        tubo(bm, p, q, raio, 5)
    return pts


# ------------------------------------------------------------------ Praça do Reservatório

LONAS = {"a": ("lona_vermelha_r2", (0.62, 0.2, 0.13)), "b": ("lona_azul_r2", (0.18, 0.32, 0.55)),
         "c": ("lona_amarela_r2", (0.76, 0.58, 0.2)), "d": ("lona_verde_r2", (0.24, 0.45, 0.27))}


def kit_cisterna():
    objs = []
    concreto = mat("concreto_reservatorio", (0.74, 0.71, 0.65), 0.85)
    madeira = mat("madeira_r2", (0.46, 0.32, 0.2), 0.85)

    # coluna do reservatório: fuste de 1,2 m chanfrado, sapata, anéis de concreto, capitel em tronco de
    # pirâmide até o teto (25 m) e a marca d'água antiga escura até 2,2 m
    n, bm = novo("coluna_reservatorio")
    comum.caixa(bm, (0, 0, 12.5), (1.2, 1.2, 25.0))
    comum.caixa(bm, (0, 0, 0.3), (1.7, 1.7, 0.6))
    for z in (6.0, 12.0, 18.0):
        comum.caixa(bm, (0, 0, z), (1.32, 1.32, 0.18))
    v = comum.cilindro(bm, (0, 0, 24.1), 0.85, 1.8, 4, raio_topo=1.55)
    girar(bm, v, math.pi / 4, "Z")
    o1 = fechar(n, bm, concreto, bisel=0.04, ruido=0.02, escala_ruido=1.1, sujeira=(0.5, 0.52, 0.45), forca_sujeira=0.7)
    _, bm = novo("marca_agua")
    comum.caixa(bm, (0, 0, 1.25), (1.215, 1.215, 1.9))
    for k in range(4):  # escorridos verticais
        v = comum.caixa(bm, (R.uniform(-0.4, 0.4), -0.61, 2.2 + k * 0.8), (0.08, 0.01, R.uniform(1.0, 3.0)))
        girar(bm, v, k * math.pi / 2, "Z")
    o2 = fechar("marca_agua", bm, mat("concreto_umido_r2", (0.3, 0.3, 0.26), 0.55), oclusao=0, forca_sujeira=0.6)
    objs.append(juntar(n, [o1, o2]))

    # bancas do mercado de lonas (3,4 x 3 m): postes, balcão de tábuas, lona com barriga e franja,
    # mercadoria (caixotes, sacos, potes)
    for letra, (nome_mat, cor) in LONAS.items():
        n, bm = novo(f"banca_mercado_{letra}")
        for px in (-1.45, 1.45):
            for py in (-1.2, 1.2):
                comum.caixa(bm, (px, py, 1.3), (0.09, 0.09, 2.6 if py > 0 else 2.35))
        comum.caixa(bm, (0, 0, 0.47), (2.6, 1.0, 0.06))
        comum.caixa(bm, (0, 0, 0.93), (2.7, 1.05, 0.05))
        for i in range(6):
            comum.caixa(bm, (-1.08 + i * 0.43, -0.5, 0.47), (0.4, 0.04, 0.92))
        comum.caixa(bm, (0, 1.2, 2.45), (3.0, 0.07, 0.07))
        comum.caixa(bm, (0, -1.2, 2.2), (3.0, 0.07, 0.07))
        o1 = fechar(n + "_estr", bm, madeira, bisel=0.01, sujeira=(0.3, 0.24, 0.18), forca_sujeira=0.8)
        o2 = pano(n + "_lona", 3.5, 3.1, 8, 6, 2.55, 0.16, inclinacao=0.18, material=mat(nome_mat, cor, 0.95), franja=0.35)
        _, bm = novo(n + "_merc")
        for i in range(3):
            comum.caixa(bm, (-0.9 + i * 0.9, 0.1, 1.1), (0.55, 0.45, 0.3))
        o3 = fechar(n + "_merc", bm, mat("caixote_r2", (0.55, 0.42, 0.28), 0.9), bisel=0.01, oclusao=0)
        _, bm = novo(n + "_sacos")
        for i in range(4):
            comum.esfera(bm, (-1.1 + i * 0.7, 0.55, 0.25), 0.28, 8, 6)
        for i in range(4):
            comum.cilindro(bm, (0.45 + i * 0.18, -0.25, 1.05), 0.07, 0.2, 8)
        o4 = fechar(n + "_sacos", bm, mat("saco_r2", (0.62, 0.55, 0.42), 0.95), ruido=0.04, oclusao=0)
        for v in o4.data.vertices:
            if v.co.z < 0.5:
                v.co.z = max(0.0, v.co.z * 0.8)
        objs.append(juntar(n, [o1, o2, o3, o4]))

    # lonas grandes do mercado entre colunas (10,8 x 6 m, a 4,25 m), com cordas até as colunas
    for letra in ("a", "b", "c"):
        nome_mat, cor = LONAS[letra]
        n = f"lona_mercado_{letra}"
        o1 = pano(n, 10.8, 6.0, 12, 8, 4.3, 0.55, ondas=0.06, material=mat(nome_mat, cor, 0.95))
        _, bm = novo(n + "_cordas")
        for x in (-5.4, 5.4):
            for y in (-3.0, 3.0):
                tubo(bm, (x, y, 4.3), (math.copysign(5.4, x) + math.copysign(0.1, x), math.copysign(0.6, y), 4.6), 0.015, 4)
        o2 = fechar(n + "_cordas", bm, mat("corda_r2", (0.5, 0.42, 0.3), 0.9), oclusao=0)
        objs.append(juntar(n, [o1, o2]))

    # varal de 12 m (a 3,4 m) com roupas de cores e formatos variados
    n, bm = novo("varal_12")
    pts = catenaria(bm, -5.6, 5.6, 0, 3.4, 0.35, 0.012, 14)
    o1 = fechar(n + "_corda", bm, mat("corda_r2", (0.5, 0.42, 0.3), 0.9), oclusao=0)
    partes = [o1]
    cores = [(0.62, 0.2, 0.13), (0.2, 0.32, 0.5), (0.7, 0.62, 0.48), (0.42, 0.5, 0.3), (0.55, 0.45, 0.6), (0.75, 0.7, 0.6)]
    for i in range(8):
        x = -4.9 + i * 1.4 + R.uniform(-0.15, 0.15)
        zc = 3.4 - 0.35 * (1 - (x / 5.6) ** 2)
        _, bm = novo(f"roupa{i}")
        tipo = i % 3
        if tipo == 0:   # camisa: corpo e mangas
            comum.caixa(bm, (x, 0, zc - 0.38), (0.5, 0.02, 0.7))
            comum.caixa(bm, (x, 0, zc - 0.12), (0.95, 0.02, 0.2))
        elif tipo == 1:  # calça: duas pernas
            for dx in (-0.12, 0.12):
                comum.caixa(bm, (x + dx, 0, zc - 0.5), (0.2, 0.02, 0.95))
            comum.caixa(bm, (x, 0, zc - 0.06), (0.46, 0.02, 0.12))
        else:            # pano
            comum.caixa(bm, (x, 0, zc - 0.3), (0.65, 0.02, 0.6))
        o = fechar(f"roupa{i}", bm, mat(f"roupa_r2_{i % 6}", cores[i % 6], 0.95), ruido=0.03, escala_ruido=3, oclusao=0, forca_sujeira=0.4)
        partes.append(o)
    objs.append(juntar(n, partes))

    # bomba d'água (origem no centro da base, 6 x 5 m): caldeira rebitada, volante com raios, bielas,
    # cano de recalque até o teto (25 m) com flanges e braçadeiras, cocho e tambores
    n, bm = novo("bomba_dagua")
    comum.caixa(bm, (0, 0, 0.5), (6.0, 5.0, 1.0))
    comum.caixa(bm, (4.25, 0, 0.35), (2.5, 1.6, 0.7))
    o_base = fechar(n + "_base", bm, concreto, bisel=0.03, ruido=0.02, sujeira=(0.28, 0.33, 0.27), forca_sujeira=0.9)
    _, bm = novo(n + "_agua")
    comum.caixa(bm, (4.25, 0, 0.62), (2.2, 1.3, 0.04))
    o_agua = fechar(n + "_agua", bm, mat("agua_r2", (0.12, 0.17, 0.18), 0.1), oclusao=0, forca_sujeira=0.2)
    _, bm = novo(n + "_ferro")
    comum.cilindro(bm, (-0.7, 0, 2.3), 1.35, 2.6, 20)
    comum.esfera(bm, (-0.7, 0, 3.6), 1.35, 20, 10)
    for z in (1.2, 2.3, 3.4):
        comum.cilindro(bm, (-0.7, 0, z), 1.39, 0.08, 20)
    comum.caixa(bm, (1.3, 0, 1.6), (1.6, 1.4, 1.2))
    comum.cilindro(bm, (2.3, 0, 2.3), 1.1, 0.12, 24, eixo="X")
    comum.cilindro(bm, (2.3, 0, 2.3), 0.18, 0.4, 10, eixo="X")
    for k in range(6):
        v = comum.caixa(bm, (2.3, 0, 2.3 + 0.55), (0.06, 0.07, 1.1))
        girar(bm, v, k * math.pi / 3, "X", (2.3, 0, 2.3))
    tubo(bm, (1.6, 0.3, 2.1), (2.25, 0.3, 2.9), 0.05)
    tubo(bm, (1.6, -0.3, 2.1), (2.25, -0.3, 1.7), 0.05)
    comum.cilindro(bm, (0, 0, 14.4), 0.42, 21.6, 14)
    for z in range(5, 25, 3):
        comum.cilindro(bm, (0, 0, z), 0.52, 0.12, 14)
    tubo(bm, (-0.7, 0, 3.9), (0, 0, 4.4), 0.3, 10)
    tubo(bm, (0.6, 0, 1.6), (3.3, 0, 1.6), 0.12, 8)
    tubo(bm, (3.3, 0, 1.6), (3.3, 0, 1.2), 0.12, 8)
    comum.cilindro(bm, (-0.7, -1.4, 2.8), 0.16, 0.06, 14, eixo="Y")
    o_ferro = fechar(n + "_ferro", bm, mat("ferro_verde_r2", (0.36, 0.46, 0.38), 0.55, 0.5), bisel=0.01,
                     sujeira=(0.5, 0.28, 0.12), forca_sujeira=1.0, oclusao=0.2)
    _, bm = novo(n + "_tambores")
    for x, y in ((-4.0, -2.0), (-4.6, -2.6), (-4.0, 2.0), (-4.6, 2.6)):
        comum.cilindro(bm, (x, y, 0.45), 0.3, 0.9, 14)
    o_tamb = fechar(n + "_tambores", bm, mat("tambor_r2", (0.55, 0.25, 0.12), 0.6, 0.4), bisel=0.01, sujeira=(0.4, 0.22, 0.1), forca_sujeira=0.9)
    objs.append(juntar(n, [o_base, o_agua, o_ferro, o_tamb]))
    return objs


# ------------------------------------------------------------------ Duto Norte (túnel de metrô)

def kit_tunel():
    objs = []
    aco = mat("aco_cambota", (0.48, 0.45, 0.42), 0.6, 0.7)

    # cambota: pórtico de perfis I para o duto de 8 m x 5,5 m (de x -4 a 4), mãos-francesas nos cantos,
    # placas de base e um suporte de cabos na coluna oeste
    n, bm = novo("cambota")
    for x in (-3.86, 3.86):
        viga_i(bm, (x, 0, 2.75), 5.5, "Z")
        comum.caixa(bm, (x, 0, 0.02), (0.4, 0.4, 0.04))
    viga_i(bm, (0, 0, 5.38), 7.9, "X")
    for s in (-1, 1):
        v = comum.caixa(bm, (s * 3.25, 0, 4.78), (1.5, 0.12, 0.14))
        girar(bm, v, s * math.radians(40), "Y", (s * 3.25, 0, 4.78))
    for z in (2.6, 3.1):
        comum.caixa(bm, (-3.6, 0, z), (0.4, 0.3, 0.03))
    o1 = fechar(n, bm, aco, sujeira=(0.45, 0.26, 0.12), forca_sujeira=1.0, oclusao=0.15)
    objs.append(o1)

    # via de 6 m (ao longo de Y): lastro de brita, 8 dormentes e dois trilhos com boleto, alma e patim
    n, bm = novo("via_6m")
    comum.caixa(bm, (0, 0, 0.03), (2.8, 6.0, 0.08))
    o_lastro = fechar(n + "_lastro", bm, mat("brita_r2", (0.42, 0.4, 0.37), 0.95), ruido=0.03, escala_ruido=6, oclusao=0, forca_sujeira=0.8)
    _, bm = novo(n + "_dormentes")
    for i in range(8):
        comum.caixa(bm, (R.uniform(-0.04, 0.04), -2.62 + i * 0.75, 0.12), (2.4, 0.24, 0.12), rot_z=R.uniform(-0.04, 0.04))
    o_dorm = fechar(n + "_dormentes", bm, mat("madeira_dormente", (0.4, 0.29, 0.2), 0.9), bisel=0.01, ruido=0.01, oclusao=0)
    _, bm = novo(n + "_trilhos")
    for x in (-0.72, 0.72):
        comum.caixa(bm, (x, 0, 0.19), (0.13, 6.0, 0.015))
        comum.caixa(bm, (x, 0, 0.245), (0.02, 6.0, 0.1))
        comum.caixa(bm, (x, 0, 0.31), (0.07, 6.0, 0.04))
    o_tril = fechar(n + "_trilhos", bm, mat("ferro_trilho_r2", (0.55, 0.5, 0.46), 0.45, 0.8), sujeira=(0.45, 0.24, 0.1), forca_sujeira=0.7, oclusao=0)
    objs.append(juntar(n, [o_lastro, o_dorm, o_tril]))

    # feixe de cabos de 6 m (ao longo de Y) preso à parede em x = 0, a 3,2 m, com braçadeiras
    n, bm = novo("cabos_6m")
    for k, (dx, dz) in enumerate(((0.12, 0.0), (0.18, -0.07), (0.1, -0.12))):
        pts = [(dx, -3.0 + 6.0 * i / 8, 3.2 + dz - 0.12 * math.sin(math.pi * ((i % 4) / 4))) for i in range(9)]
        for p, q in zip(pts, pts[1:]):
            tubo(bm, p, q, 0.025 + 0.01 * k, 5)
    o1 = fechar(n + "_cabos", bm, mat("cabo_r2", (0.08, 0.08, 0.08), 0.6), oclusao=0)
    _, bm = novo(n + "_suporte")
    for y in (-3.0, 0.0):
        comum.caixa(bm, (0.12, y, 3.25), (0.24, 0.05, 0.05))
    o2 = fechar(n + "_suporte", bm, aco, oclusao=0)
    objs.append(juntar(n, [o1, o2]))
    return objs


# ------------------------------------------------------------------ superfície

CARROS = {"carro_vermelho": (0.72, 0.28, 0.2), "carro_azul": (0.32, 0.45, 0.6), "carro_bege": (0.8, 0.73, 0.58),
          "carro_ferrugem": (0.62, 0.38, 0.24)}


def carro(nome, cor):
    """Sedã soterrado com a origem no centro da carroceria (caixa de 1,8 x 1,3 x 4,3 m dos blocos): capô e
    porta-malas, cabine com colunas e vidros escuros, rodas, para-choques e ferrugem."""
    _, bm = novo(nome)
    comum.caixa(bm, (0, 0, -0.1), (1.8, 4.3, 0.9))                       # saia
    v = comum.caixa(bm, (0, 1.2, 0.5), (1.74, 1.6, 0.3))                # capô, caindo para a frente
    girar(bm, v, math.radians(-5), "X", (0, 1.2, 0.5))
    comum.caixa(bm, (0, -1.6, 0.5), (1.74, 1.0, 0.3))                   # porta-malas
    comum.caixa(bm, (0, -0.3, 0.5), (1.76, 1.6, 0.28))
    for y in (2.13, -2.13):
        comum.caixa(bm, (0, y, -0.15), (1.84, 0.12, 0.22))              # para-choques
    cab = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -0.3, 1.0)) @ Matrix.Diagonal((1.6, 2.2, 0.75, 1)))
    for vv in cab["verts"]:
        if vv.co.z > 1.1:
            vv.co.x *= 0.86
            vv.co.y = -0.3 + (vv.co.y + 0.3) * 0.62
    o1 = fechar(nome + "_lataria", bm, mat(f"lataria_{nome}", cor, 0.7, 0.35), bisel=0.05, ruido=0.025, escala_ruido=2,
                sujeira=(0.74, 0.66, 0.5), forca_sujeira=1.1, oclusao=0.0)  # coberto de poeira
    _, bm = novo(nome + "_vidro")
    for y, comp, inc in ((0.5, 0.05, 0.9), (-1.12, 0.05, 0.9)):
        v = comum.caixa(bm, (0, y, 1.02), (1.42, comp, 0.55))
        girar(bm, v, math.radians(38 if y > 0 else -38), "X", (0, y, 1.02))
    for s in (-1, 1):
        comum.caixa(bm, (s * 0.81, -0.3, 1.02), (0.04, 1.6, 0.45))
    o2 = fechar(nome + "_vidro", bm, mat("vidro_sujo_r2", (0.08, 0.08, 0.07), 0.3, 0.2), oclusao=0, forca_sujeira=0.3)
    _, bm = novo(nome + "_rodas")
    for x in (-0.8, 0.8):
        for y in (-1.35, 1.35):
            comum.cilindro(bm, (x, y, -0.5), 0.34, 0.24, 12, eixo="X")
    o3 = fechar(nome + "_rodas", bm, mat("pneu_r2", (0.1, 0.09, 0.08), 0.9), oclusao=0)
    return juntar(nome, [o1, o2, o3])


def kit_superficie():
    objs = [carro(n, c) for n, c in CARROS.items()]

    # poste de rua torto com braço e luminária quebrada (7 m), base no chão
    n, bm = novo("poste_rua")
    comum.cilindro(bm, (0, 0, 3.4), 0.11, 6.8, 8, raio_topo=0.07)
    comum.cilindro(bm, (0, 0, 0.3), 0.18, 0.6, 8)
    tubo(bm, (0, 0, 6.6), (1.2, 0, 7.0), 0.05, 6)
    tubo(bm, (1.2, 0, 7.0), (1.7, 0, 6.85), 0.05, 6)
    comum.caixa(bm, (1.85, 0, 6.75), (0.55, 0.25, 0.12))
    objs.append(fechar(n, bm, mat("ferro_poste_r2", (0.32, 0.3, 0.28), 0.6, 0.6), sujeira=(0.45, 0.25, 0.12), forca_sujeira=1.0, oclusao=0))

    # monte de entulho baixo (3 x 3 m, até 0,5 m): pedaços de laje, tijolos e vergalhões
    n, bm = novo("entulho_r2")
    for _ in range(14):
        s = R.uniform(0.25, 0.8)
        v = comum.caixa(bm, (R.uniform(-1.2, 1.2), R.uniform(-1.2, 1.2), s * 0.15), (s, s * R.uniform(0.6, 1.3), s * 0.35))
        girar(bm, v, R.uniform(0, 3), "Z")
        girar(bm, v, R.uniform(-0.3, 0.3), "X", tuple(sum((x.co for x in v), Vector()) / len(v)))
    o1 = fechar(n + "_pedras", bm, mat("entulho_concreto_r2", (0.66, 0.61, 0.53), 0.95), ruido=0.04, escala_ruido=2.5, oclusao=0.0,
                sujeira=(0.62, 0.55, 0.42), forca_sujeira=0.9)
    _, bm = novo(n + "_ferros")
    for _ in range(6):
        x, y = R.uniform(-0.8, 0.8), R.uniform(-0.8, 0.8)
        tubo(bm, (x, y, 0.1), (x + R.uniform(-0.4, 0.4), y + R.uniform(-0.4, 0.4), R.uniform(0.6, 1.2)), 0.012, 4)
    o2 = fechar(n + "_ferros", bm, mat("vergalhao_r2", (0.35, 0.2, 0.12), 0.7, 0.6), oclusao=0)
    objs.append(juntar(n, [o1, o2]))

    # vergalhões saindo do topo quebrado de uma parede (2 m de largura, base em z = 0)
    n, bm = novo("vergalhoes")
    for i in range(7):
        x = -0.9 + i * 0.3
        h = R.uniform(0.4, 1.4)
        tubo(bm, (x, 0, -0.1), (x + R.uniform(-0.15, 0.15), R.uniform(-0.2, 0.2), h), 0.012, 4)
    objs.append(fechar(n, bm, mat("vergalhao_r2", (0.35, 0.2, 0.12), 0.7, 0.6), oclusao=0))
    return objs


KITS = {"r2_cisterna": kit_cisterna, "r2_tunel": kit_tunel, "r2_superficie": kit_superficie}


def gerar(nome: str) -> None:
    comum.limpar_cena()
    M.clear()
    objs = KITS[nome]()
    tri = 0
    for o in objs:
        o.location = (0, 0, 0)
        tri += sum(len(p.vertices) - 2 for p in o.data.polygons)
        print(f"  {o.name}: {sum(len(p.vertices) - 2 for p in o.data.polygons)} triângulos")
    print(f"{nome}: {len(objs)} módulos, {tri} triângulos")
    comum.exportar_glb(os.path.join(SAIDA, f"{nome}.glb"), selecionados=objs)


if __name__ == "__main__":
    for k in (comum.argumentos() or list(KITS)):
        gerar(k)
