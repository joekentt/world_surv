"""Gera os kits modulares de cenário e exporta um GLB por estética em public/assets/kits/.

Uso: python tools/blender/kits/gerar_kits.py [kit ...]   (sem argumentos gera todos)

Cada módulo é um objeto de topo cujo nome é o nome usado nos layouts de content/areas/.
Eixos no Blender: X = lateral (eixo do jogo), Y = profundidade (positivo se afasta da câmera),
Z = para cima. O carregador do jogo converte para X lateral, Y para cima, Z profundidade.
Origem de cada módulo: no chão, no centro em X, na face da frente (Y = 0) salvo indicação.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

import comum  # noqa: E402

SAIDA = os.path.join(comum.ASSETS, "kits")
R = comum.semente(42)


# ------------------------------------------------------------------ utilidades

def novo(nome: str):
    return nome, bmesh.new()


def fechar(nome: str, bm, mat, *, bisel=0.0, ruido=0.0, escala_ruido=1.5, suave=35, sujeira=(0.55, 0.5, 0.45),
           forca_sujeira=0.5, oclusao=0.35, base=(1, 1, 1)):
    obj = comum.objeto_de_bmesh(nome, bm)
    if bisel:
        comum.biselar(obj, bisel)
        comum.aplicar_modificadores(obj)
    if ruido:
        comum.deformar_ruido(obj, escala_ruido, ruido, semente_ruido=R.uniform(0, 50))
    comum.suavizar(obj, suave)
    comum.cor_vertice_desgaste(obj, base=base, sujeira=sujeira, forca=forca_sujeira, oclusao_chao=oclusao,
                               semente_ruido=R.uniform(0, 50))
    comum.atribuir(obj, mat)
    return obj


def juntar(nome: str, partes: list):
    partes = [p for p in partes if p]
    bpy.ops.object.select_all(action="DESELECT")
    for p in partes:
        p.select_set(True)
    bpy.context.view_layer.objects.active = partes[0]
    if len(partes) > 1:
        bpy.ops.object.join()
    partes[0].name = nome
    partes[0].data.name = nome
    return partes[0]


def texto(conteudo: str, tamanho: float, extrusao: float = 0.01):
    curva = bpy.data.curves.new("txt", "FONT")
    curva.body = conteudo
    curva.size = tamanho
    curva.extrude = extrusao
    curva.align_x = "CENTER"
    obj = bpy.data.objects.new("txt", curva)
    bpy.context.scene.collection.objects.link(obj)
    deps = bpy.context.evaluated_depsgraph_get()
    malha = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    bpy.data.objects.remove(obj)
    o = bpy.data.objects.new("txt_malha", malha)
    bpy.context.scene.collection.objects.link(o)
    # texto deitado em XY: gira para ficar de pé, virado para a câmera (-Y)
    o.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    return o


M = {}


def mat(nome, cor, rug=0.8, metal=0.0, emissao=None, forca=0.0, alfa=1.0):
    if nome not in M:
        M[nome] = comum.material(nome, cor, rug, metal, emissao, forca, alfa)
    return M[nome]


# ------------------------------------------------------------------ kit comum (objetos e itens)

def kit_comum():
    objs = []
    n, bm = novo("caixote")
    comum.caixa(bm, (0, 0.5, 0.5), (1, 1, 1))
    for z in (0.1, 0.9):
        comum.caixa(bm, (0, 0.5, z), (1.04, 1.04, 0.08))
    objs.append(fechar(n, bm, mat("madeira", (0.45, 0.32, 0.2)), bisel=0.015, sujeira=(0.3, 0.25, 0.2)))

    n, bm = novo("barril")
    comum.cilindro(bm, (0, 0.35, 0.5), 0.33, 1.0, 16)
    for z in (0.18, 0.82):
        comum.cilindro(bm, (0, 0.35, z), 0.345, 0.05, 16)
    objs.append(fechar(n, bm, mat("metal_azul", (0.22, 0.32, 0.4), 0.6, 0.5), sujeira=(0.45, 0.28, 0.15), forca_sujeira=0.8))

    n, bm = novo("cano")
    comum.cilindro(bm, (0, 0, 0), 0.12, 4.0, 12, eixo="X")
    for x in (-1.9, 1.9):
        comum.cilindro(bm, (x, 0, 0), 0.16, 0.12, 12, eixo="X")
    objs.append(fechar(n, bm, mat("metal_ferrugem", (0.42, 0.3, 0.22), 0.7, 0.4), sujeira=(0.5, 0.25, 0.1), forca_sujeira=0.9, oclusao=0))

    n, bm = novo("cabo")
    pts = [Vector((x, 0, -0.6 * (1 - (x / 3) ** 2))) for x in [i * 0.5 - 3 for i in range(13)]]
    for a, b in zip(pts, pts[1:]):
        meio = (a + b) / 2
        d = b - a
        v = comum.cilindro(bm, meio, 0.015, d.length, 5, eixo="X")
        ang = math.atan2(d.z, d.x)
        bmesh.ops.rotate(bm, verts=v, cent=meio, matrix=Matrix.Rotation(-ang, 3, "Y"))
    objs.append(fechar(n, bm, mat("borracha", (0.06, 0.06, 0.06), 0.6), oclusao=0))

    n, bm = novo("lampada")
    comum.cilindro(bm, (0, 0, -0.35), 0.008, 0.7, 4)
    comum.cilindro(bm, (0, 0, -0.72), 0.16, 0.08, 14, raio_topo=0.05)
    o1 = fechar(n + "_suporte", bm, mat("metal_escuro", (0.12, 0.12, 0.12), 0.5, 0.6), oclusao=0)
    n2, bm = novo("lampada_bulbo")
    comum.esfera(bm, (0, 0, -0.8), 0.07, 10, 7)
    o2 = fechar(n2, bm, mat("luz_ambar", (1, 0.75, 0.4), 0.3, emissao=(1, 0.72, 0.38), forca=6), oclusao=0)
    objs.append(juntar(n, [o1, o2]))

    n, bm = novo("tubo_fluor")
    comum.caixa(bm, (0, 0, 0.03), (1.3, 0.12, 0.05))
    o1 = fechar(n + "_calha", bm, mat("metal_escuro", (0.12, 0.12, 0.12), 0.5, 0.6), oclusao=0)
    n2, bm = novo("tubo_luz")
    comum.cilindro(bm, (0, 0, -0.01), 0.025, 1.2, 8, eixo="X")
    o2 = fechar(n2, bm, mat("luz_fria", (0.6, 1, 0.92), 0.3, emissao=(0.55, 1.0, 0.9), forca=5), oclusao=0)
    objs.append(juntar(n, [o1, o2]))

    n, bm = novo("escada_mao")  # 1 m de altura; o layout escala em Z
    for x in (-0.28, 0.28):
        comum.caixa(bm, (x, 0, 0.5), (0.06, 0.06, 1.0))
    for z in (0.15, 0.5, 0.85):
        comum.cilindro(bm, (0, 0, z), 0.02, 0.56, 6, eixo="X")
    objs.append(fechar(n, bm, mat("metal_ferrugem", (0.42, 0.3, 0.22), 0.7, 0.4), sujeira=(0.5, 0.25, 0.1), oclusao=0))

    n, bm = novo("entulho")
    for i in range(9):
        comum.caixa(bm, (R.uniform(-0.9, 0.9), R.uniform(0, 0.8), R.uniform(0.05, 0.3)),
                    (R.uniform(0.2, 0.6), R.uniform(0.2, 0.5), R.uniform(0.1, 0.35)), R.uniform(0, 3))
    objs.append(fechar(n, bm, mat("concreto", (0.5, 0.48, 0.44), 0.9), ruido=0.03, escala_ruido=3))

    n, bm = novo("mesa")
    comum.caixa(bm, (0, 0.5, 0.78), (1.4, 0.8, 0.06))
    for x in (-0.62, 0.62):
        for y in (0.18, 0.82):
            comum.caixa(bm, (x, y, 0.38), (0.06, 0.06, 0.76))
    objs.append(fechar(n, bm, mat("madeira", (0.45, 0.32, 0.2)), bisel=0.01, sujeira=(0.3, 0.25, 0.2)))

    n, bm = novo("banco")
    comum.caixa(bm, (0, 0.25, 0.45), (1.6, 0.4, 0.06))
    for x in (-0.7, 0.7):
        comum.caixa(bm, (x, 0.25, 0.22), (0.08, 0.36, 0.44))
    objs.append(fechar(n, bm, mat("madeira", (0.45, 0.32, 0.2)), bisel=0.01, sujeira=(0.3, 0.25, 0.2)))

    n, bm = novo("varal")
    comum.cilindro(bm, (0, 0, 0), 0.006, 6.0, 4, eixo="X")
    o1 = fechar(n + "_fio", bm, mat("borracha", (0.06, 0.06, 0.06)), oclusao=0)
    pecas = [o1]
    cores = [(0.6, 0.2, 0.15), (0.2, 0.35, 0.5), (0.7, 0.65, 0.5), (0.3, 0.45, 0.25), (0.55, 0.4, 0.15)]
    for i, x in enumerate((-2.2, -1.1, 0.2, 1.4, 2.4)):
        nn, bm = novo(f"roupa{i}")
        w, h = R.uniform(0.35, 0.6), R.uniform(0.45, 0.8)
        comum.caixa(bm, (x, 0, -h / 2), (w, 0.02, h))
        pecas.append(fechar(nn, bm, mat(f"pano{i}", cores[i], 0.95), ruido=0.02, escala_ruido=4, oclusao=0, forca_sujeira=0.6))
    objs.append(juntar(n, pecas))

    n, bm = novo("lona")
    v = comum.caixa(bm, (0, 0.6, 0), (3.0, 1.6, 0.02))
    objs.append(fechar(n, bm, mat("lona_azul", (0.18, 0.3, 0.42), 0.9), ruido=0.06, escala_ruido=1.2, oclusao=0, forca_sujeira=0.7))
    _ = v

    n, bm = novo("saco")
    comum.esfera(bm, (0, 0.3, 0.28), 0.32, 10, 7)
    o = fechar(n, bm, mat("juta", (0.55, 0.45, 0.3), 0.95), ruido=0.04, escala_ruido=3)
    o.scale = (1, 0.8, 0.85)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(scale=True)
    objs.append(o)

    n, bm = novo("placa_reservatorio")
    comum.caixa(bm, (0, 0.02, 0), (3.4, 0.04, 0.7))
    o1 = fechar(n + "_chapa", bm, mat("esmalte_azul", (0.15, 0.25, 0.45), 0.5, 0.3), sujeira=(0.4, 0.3, 0.2), forca_sujeira=0.9, oclusao=0)
    t = texto("RESERVATÓRIO MUNICIPAL Nº 3", 0.24)
    t.location = (0, -0.01, -0.08)
    comum.atribuir(t, mat("esmalte_branco", (0.85, 0.85, 0.8), 0.5))
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    objs.append(juntar(n, [o1, t]))

    n, bm = novo("poca")
    v = comum.cilindro(bm, (0, 0, 0.005), 1.0, 0.01, 16)
    o = fechar(n, bm, mat("agua_poca", (0.08, 0.09, 0.1), 0.05, 0.3), oclusao=0)
    o.scale = (1.6, 0.8, 1)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(scale=True)
    objs.append(o)
    _ = v

    # itens coletáveis (pequenos, com cor forte para leitura)
    n, bm = novo("item_sucata")
    for i in range(5):
        comum.caixa(bm, (R.uniform(-0.2, 0.2), R.uniform(-0.1, 0.1), R.uniform(0.05, 0.2)),
                    (R.uniform(0.15, 0.35), R.uniform(0.05, 0.2), R.uniform(0.04, 0.15)), R.uniform(0, 3))
    objs.append(fechar(n, bm, mat("metal_ferrugem", (0.42, 0.3, 0.22), 0.7, 0.4), sujeira=(0.55, 0.3, 0.12), forca_sujeira=0.9))
    n, bm = novo("item_componente")
    comum.caixa(bm, (0, 0, 0.04), (0.3, 0.22, 0.03))
    for i in range(6):
        comum.caixa(bm, (R.uniform(-0.1, 0.1), R.uniform(-0.07, 0.07), 0.07), (0.05, 0.04, 0.03))
    objs.append(fechar(n, bm, mat("placa_verde", (0.1, 0.4, 0.2), 0.5, 0.2, emissao=(0.1, 0.6, 0.3), forca=0.6), oclusao=0))
    n, bm = novo("item_vidro")
    for i in range(3):
        comum.cilindro(bm, (i * 0.12 - 0.12, 0, 0.15), 0.05, 0.3, 10, raio_topo=0.03)
    objs.append(fechar(n, bm, mat("vidro_verde", (0.4, 0.75, 0.6), 0.1, 0.0, emissao=(0.2, 0.5, 0.4), forca=0.5), oclusao=0))
    n, bm = novo("item_amostra")
    comum.cilindro(bm, (0, 0, 0.12), 0.06, 0.24, 10)
    objs.append(fechar(n, bm, mat("vidro_ambar", (0.8, 0.55, 0.25), 0.15, emissao=(0.6, 0.35, 0.1), forca=0.8), oclusao=0))
    n, bm = novo("item_mascara")
    comum.esfera(bm, (0, 0, 0.12), 0.14, 12, 8)
    comum.cilindro(bm, (0.1, -0.08, 0.08), 0.05, 0.06, 10, eixo="Y")
    comum.cilindro(bm, (-0.1, -0.08, 0.08), 0.05, 0.06, 10, eixo="Y")
    objs.append(fechar(n, bm, mat("borracha_cinza", (0.3, 0.3, 0.32), 0.6), oclusao=0))
    n, bm = novo("item_gravador")
    comum.caixa(bm, (0, 0, 0.06), (0.22, 0.1, 0.12))
    comum.cilindro(bm, (0.05, -0.051, 0.07), 0.03, 0.01, 10, eixo="Y")
    objs.append(fechar(n, bm, mat("plastico_preto", (0.08, 0.08, 0.09), 0.4, emissao=(0.9, 0.1, 0.05), forca=0.0), oclusao=0))
    n, bm = novo("ponto_amostra")  # marcação no solo onde se colhe a amostra
    comum.cilindro(bm, (0, 0, 0.6), 0.03, 1.2, 6)
    comum.caixa(bm, (0.15, 0, 1.1), (0.3, 0.01, 0.18))
    objs.append(fechar(n, bm, mat("bandeira", (0.85, 0.35, 0.1), 0.8, emissao=(0.8, 0.3, 0.05), forca=0.8), oclusao=0))
    return objs


# ------------------------------------------------------------------ cisterna (Praça do Reservatório)

CONCRETO = None


def kit_cisterna():
    objs = []
    concreto = mat("concreto_umido", (0.5, 0.48, 0.44), 0.75)
    n, bm = novo("piso")  # 6 m x 14 m de profundidade, topo em z = 0
    comum.caixa(bm, (0, 4, -0.25), (6.0, 14.0, 0.5))
    objs.append(fechar(n, bm, concreto, ruido=0.01, sujeira=(0.35, 0.33, 0.3), forca_sujeira=0.8, oclusao=0))

    n, bm = novo("parede_fundo")  # 6 m de largura, 12 de altura, em y = 0..0.6
    comum.caixa(bm, (0, 0.3, 6), (6.0, 0.6, 12))
    for z in (3, 6.5, 10):
        comum.caixa(bm, (0, -0.05, z), (6.0, 0.15, 0.25))
    comum.caixa(bm, (0, -0.1, 0.4), (6.0, 0.25, 0.8))
    objs.append(fechar(n, bm, concreto, bisel=0.02, ruido=0.02, sujeira=(0.32, 0.36, 0.3), forca_sujeira=0.9))

    n, bm = novo("coluna")
    comum.cilindro(bm, (0, 0, 5.5), 0.45, 11, 16)
    comum.cilindro(bm, (0, 0, 11.4), 1.1, 0.8, 16, raio_topo=1.3)
    comum.cilindro(bm, (0, 0, 10.8), 0.45, 0.6, 16, raio_topo=1.1)
    comum.cilindro(bm, (0, 0, 0.2), 0.6, 0.4, 16)
    objs.append(fechar(n, bm, concreto, ruido=0.015, sujeira=(0.3, 0.35, 0.28), forca_sujeira=0.9))

    n, bm = novo("teto")
    comum.caixa(bm, (0, 4, 12.2), (6.0, 14.0, 0.4))
    objs.append(fechar(n, bm, concreto, ruido=0.02, oclusao=0, sujeira=(0.25, 0.25, 0.22)))

    n, bm = novo("bomba")
    comum.caixa(bm, (0, 0.8, 0.4), (2.4, 1.6, 0.8))
    comum.cilindro(bm, (-0.5, 0.8, 1.4), 0.55, 1.4, 16)
    comum.cilindro(bm, (0.7, 0.8, 1.2), 0.75, 0.25, 20, eixo="Y")  # volante
    comum.cilindro(bm, (-0.5, 0.8, 3.5), 0.15, 3.0, 10)  # cano de subida
    comum.cilindro(bm, (0.3, 0.8, 5.0), 0.15, 1.8, 10, eixo="X")
    objs.append(fechar(n, bm, mat("metal_verde", (0.25, 0.35, 0.28), 0.6, 0.5), bisel=0.01, sujeira=(0.5, 0.3, 0.12), forca_sujeira=0.9))

    n, bm = novo("barraca_lona")
    for x in (-1.4, 1.4):
        for y in (0.2, 1.6):
            comum.caixa(bm, (x, y, 1.1), (0.08, 0.08, 2.2))
    comum.caixa(bm, (0, 0.5, 0.85), (2.8, 0.7, 0.08))
    comum.caixa(bm, (0, 0.5, 0.42), (2.8, 0.05, 0.84))
    o1 = fechar(n + "_estr", bm, mat("madeira", (0.45, 0.32, 0.2)), sujeira=(0.3, 0.25, 0.2))
    nn, bm = novo("barraca_teto")
    v = comum.caixa(bm, (0, 0.9, 2.35), (3.2, 2.0, 0.03))
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0.9, 2.35), matrix=Matrix.Rotation(-0.25, 3, "X"))
    o2 = fechar(nn, bm, mat("lona_laranja", (0.6, 0.35, 0.15), 0.9), ruido=0.05, oclusao=0, forca_sujeira=0.7)
    pecas = [o1, o2]
    for i in range(6):
        nn, bm = novo(f"merc{i}")
        comum.caixa(bm, (-1.1 + i * 0.44, 0.45, 0.98), (0.3, 0.3, R.uniform(0.15, 0.35)))
        pecas.append(fechar(nn, bm, mat(f"merc_mat{i % 3}", [(0.5, 0.4, 0.3), (0.35, 0.4, 0.3), (0.45, 0.3, 0.3)][i % 3]), oclusao=0))
    objs.append(juntar(n, pecas))

    n, bm = novo("barraca_caravana")
    for x in (-1.6, 1.6):
        comum.caixa(bm, (x, 0.9, 1.3), (0.1, 0.1, 2.6))
    comum.caixa(bm, (0, 0.6, 0.45), (3.0, 0.9, 0.9))
    o1 = fechar(n + "_estr", bm, mat("madeira_escura", (0.3, 0.2, 0.12)), bisel=0.01)
    pecas = [o1]
    for i, cor in enumerate([(0.55, 0.12, 0.1), (0.15, 0.2, 0.45), (0.7, 0.55, 0.15)]):
        nn, bm = novo(f"tecido{i}")
        v = comum.caixa(bm, (-1 + i, 1.0, 2.5 - i * 0.05), (1.1, 1.8, 0.03))
        pecas.append(fechar(nn, bm, mat(f"tecido_qarar{i}", cor, 0.9), ruido=0.05, oclusao=0, forca_sujeira=0.3))
    nn, bm = novo("filtros_novos")
    for i in range(7):
        comum.cilindro(bm, (-1.2 + i * 0.4, 0.4, 1.0), 0.09, 0.18, 12)
    pecas.append(fechar(nn, bm, mat("filtro_novo", (0.85, 0.82, 0.75), 0.4, 0.3, emissao=(0.5, 0.48, 0.42), forca=0.4), oclusao=0))
    objs.append(juntar(n, pecas))

    n, bm = novo("sede_conselho")  # fachada de 8 m com balcão
    comum.caixa(bm, (0, 1.2, 2.6), (8, 0.4, 5.2))
    comum.caixa(bm, (0, -0.2, 0.55), (3.4, 0.6, 1.1))  # balcão
    comum.caixa(bm, (0, -0.4, 4.6), (8.4, 0.6, 0.4))
    o1 = fechar(n + "_corpo", bm, mat("reboco", (0.6, 0.56, 0.48), 0.85), bisel=0.02, ruido=0.01, forca_sujeira=0.7)
    nn, bm = novo("grade_balcao")
    for x in range(9):
        comum.cilindro(bm, (-1.6 + x * 0.4, -0.45, 1.75), 0.015, 1.3, 5)
    o2 = fechar(nn, bm, mat("metal_escuro", (0.12, 0.12, 0.12), 0.5, 0.6), oclusao=0)
    t = texto("CONSELHO DA CISTERNA", 0.32)
    t.location = (0, -0.72, 4.5)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("esmalte_branco", (0.85, 0.85, 0.8), 0.5))
    t2 = texto("COTAS", 0.22)
    t2.location = (0, -0.52, 1.2)
    bpy.context.view_layer.objects.active = t2
    t2.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t2, mat("tinta_vermelha", (0.6, 0.12, 0.08), 0.7))
    objs.append(juntar(n, [o1, o2, t, t2]))

    n, bm = novo("muro_subidores")  # 6 m, com ganchos; máscaras são peças separadas
    comum.caixa(bm, (0, 0.2, 1.8), (6, 0.4, 3.6))
    comum.caixa(bm, (0, -0.05, 3.7), (6.3, 0.5, 0.2))
    o1 = fechar(n + "_parede", bm, mat("tijolo", (0.5, 0.3, 0.22), 0.9), bisel=0.02, ruido=0.015, forca_sujeira=0.7)
    t = texto("OS QUE SUBIRAM", 0.26)
    t.location = (0, -0.05, 3.25)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("tinta_branca_gasta", (0.75, 0.72, 0.65), 0.9))
    nn, bm = novo("mascaras_muro")
    for fila, z in enumerate((2.4, 1.5)):
        for i in range(9):
            x = -2.4 + i * 0.6 + (0.3 if fila else 0)
            if abs(x) > 2.6:
                continue
            comum.esfera(bm, (x, -0.08, z), 0.14, 10, 6)
            comum.cilindro(bm, (x + 0.08, -0.2, z - 0.05), 0.04, 0.06, 8, eixo="Y")
            comum.cilindro(bm, (x - 0.08, -0.2, z - 0.05), 0.04, 0.06, 8, eixo="Y")
    o2 = fechar(nn, bm, mat("borracha_cinza", (0.3, 0.3, 0.32), 0.6), oclusao=0, forca_sujeira=0.8)
    objs.append(juntar(n, [o1, t, o2]))

    n, bm = novo("mascara_darci_muro")
    comum.esfera(bm, (0, -0.08, 0), 0.15, 12, 8)
    comum.cilindro(bm, (0.09, -0.21, -0.05), 0.045, 0.07, 8, eixo="Y")
    comum.cilindro(bm, (-0.09, -0.21, -0.05), 0.045, 0.07, 8, eixo="Y")
    objs.append(fechar(n, bm, mat("borracha_laranja", (0.7, 0.35, 0.1), 0.6), oclusao=0))

    n, bm = novo("plataforma_metal")  # 4 x 1.6 m, topo em z = 0
    comum.caixa(bm, (0, 0.3, -0.06), (4, 1.6, 0.12))
    for x in (-1.9, 1.9):
        comum.caixa(bm, (x, -0.45, 0.5), (0.05, 0.05, 1.0))
    comum.caixa(bm, (0, -0.45, 1.0), (4, 0.05, 0.05))
    objs.append(fechar(n, bm, mat("grade_metal", (0.3, 0.3, 0.3), 0.5, 0.7), sujeira=(0.45, 0.28, 0.12), forca_sujeira=0.8, oclusao=0))

    n, bm = novo("escotilha")  # moldura de porta no alto da escada do Duto Norte
    comum.caixa(bm, (0, 0.3, 1.3), (2.0, 0.5, 2.6))
    o1 = fechar(n + "_moldura", bm, mat("metal_escuro", (0.12, 0.12, 0.12), 0.5, 0.6), bisel=0.02)
    nn, bm = novo("escotilha_porta")
    comum.caixa(bm, (0, 0.02, 1.1), (1.3, 0.1, 2.1))
    comum.cilindro(bm, (0.4, -0.05, 1.1), 0.12, 0.05, 10, eixo="Y")
    o2 = fechar(nn, bm, mat("metal_amarelo", (0.6, 0.48, 0.12), 0.6, 0.4), sujeira=(0.4, 0.25, 0.1), forca_sujeira=0.9)
    t = texto("DUTO NORTE", 0.18)
    t.location = (0, -0.1, 2.4)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("esmalte_branco", (0.85, 0.85, 0.8), 0.5))
    objs.append(juntar(n, [o1, o2, t]))

    n, bm = novo("foto_ceu")
    comum.caixa(bm, (0, 0, 0), (0.5, 0.03, 0.36))
    o1 = fechar(n + "_moldura", bm, mat("madeira_escura", (0.3, 0.2, 0.12)), oclusao=0)
    nn, bm = novo("foto_ceu_imagem")
    comum.caixa(bm, (0, -0.02, 0.02), (0.42, 0.01, 0.26))
    o2 = fechar(nn, bm, mat("ceu_azul", (0.45, 0.7, 0.95), 0.6, emissao=(0.35, 0.6, 0.9), forca=1.2), oclusao=0)
    nn, bm = novo("foto_ceu_chao")
    comum.caixa(bm, (0, -0.025, -0.09), (0.42, 0.01, 0.07))
    o3 = fechar(nn, bm, mat("campo_verde", (0.35, 0.5, 0.25), 0.8), oclusao=0)
    objs.append(juntar(n, [o1, o2, o3]))

    n, bm = novo("casa_fundo")  # casinha encostada no fundo, com porta (NPCs entram para descansar)
    comum.caixa(bm, (0, 1.3, 1.5), (3.6, 2.6, 3.0))
    comum.caixa(bm, (0, 1.3, 3.15), (3.9, 2.9, 0.3))
    o1 = fechar(n + "_corpo", bm, mat("reboco_gasto", (0.55, 0.5, 0.42), 0.9), bisel=0.02, ruido=0.015, forca_sujeira=0.8)
    nn, bm = novo("casa_porta")
    comum.caixa(bm, (0.6, -0.01, 1.0), (0.9, 0.05, 2.0))
    comum.caixa(bm, (-0.9, -0.01, 1.7), (0.7, 0.05, 0.6))
    o2 = fechar(nn, bm, mat("madeira_escura", (0.3, 0.2, 0.12)), oclusao=0)
    nn, bm = novo("casa_janela")
    comum.caixa(bm, (-0.9, -0.03, 1.7), (0.55, 0.02, 0.45))
    o3 = fechar(nn, bm, mat("janela_luz", (1, 0.7, 0.35), 0.5, emissao=(1, 0.65, 0.3), forca=1.5), oclusao=0)
    objs.append(juntar(n, [o1, o2, o3]))

    n, bm = novo("cozinha")  # fogareiro com panela
    comum.cilindro(bm, (0, 0.4, 0.35), 0.35, 0.7, 12)
    comum.cilindro(bm, (0, 0.4, 0.85), 0.28, 0.3, 14)
    o1 = fechar(n + "_corpo", bm, mat("metal_escuro", (0.12, 0.12, 0.12), 0.5, 0.6), sujeira=(0.1, 0.08, 0.06))
    nn, bm = novo("brasa")
    comum.cilindro(bm, (0, 0.4, 0.66), 0.3, 0.04, 12)
    o2 = fechar(nn, bm, mat("brasa", (1, 0.4, 0.1), 0.8, emissao=(1, 0.35, 0.05), forca=3), oclusao=0)
    objs.append(juntar(n, [o1, o2]))
    return objs


# ------------------------------------------------------------------ gueto (Galerias Secas)

def barraco(nome: str, largura: float, altura: float, cor):
    _, bm = novo(nome)
    comum.caixa(bm, (0, 1.3, altura / 2), (largura, 2.6, altura))
    v = comum.caixa(bm, (0, 1.3, altura + 0.1), (largura + 0.4, 3.0, 0.06))
    bmesh.ops.rotate(bm, verts=v, cent=(0, 1.3, altura + 0.1), matrix=Matrix.Rotation(0.12, 3, "X"))
    corpo = fechar(nome + "_corpo", bm, mat(f"chapa_{nome}", cor, 0.7, 0.5), ruido=0.04, escala_ruido=2.2,
                   sujeira=(0.45, 0.25, 0.12), forca_sujeira=1.0)
    # ondulação da chapa
    for vv in corpo.data.vertices:
        vv.co.y += 0.03 * math.sin(vv.co.x * 18) * (1 if vv.co.y < 0.1 else 0)
    _, bm = novo(nome + "_porta")
    comum.caixa(bm, (largura * 0.2, -0.02, 0.95), (0.8, 0.05, 1.9))
    porta = fechar(nome + "_porta", bm, mat("madeira_escura", (0.3, 0.2, 0.12)), oclusao=0)
    _, bm = novo(nome + "_janela")
    comum.caixa(bm, (-largura * 0.25, -0.03, altura * 0.62), (0.6, 0.02, 0.45))
    janela = fechar(nome + "_janela", bm, mat("janela_fria", (0.5, 0.9, 0.85), 0.5, emissao=(0.4, 0.85, 0.8), forca=1.2), oclusao=0)
    return juntar(nome, [corpo, porta, janela])


def kit_gueto():
    objs = []
    rocha = mat("rocha_galeria", (0.38, 0.36, 0.33), 0.95)
    n, bm = novo("piso")
    comum.caixa(bm, (0, 4, -0.25), (6.0, 14.0, 0.5))
    objs.append(fechar(n, bm, mat("concreto_sujo", (0.36, 0.34, 0.31), 0.9), ruido=0.015, sujeira=(0.22, 0.22, 0.2), forca_sujeira=0.9, oclusao=0))
    n, bm = novo("parede_rocha")  # fundo rochoso da galeria, 6 m x 10 m
    comum.caixa(bm, (0, 0.5, 5), (6.0, 1.0, 10))
    objs.append(fechar(n, bm, rocha, ruido=0.25, escala_ruido=0.8, forca_sujeira=0.6))
    n, bm = novo("teto_galeria")
    comum.caixa(bm, (0, 4, 9.6), (6.0, 14, 0.6))
    for y in (1.0, 2.5):
        comum.cilindro(bm, (0, y, 9.0), 0.15, 6.0, 10, eixo="X")
    objs.append(fechar(n, bm, rocha, ruido=0.12, escala_ruido=1, oclusao=0))
    objs.append(barraco("barraco_a", 3.0, 2.6, (0.45, 0.4, 0.35)))
    objs.append(barraco("barraco_b", 2.6, 2.5, (0.38, 0.45, 0.42)))
    objs.append(barraco("barraco_c", 3.4, 2.7, (0.5, 0.35, 0.28)))
    n, bm = novo("passarela")  # 4 m, topo em z = 0
    comum.caixa(bm, (0, 0.5, -0.05), (4, 1.4, 0.1))
    for x in (-1.9, 0, 1.9):
        comum.caixa(bm, (x, -0.15, 0.5), (0.05, 0.05, 1.0))
    comum.caixa(bm, (0, -0.15, 0.95), (4, 0.04, 0.04))
    comum.caixa(bm, (0, -0.15, 0.5), (4, 0.03, 0.03))
    objs.append(fechar(n, bm, mat("madeira_velha", (0.4, 0.3, 0.2)), sujeira=(0.25, 0.2, 0.15), forca_sujeira=0.8, oclusao=0))
    n, bm = novo("pichacao")  # painel de 3 m com traços coloridos gerados por ruído
    pecas = []
    for i, cor in enumerate([(0.85, 0.2, 0.3), (0.2, 0.8, 0.5), (0.95, 0.75, 0.1), (0.3, 0.5, 0.95)]):
        nn, bm = novo(f"tinta{i}")
        x0 = R.uniform(-1.2, 0.6)
        z0 = R.uniform(0.8, 2.0)
        pts = []
        for k in range(24):
            t = k / 23
            pts.append(Vector((x0 + t * R.uniform(0.6, 1.4), 0, z0 + 0.35 * math.sin(t * R.uniform(4, 9)) + noise.noise(Vector((t * 3, i, 0))) * 0.2)))
        for a, b in zip(pts, pts[1:]):
            d = b - a
            v = comum.caixa(bm, (a + b) / 2, (d.length + 0.03, 0.01, 0.07))
            bmesh.ops.rotate(bm, verts=v, cent=(a + b) / 2, matrix=Matrix.Rotation(-math.atan2(d.z, d.x), 3, "Y"))
        pecas.append(fechar(nn, bm, mat(f"spray{i}", cor, 0.9), oclusao=0, forca_sujeira=0.2))
    t = texto("O SOL PERDOA", 0.3)
    t.location = (0.3, -0.01, 0.4)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("spray_amarelo", (0.95, 0.75, 0.15), 0.9))
    pecas.append(t)
    objs.append(juntar(n, pecas))
    n, bm = novo("pichacao_b")
    t = texto("COTA É ROUBO", 0.28)
    comum.atribuir(t, mat("spray_vermelho", (0.85, 0.15, 0.15), 0.9))
    t2 = texto("DARCI VIVE?", 0.2)
    t2.location = (0.4, 0, -0.5)
    bpy.context.view_layer.objects.active = t2
    t2.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t2, mat("spray_branco", (0.85, 0.85, 0.85), 0.9))
    o = juntar(n, [t, t2])
    objs.append(o)
    n, bm = novo("fiacao")
    for i in range(4):
        pts = [Vector((x, 0.02 * i, -0.3 * (1 - (x / 3) ** 2) - i * 0.06)) for x in [k * 0.5 - 3 for k in range(13)]]
        for a, b in zip(pts, pts[1:]):
            d = b - a
            v = comum.cilindro(bm, (a + b) / 2, 0.012, d.length, 4, eixo="X")
            bmesh.ops.rotate(bm, verts=v, cent=(a + b) / 2, matrix=Matrix.Rotation(-math.atan2(d.z, d.x), 3, "Y"))
    objs.append(fechar(n, bm, mat("borracha", (0.06, 0.06, 0.06), 0.6), oclusao=0))
    n, bm = novo("oficina")  # bancada da Nita
    comum.caixa(bm, (0, 0.5, 0.85), (2.2, 0.9, 0.08))
    comum.caixa(bm, (0, 0.5, 0.42), (2.1, 0.85, 0.8))
    comum.caixa(bm, (0, 0.95, 1.6), (2.2, 0.05, 1.4))
    for i in range(5):
        comum.caixa(bm, (-0.8 + i * 0.4, 0.9, 1.5 + (i % 2) * 0.3), (0.05, 0.05, 0.35))
    comum.cilindro(bm, (0.6, 0.4, 1.0), 0.2, 0.25, 14)  # ventilador desmontado
    objs.append(fechar(n, bm, mat("metal_oficina", (0.35, 0.33, 0.3), 0.6, 0.5), sujeira=(0.3, 0.2, 0.1), forca_sujeira=0.9))
    n, bm = novo("banca_filtros")
    comum.caixa(bm, (0, 0.4, 0.5), (1.6, 0.7, 1.0))
    for i in range(6):
        comum.cilindro(bm, (-0.6 + i * 0.24, 0.3, 1.08), 0.08, 0.16, 10)
    objs.append(fechar(n, bm, mat("chapa_remendada", (0.4, 0.38, 0.32), 0.7, 0.4), ruido=0.02, sujeira=(0.45, 0.25, 0.1), forca_sujeira=1.0))
    return objs


# ------------------------------------------------------------------ capela

def kit_capela():
    objs = []
    tijolo = mat("tijolo_capela", (0.52, 0.33, 0.24), 0.9)
    n, bm = novo("piso_capela")
    comum.caixa(bm, (0, 4, -0.25), (6.0, 14.0, 0.5))
    for i in range(7):
        comum.caixa(bm, (-2.6 + i * 0.86, 3.0, 0.005), (0.8, 8.0, 0.01))
    objs.append(fechar(n, bm, mat("ladrilho_capela", (0.5, 0.36, 0.28), 0.8), ruido=0.005, sujeira=(0.3, 0.22, 0.18), forca_sujeira=0.8, oclusao=0))
    n, bm = novo("parede_capela")  # 6 m x 9 m
    comum.caixa(bm, (0, 0.3, 4.5), (6, 0.6, 9))
    for z in (2.2, 5.0, 7.8):
        comum.caixa(bm, (0, -0.03, z), (6, 0.1, 0.12))
    objs.append(fechar(n, bm, tijolo, bisel=0.015, ruido=0.015, forca_sujeira=0.7))
    n, bm = novo("vitral")  # janela de garrafas, 2,4 x 3 m
    comum.caixa(bm, (0, 0.1, 1.5), (2.6, 0.2, 3.2))
    o1 = fechar(n + "_moldura", bm, mat("madeira_escura", (0.3, 0.2, 0.12)), oclusao=0)
    pecas = [o1]
    cores = [(0.2, 0.55, 0.3), (0.65, 0.35, 0.1), (0.25, 0.35, 0.7), (0.75, 0.6, 0.15), (0.6, 0.15, 0.15)]
    for c_i, cor in enumerate(cores):
        nn, bm = novo(f"garrafas{c_i}")
        for ix in range(10):
            for iz in range(13):
                if (ix * 7 + iz * 3 + c_i) % 5 != 0:
                    continue
                comum.cilindro(bm, (-1.08 + ix * 0.24, -0.01, 0.2 + iz * 0.22), 0.095, 0.06, 10, eixo="Y")
        pecas.append(fechar(nn, bm, mat(f"vidro_vitral{c_i}", cor, 0.2, emissao=cor, forca=2.5), oclusao=0))
    objs.append(juntar(n, pecas))
    n, bm = novo("banco_madeira")
    comum.caixa(bm, (0, 0.25, 0.45), (2.4, 0.45, 0.06))
    comum.caixa(bm, (0, 0.47, 0.8), (2.4, 0.05, 0.6))
    for x in (-1.1, 1.1):
        comum.caixa(bm, (x, 0.25, 0.25), (0.08, 0.45, 0.5))
    objs.append(fechar(n, bm, mat("madeira_reaproveitada", (0.42, 0.3, 0.18)), bisel=0.008, sujeira=(0.28, 0.22, 0.15), forca_sujeira=0.8))
    n, bm = novo("altar")
    comum.caixa(bm, (0, 0.5, 0.5), (2.6, 1.0, 1.0))
    comum.caixa(bm, (0, 0.5, 1.03), (2.8, 1.1, 0.06))
    o1 = fechar(n + "_mesa", bm, mat("pedra_altar", (0.6, 0.56, 0.5), 0.8), bisel=0.02, ruido=0.01)
    pecas = [o1]
    nn, bm = novo("fotos_altar")
    for i in range(5):
        v = comum.caixa(bm, (-1 + i * 0.5, 0.75, 1.3), (0.34, 0.02, 0.25))
        bmesh.ops.rotate(bm, verts=v, cent=(-1 + i * 0.5, 0.75, 1.3), matrix=Matrix.Rotation(-0.2, 3, "X"))
    pecas.append(fechar(nn, bm, mat("ceu_azul", (0.45, 0.7, 0.95), 0.6, emissao=(0.35, 0.6, 0.9), forca=1.2), oclusao=0))
    nn, bm = novo("velas")
    for i in range(7):
        comum.cilindro(bm, (-1.2 + i * 0.4, 0.25, 1.15), 0.03, 0.18 + (i % 3) * 0.06, 8)
    pecas.append(fechar(nn, bm, mat("vela", (0.9, 0.85, 0.7), 0.6, emissao=(1, 0.6, 0.2), forca=1.5), oclusao=0))
    nn, bm = novo("sol_altar")
    comum.cilindro(bm, (0, 0.95, 3.2), 0.6, 0.06, 24, eixo="Y")
    for i in range(12):
        a = i * math.pi / 6
        v = comum.caixa(bm, (math.cos(a) * 0.95, 0.95, 3.2 + math.sin(a) * 0.95), (0.5, 0.04, 0.08))
        bmesh.ops.rotate(bm, verts=v, cent=(math.cos(a) * 0.95, 0.95, 3.2 + math.sin(a) * 0.95), matrix=Matrix.Rotation(-a, 3, "Y"))
    pecas.append(fechar(nn, bm, mat("ouro_gasto", (0.75, 0.58, 0.25), 0.4, 0.8, emissao=(0.5, 0.35, 0.1), forca=0.6), oclusao=0))
    objs.append(juntar(n, pecas))
    n, bm = novo("facho")  # cone de luz que imita o sol, 9 m de altura, transparente
    comum.cilindro(bm, (0, 0, 4.5), 1.8, 9, 20, raio_topo=0.5)
    o = comum.objeto_de_bmesh(n, bm)
    comum.atribuir(o, mat("facho_luz", (1, 0.9, 0.6), 1.0, emissao=(1, 0.85, 0.55), forca=1.2, alfa=0.12))
    objs.append(o)
    n, bm = novo("maquina_velha")
    comum.cilindro(bm, (0, 1.2, 2.2), 1.8, 0.35, 28, eixo="Y")
    comum.cilindro(bm, (0, 1.2, 2.2), 0.3, 1.0, 12, eixo="Y")
    comum.caixa(bm, (0, 1.2, 0.5), (3.2, 1.6, 1.0))
    for i in range(6):
        a = i * math.pi / 3
        v = comum.caixa(bm, (math.cos(a) * 0.9, 0.95, 2.2 + math.sin(a) * 0.9), (1.6, 0.12, 0.14))
        bmesh.ops.rotate(bm, verts=v, cent=(math.cos(a) * 0.9, 0.95, 2.2 + math.sin(a) * 0.9), matrix=Matrix.Rotation(-a, 3, "Y"))
    objs.append(fechar(n, bm, mat("ferro_velho", (0.3, 0.26, 0.22), 0.7, 0.6), bisel=0.01, sujeira=(0.5, 0.28, 0.1), forca_sujeira=1.0))
    n, bm = novo("porta_capela")
    comum.caixa(bm, (-1.4, 0.3, 2.0), (0.6, 0.6, 4.0))
    comum.caixa(bm, (1.4, 0.3, 2.0), (0.6, 0.6, 4.0))
    comum.caixa(bm, (0, 0.3, 4.2), (3.4, 0.6, 0.5))
    o1 = fechar(n + "_moldura", bm, tijolo, bisel=0.015, ruido=0.01)
    t = texto("CAPELA DA VIGÍLIA", 0.22)
    t.location = (0, -0.02, 4.1)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("ouro_gasto", (0.75, 0.58, 0.25), 0.4, 0.8, emissao=(0.5, 0.35, 0.1), forca=0.6))
    objs.append(juntar(n, [o1, t]))
    return objs


# ------------------------------------------------------------------ túnel (Duto Norte)

def kit_tunel():
    objs = []
    concreto = mat("concreto_tunel", (0.34, 0.33, 0.31), 0.85)
    n, bm = novo("tunel_segmento")  # 6 m de comprimento: chão, arco de fundo e teto, aberto para a câmera
    comum.caixa(bm, (0, 3, -0.25), (6, 7, 0.5))
    segs = 10
    for i in range(segs + 1):
        a = math.pi * i / segs
        y = 3.0 + math.cos(a) * 3.2
        z = math.sin(a) * 4.2 + 0.3
        if y < 2.0:
            continue
        v = comum.caixa(bm, (0, y, z), (6, 0.5, 1.4))
        bmesh.ops.rotate(bm, verts=v, cent=(0, y, z), matrix=Matrix.Rotation(-(a - math.pi / 2), 3, "X"))
    for x in (-3, 3):
        comum.caixa(bm, (x * 0.98, 4.5, 2.4), (0.25, 4.0, 4.8))
    objs.append(fechar(n, bm, concreto, ruido=0.04, escala_ruido=1.2, sujeira=(0.25, 0.3, 0.22), forca_sujeira=1.0))
    n, bm = novo("trilho")
    for y in (1.6, 3.0):
        comum.caixa(bm, (0, y, 0.08), (6, 0.08, 0.12))
    for i in range(10):
        comum.caixa(bm, (-2.7 + i * 0.6, 2.3, 0.03), (0.25, 2.0, 0.08))
    objs.append(fechar(n, bm, mat("ferro_trilho", (0.3, 0.24, 0.2), 0.6, 0.7), sujeira=(0.45, 0.25, 0.1), forca_sujeira=1.0, oclusao=0))
    n, bm = novo("rocha_caverna")  # bloco irregular de 3 m
    comum.esfera(bm, (0, 1.0, 1.0), 1.5, 12, 8)
    objs.append(fechar(n, bm, mat("rocha_caverna", (0.32, 0.3, 0.28), 0.95), ruido=0.4, escala_ruido=0.7, suave=60))
    n, bm = novo("estalactite")
    comum.cilindro(bm, (0, 0, -0.6), 0.25, 1.2, 8, raio_topo=0.02)
    o = fechar(n, bm, mat("rocha_caverna", (0.32, 0.3, 0.28), 0.95), ruido=0.04, escala_ruido=3, oclusao=0)
    o.data.transform(Matrix.Rotation(math.pi, 4, "X"))
    objs.append(o)
    n, bm = novo("musgo")  # mancha luminosa
    for i in range(14):
        comum.esfera(bm, (R.uniform(-0.8, 0.8), R.uniform(-0.05, 0.05), R.uniform(-0.4, 0.4)), R.uniform(0.06, 0.16), 6, 4)
    objs.append(fechar(n, bm, mat("musgo_luz", (0.3, 0.9, 0.7), 0.9, emissao=(0.2, 0.9, 0.65), forca=2.2), oclusao=0))
    n, bm = novo("placa_metro")
    comum.caixa(bm, (0, 0, 0), (2.6, 0.05, 0.5))
    o1 = fechar(n + "_chapa", bm, mat("esmalte_azul", (0.15, 0.25, 0.45), 0.5, 0.3), sujeira=(0.4, 0.3, 0.2), forca_sujeira=0.9, oclusao=0)
    t = texto("ESTAÇÃO NORTE", 0.22)
    t.location = (0, -0.03, -0.08)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("esmalte_branco", (0.85, 0.85, 0.8), 0.5))
    objs.append(juntar(n, [o1, t]))
    n, bm = novo("vagao")  # vagão abandonado, 12 m
    comum.caixa(bm, (0, 1.4, 1.9), (12, 2.8, 2.9))
    for i in range(6):
        comum.caixa(bm, (-5 + i * 2, -0.01, 2.3), (1.0, 0.05, 0.9))
    objs.append(fechar(n, bm, mat("vagao", (0.35, 0.4, 0.38), 0.6, 0.5), bisel=0.05, ruido=0.03, sujeira=(0.45, 0.25, 0.12), forca_sujeira=1.0))
    return objs


# ------------------------------------------------------------------ eclusa (Boca do Poço)

def kit_eclusa():
    objs = []
    aco = mat("aco_painel", (0.36, 0.38, 0.4), 0.5, 0.7)
    n, bm = novo("parede_eclusa")  # 6 x 7 m
    comum.caixa(bm, (0, 0.3, 3.5), (6, 0.6, 7))
    for x in (-2, 0, 2):
        comum.caixa(bm, (x, -0.04, 3.5), (0.12, 0.1, 7))
    for z in (1.2, 4.5):
        comum.caixa(bm, (0, -0.04, z), (6, 0.1, 0.12))
    objs.append(fechar(n, bm, aco, bisel=0.01, sujeira=(0.45, 0.3, 0.2), forca_sujeira=0.8))
    n, bm = novo("piso_eclusa")
    comum.caixa(bm, (0, 3, -0.2), (6, 6, 0.4))
    objs.append(fechar(n, bm, mat("grade_metal", (0.3, 0.3, 0.3), 0.5, 0.7), sujeira=(0.45, 0.28, 0.12), forca_sujeira=0.8, oclusao=0))
    n, bm = novo("porta_eclusa")  # porta redonda de 3 m
    comum.cilindro(bm, (0, 0.3, 1.8), 1.8, 0.6, 32, eixo="Y")
    o1 = fechar(n + "_moldura", bm, mat("aco_escuro", (0.2, 0.2, 0.22), 0.5, 0.8), bisel=0.02)
    nn, bm = novo("porta_eclusa_folha")
    comum.cilindro(bm, (0, -0.05, 1.8), 1.4, 0.25, 32, eixo="Y")
    comum.cilindro(bm, (0, -0.2, 1.8), 0.45, 0.12, 6, eixo="Y")
    for i in range(4):
        a = i * math.pi / 2
        comum.caixa(bm, (math.cos(a) * 0.7, -0.22, 1.8 + math.sin(a) * 0.7), (0.15, 0.06, 0.15))
    o2 = fechar(nn, bm, mat("amarelo_risco", (0.75, 0.6, 0.12), 0.5, 0.5), sujeira=(0.4, 0.3, 0.15), forca_sujeira=0.8, oclusao=0)
    objs.append(juntar(n, [o1, o2]))
    n, bm = novo("chuveiro")
    comum.cilindro(bm, (0, 0.2, 1.4), 0.05, 2.8, 8)
    comum.cilindro(bm, (0, -0.1, 2.75), 0.25, 0.08, 14)
    comum.cilindro(bm, (0, 0.05, 2.8), 0.04, 0.4, 8, eixo="Y")
    objs.append(fechar(n, bm, mat("cromado_velho", (0.6, 0.6, 0.6), 0.3, 0.9), oclusao=0))
    n, bm = novo("armario_epi")  # 3 portas, 2 m
    comum.caixa(bm, (0, 0.3, 1.0), (1.8, 0.6, 2.0))
    for i in range(3):
        comum.caixa(bm, (-0.6 + i * 0.6, -0.01, 1.0), (0.55, 0.03, 1.9))
        comum.caixa(bm, (-0.6 + i * 0.6 + 0.18, -0.04, 1.0), (0.04, 0.04, 0.2))
    objs.append(fechar(n, bm, mat("armario_verde", (0.25, 0.38, 0.3), 0.6, 0.6), bisel=0.008, sujeira=(0.4, 0.3, 0.2), forca_sujeira=0.8))
    n, bm = novo("luz_alerta")
    comum.cilindro(bm, (0, 0, 0.05), 0.12, 0.1, 12)
    o1 = fechar(n + "_base", bm, mat("aco_escuro", (0.2, 0.2, 0.22), 0.5, 0.8), oclusao=0)
    nn, bm = novo("luz_alerta_cupula")
    comum.esfera(bm, (0, 0, 0.16), 0.11, 12, 6)
    o2 = fechar(nn, bm, mat("luz_vermelha", (1, 0.15, 0.1), 0.3, emissao=(1, 0.1, 0.05), forca=6), oclusao=0)
    objs.append(juntar(n, [o1, o2]))
    n, bm = novo("painel_controle")
    comum.caixa(bm, (0, 0.2, 1.1), (1.0, 0.4, 0.8))
    o1 = fechar(n + "_corpo", bm, aco, bisel=0.01)
    pecas = [o1]
    for i, cor in enumerate([(0.1, 1, 0.2), (1, 0.6, 0.1), (1, 0.1, 0.1)]):
        nn, bm = novo(f"led{i}")
        for k in range(3):
            comum.caixa(bm, (-0.3 + k * 0.3, -0.01, 1.3 - i * 0.18), (0.08, 0.02, 0.06))
        pecas.append(fechar(nn, bm, mat(f"led{i}", cor, 0.3, emissao=cor, forca=3), oclusao=0))
    objs.append(juntar(n, pecas))
    n, bm = novo("placa_eclusa")
    comum.caixa(bm, (0, 0, 0), (2.4, 0.04, 0.6))
    o1 = fechar(n + "_chapa", bm, mat("amarelo_risco", (0.75, 0.6, 0.12), 0.5, 0.5), oclusao=0)
    t = texto("ECLUSA · USE O EPI", 0.17)
    t.location = (0, -0.03, -0.06)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("plastico_preto", (0.08, 0.08, 0.09), 0.4))
    objs.append(juntar(n, [o1, t]))
    return objs


# ------------------------------------------------------------------ superfície

def kit_superficie():
    objs = []
    areia = mat("areia_cinza", (0.68, 0.62, 0.52), 0.95)
    n, bm = novo("chao_areia")  # 10 m x 40 m de profundidade, ondulado no fundo
    comum.caixa(bm, (0, 18, -0.3), (10, 40, 0.6))
    o = fechar(n, bm, areia, oclusao=0, sujeira=(0.55, 0.5, 0.42), forca_sujeira=0.6)
    for v in o.data.vertices:
        if v.co.z > 0 and v.co.y > 3:
            v.co.z += (noise.noise(Vector((v.co.x * 0.15, v.co.y * 0.1, 0))) + 0.4) * min(1.0, (v.co.y - 3) / 10) * 1.5
    objs.append(o)
    concreto = mat("concreto_queimado", (0.55, 0.52, 0.48), 0.95)

    def predio(nome, w, h, andares, quebrado=0.3):
        _, bm = novo(nome)
        d = 6
        espess = 0.3
        comum.caixa(bm, (-w / 2 + espess / 2, d / 2, h / 2), (espess, d, h))
        comum.caixa(bm, (0, d - espess / 2, h / 2), (w, espess, h))
        alt_dir = h * (1 - quebrado)
        comum.caixa(bm, (w / 2 - espess / 2, d / 2, alt_dir / 2), (espess, d, alt_dir))
        for i in range(1, andares + 1):
            z = i * h / (andares + 1)
            larg = w if z < alt_dir else w * 0.6
            comum.caixa(bm, (-w / 2 + larg / 2, d / 2, z), (larg, d, 0.25))
        for i in range(int(w / 2)):
            for j in range(andares + 1):
                z = (j + 0.5) * h / (andares + 1)
                if z < h - 0.5:
                    comum.caixa(bm, (-w / 2 + 1 + i * 2, d - 0.4, z), (0.9, 0.2, 1.1))
        return fechar(nome, bm, concreto, bisel=0.04, ruido=0.08, escala_ruido=0.9, sujeira=(0.3, 0.27, 0.24), forca_sujeira=1.0)

    objs.append(predio("predio_ruina_a", 8, 12, 3))
    objs.append(predio("predio_ruina_b", 6, 8, 2, 0.45))
    objs.append(predio("predio_ruina_c", 10, 18, 5, 0.2))
    n, bm = novo("carro_soterrado")
    comum.caixa(bm, (0, 1.0, 0.35), (4.2, 1.8, 0.9))
    comum.caixa(bm, (-0.2, 1.0, 1.05), (2.2, 1.6, 0.6))
    for x in (-1.4, 1.4):
        comum.cilindro(bm, (x, 0.1, 0.15), 0.35, 0.25, 12, eixo="Y")
    o = fechar(n, bm, mat("carro_ferrugem", (0.45, 0.25, 0.15), 0.8, 0.4), bisel=0.06, ruido=0.05, sujeira=(0.6, 0.55, 0.45), forca_sujeira=0.9)
    o.data.transform(Matrix.Rotation(0.08, 4, "Y"))
    objs.append(o)
    n, bm = novo("poste")
    v = comum.cilindro(bm, (0, 0.5, 3), 0.1, 6, 8)
    bmesh.ops.rotate(bm, verts=v, cent=(0, 0.5, 0), matrix=Matrix.Rotation(0.25, 3, "Y"))
    objs.append(fechar(n, bm, mat("ferro_trilho", (0.3, 0.24, 0.2), 0.6, 0.7), sujeira=(0.45, 0.25, 0.1), forca_sujeira=1.0, oclusao=0))
    n, bm = novo("antena")  # torre treliçada de 42 m
    alt = 42
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4
        comum.cilindro(bm, (math.cos(a) * 1.6, 1.6 + math.sin(a) * 1.6, alt / 2), 0.09, alt, 6, raio_topo=0.09)
    for k in range(14):
        z = 1 + k * 3
        esc = 1.0 - z / alt * 0.6
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            b = a + math.pi / 2
            p1 = Vector((math.cos(a) * 1.6 * esc, 1.6 + math.sin(a) * 1.6 * esc, z))
            p2 = Vector((math.cos(b) * 1.6 * esc, 1.6 + math.sin(b) * 1.6 * esc, z + 1.5))
            meio = (p1 + p2) / 2
            d = p2 - p1
            v = comum.cilindro(bm, meio, 0.04, d.length, 4)
            eixo = Vector((0, 0, 1)).cross(d.normalized())
            if eixo.length > 1e-6:
                bmesh.ops.rotate(bm, verts=v, cent=meio, matrix=Matrix.Rotation(Vector((0, 0, 1)).angle(d), 3, eixo.normalized()))
    o1 = fechar(n + "_torre", bm, mat("aco_antena", (0.45, 0.2, 0.15), 0.6, 0.7), sujeira=(0.6, 0.55, 0.45), forca_sujeira=0.8, oclusao=0)
    o1.data.transform(Matrix.Diagonal((1, 1, 1, 1)))
    for v in o1.data.vertices:  # afunila
        f = 1.0 - v.co.z / alt * 0.6
        v.co.x *= f
        v.co.y = 1.6 + (v.co.y - 1.6) * f
    nn, bm = novo("antena_luz")
    comum.esfera(bm, (0, 1.6, alt + 0.3), 0.3, 10, 6)
    o2 = fechar(nn, bm, mat("luz_vermelha", (1, 0.15, 0.1), 0.3, emissao=(1, 0.1, 0.05), forca=6), oclusao=0)
    nn, bm = novo("antena_cabine")
    comum.caixa(bm, (2.8, 0.8, 1.2), (2.4, 2.0, 2.4))
    o3 = fechar(nn, bm, concreto, bisel=0.03, ruido=0.04)
    objs.append(juntar(n, [o1, o2, o3]))
    n, bm = novo("marco")  # obelisco de concreto com placa
    comum.caixa(bm, (0, 0.6, 0.3), (2.0, 2.0, 0.6))
    comum.cilindro(bm, (0, 0.6, 2.6), 0.55, 4.2, 4, raio_topo=0.25)
    o1 = fechar(n + "_pedra", bm, concreto, bisel=0.03, ruido=0.03)
    o1.data.transform(Matrix.Translation((0, 0, 0)))
    t = texto("MARCO 0 · KM 12", 0.16)
    t.location = (0, -0.42, 0.95)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("bronze", (0.5, 0.35, 0.2), 0.4, 0.8))
    objs.append(juntar(n, [o1, t]))
    n, bm = novo("duna")  # rampa de areia de 8 m, 1,6 m de altura
    v = comum.esfera(bm, (0, 2, 0), 1.0, 16, 8)
    o = fechar(n, bm, areia, oclusao=0, forca_sujeira=0.5)
    for vv in o.data.vertices:
        vv.co.x *= 4.5
        vv.co.y *= 3
        vv.co.z = max(-0.2, vv.co.z * 1.7)
    objs.append(o)
    _ = v
    n, bm = novo("cerca")
    for i in range(5):
        comum.caixa(bm, (-2 + i, 0, 0.6), (0.06, 0.06, 1.2))
    for z in (0.4, 0.9):
        comum.cilindro(bm, (0, 0, z), 0.01, 4.2, 4, eixo="X")
    objs.append(fechar(n, bm, mat("ferro_trilho", (0.3, 0.24, 0.2), 0.6, 0.7), oclusao=0))
    n, bm = novo("placa_estrada")
    comum.cilindro(bm, (0, 0, 1.2), 0.05, 2.4, 6)
    v = comum.caixa(bm, (0, -0.05, 2.4), (1.2, 0.04, 0.6))
    bmesh.ops.rotate(bm, verts=v, cent=(0, -0.05, 2.4), matrix=Matrix.Rotation(0.2, 3, "Y"))
    o1 = fechar(n + "_poste", bm, mat("esmalte_verde", (0.15, 0.35, 0.2), 0.6, 0.3), sujeira=(0.6, 0.55, 0.45), forca_sujeira=1.0, oclusao=0)
    t = texto("QARAR 340", 0.14)
    t.location = (0, -0.08, 2.35)
    bpy.context.view_layer.objects.active = t
    t.select_set(True)
    bpy.ops.object.transform_apply(location=True)
    comum.atribuir(t, mat("esmalte_branco", (0.85, 0.85, 0.8), 0.5))
    objs.append(juntar(n, [o1, t]))
    n, bm = novo("skyline")  # silhueta de cidade distante, 60 m
    for i in range(14):
        h = R.uniform(10, 45)
        w = R.uniform(3, 7)
        comum.caixa(bm, (-30 + i * 4.4, 2, h / 2), (w, 4, h))
    objs.append(fechar(n, bm, mat("silhueta", (0.5, 0.47, 0.42), 1.0), oclusao=0, forca_sujeira=0.2))
    n, bm = novo("rocha")
    comum.esfera(bm, (0, 0.6, 0.4), 0.8, 10, 6)
    objs.append(fechar(n, bm, mat("rocha_sup", (0.45, 0.42, 0.38), 0.95), ruido=0.25, escala_ruido=1.2, suave=60))
    n, bm = novo("sucata_pilha")
    for i in range(14):
        comum.caixa(bm, (R.uniform(-1.2, 1.2), R.uniform(0, 1.4), R.uniform(0.1, 0.8)),
                    (R.uniform(0.3, 1.0), R.uniform(0.2, 0.8), R.uniform(0.05, 0.4)), R.uniform(0, 3))
    objs.append(fechar(n, bm, mat("carro_ferrugem", (0.45, 0.25, 0.15), 0.8, 0.4), sujeira=(0.6, 0.55, 0.45), forca_sujeira=0.9))
    n, bm = novo("escotilha_superficie")  # saída do poço no chão da superfície
    comum.cilindro(bm, (0, 1.0, 0.4), 1.4, 0.8, 20)
    comum.caixa(bm, (0, 1.0, 1.4), (2.8, 2.4, 0.2))
    for x in (-1.2, 1.2):
        comum.caixa(bm, (x, 1.0, 0.8), (0.2, 2.2, 1.2))
    objs.append(fechar(n, bm, mat("aco_escuro", (0.2, 0.2, 0.22), 0.5, 0.8), bisel=0.03, sujeira=(0.6, 0.55, 0.45), forca_sujeira=0.9))
    return objs


KITS = {
    "comum": kit_comum, "cisterna": kit_cisterna, "gueto": kit_gueto, "capela": kit_capela,
    "tunel": kit_tunel, "eclusa": kit_eclusa, "superficie": kit_superficie,
}


def gerar(nome: str) -> None:
    comum.limpar_cena()
    M.clear()
    objs = KITS[nome]()
    for o in objs:
        o.location = (0, 0, 0)
    comum.exportar_glb(os.path.join(SAIDA, f"{nome}.glb"), selecionados=objs)


if __name__ == "__main__":
    for k in (comum.argumentos() or list(KITS)):
        gerar(k)
