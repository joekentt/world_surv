"""Funções compartilhadas pelos scripts de geração de assets.

Roda tanto no Blender (`blender -b -P script.py -- args`) quanto no módulo
`bpy` do PyPI (`python script.py args`). Nenhum asset é modelado à mão:
tudo o que sai em public/assets/ é gerado por estes scripts.
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy  # precisa vir antes de bmesh no módulo bpy do PyPI
import bmesh
from mathutils import Matrix, Vector, noise

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(RAIZ, "public", "assets")


def argumentos() -> list[str]:
    """Argumentos depois de '--' (Blender) ou de sys.argv[1:] (módulo bpy)."""
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return sys.argv[1:]


def limpar_cena() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for colecao in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                    bpy.data.actions, bpy.data.images, bpy.data.textures):
        for item in list(colecao):
            colecao.remove(item)


def semente(valor: int) -> random.Random:
    random.seed(valor)
    return random.Random(valor)


# ---------------------------------------------------------------- materiais

def lin(cor) -> tuple:
    """Converte uma cor sRGB (como escolhida a olho) para linear, que é o que o glTF espera."""
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(f(float(c)) for c in cor[:3])


def material(nome: str, cor, rugosidade: float = 0.8, metal: float = 0.0,
             emissao=None, forca_emissao: float = 0.0, alfa: float = 1.0) -> bpy.types.Material:
    """Material PBR simples (Principled BSDF), exportado como glTF metallic-roughness.

    Usa a cor de vértice (atributo "Col") como multiplicador da cor base, para que
    o desgaste e a oclusão gerados por script cheguem ao glTF como COLOR_0.
    """
    mat = bpy.data.materials.get(nome)
    if mat:
        return mat
    mat = bpy.data.materials.new(nome)
    mat.use_nodes = True
    nos = mat.node_tree.nodes
    bsdf = nos.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*lin(cor), 1.0)
    bsdf.inputs["Roughness"].default_value = rugosidade
    bsdf.inputs["Metallic"].default_value = metal
    if emissao is not None:
        bsdf.inputs["Emission Color"].default_value = (*lin(emissao), 1.0)
        bsdf.inputs["Emission Strength"].default_value = forca_emissao
    if alfa < 1.0:
        bsdf.inputs["Alpha"].default_value = alfa
        mat.surface_render_method = "BLENDED"
    return mat


def atribuir(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ---------------------------------------------------------------- malhas

def objeto_de_bmesh(nome: str, bm: bmesh.types.BMesh, colecao=None) -> bpy.types.Object:
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    (colecao or bpy.context.scene.collection).objects.link(obj)
    return obj


def caixa(bm: bmesh.types.BMesh, centro, tamanho, rot_z: float = 0.0) -> list:
    """Adiciona uma caixa ao bmesh. tamanho = (x, y, z) em metros (Z para cima no Blender)."""
    mat = Matrix.Translation(Vector(centro)) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((*tamanho, 1.0))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
    return res["verts"]


def cilindro(bm, centro, raio, altura, segmentos=12, eixo="Z", raio_topo=None):
    rot = Matrix.Identity(4)
    if eixo == "X":
        rot = Matrix.Rotation(math.pi / 2, 4, "Y")
    elif eixo == "Y":
        rot = Matrix.Rotation(math.pi / 2, 4, "X")
    mat = Matrix.Translation(Vector(centro)) @ rot
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segmentos, radius1=raio,
                                radius2=raio if raio_topo is None else raio_topo,
                                depth=altura, matrix=mat)
    return res["verts"]


def esfera(bm, centro, raio, seg=12, aneis=8):
    mat = Matrix.Translation(Vector(centro))
    res = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=aneis, radius=raio, matrix=mat)
    return res["verts"]


def deformar_ruido(obj, escala: float = 1.5, forca: float = 0.03, semente_ruido: float = 0.0) -> None:
    """Desloca vértices com ruído para quebrar a regularidade (concreto, rocha, chapa amassada)."""
    for v in obj.data.vertices:
        p = v.co * escala + Vector((semente_ruido, semente_ruido * 0.7, 0))
        v.co += Vector((noise.noise(p), noise.noise(p + Vector((5.2, 1.3, 0))), noise.noise(p + Vector((1.7, 9.2, 3.1))))) * forca


def biselar(obj, largura: float = 0.02, segmentos: int = 1) -> None:
    mod = obj.modifiers.new("bisel", "BEVEL")
    mod.width = largura
    mod.segments = segmentos
    mod.limit_method = "ANGLE"


def subdividir(obj, niveis: int = 1) -> None:
    mod = obj.modifiers.new("subsurf", "SUBSURF")
    mod.levels = niveis
    mod.render_levels = niveis


def aplicar_modificadores(obj) -> None:
    bpy.context.view_layer.objects.active = obj
    deps = bpy.context.evaluated_depsgraph_get()
    avaliado = obj.evaluated_get(deps)
    malha = bpy.data.meshes.new_from_object(avaliado)
    obj.modifiers.clear()
    antigo = obj.data
    obj.data = malha
    bpy.data.meshes.remove(antigo)


def suavizar(obj, angulo_graus: float = 40.0) -> None:
    """Shading suave com corte por ângulo (Blender 4.1+: sharp_edge por ângulo)."""
    malha = obj.data
    for p in malha.polygons:
        p.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(malha)
    limite = math.radians(angulo_graus)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > limite:
            e.smooth = False
    bm.to_mesh(malha)
    bm.free()


def cor_vertice_desgaste(obj, base=(1, 1, 1), sujeira=(0.55, 0.5, 0.45), escala: float = 0.8,
                         forca: float = 0.5, oclusao_chao: float = 0.35, semente_ruido: float = 0.0) -> None:
    """Pinta COLOR_0 com sujeira por ruído e escurecimento perto do chão (oclusão falsa)."""
    malha = obj.data
    if "Col" not in malha.color_attributes:
        malha.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    attr = malha.color_attributes["Col"]
    mw = obj.matrix_world
    for poli in malha.polygons:
        for li in poli.loop_indices:
            vi = malha.loops[li].vertex_index
            p = mw @ malha.vertices[vi].co
            n = noise.fractal(p * escala + Vector((semente_ruido, 0, 0)), 0.5, 2.0, 3)
            t = max(0.0, min(1.0, 0.5 + n * forca))
            chao = max(0.0, 1.0 - p.z / 1.2) * oclusao_chao
            cor = [base[i] * (1 - t) + sujeira[i] * t for i in range(3)]
            cor = [c * (1 - chao) for c in cor]
            attr.data[li].color = (*lin(cor), 1.0)


# ---------------------------------------------------------------- exportação

def exportar_glb(caminho: str, selecionados: list | None = None, animacoes: bool = False,
                 cores_vertice: bool = True, skins: bool = True) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if selecionados is not None:
        bpy.ops.object.select_all(action="DESELECT")
        for o in selecionados:
            o.select_set(True)
    opcoes = dict(
        filepath=caminho,
        export_format="GLB",
        use_selection=selecionados is not None,
        export_apply=False,
        export_yup=True,
        export_animations=animacoes,
        export_skins=skins,
        export_morph=False,
        export_materials="EXPORT",
        export_extras=True,
    )
    # A opção de cor de vértice mudou de nome entre versões do exportador.
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    if "export_vertex_color" in props:
        opcoes["export_vertex_color"] = "ACTIVE" if cores_vertice else "NONE"
    elif "export_colors" in props:
        opcoes["export_colors"] = cores_vertice
    if animacoes and "export_animation_mode" in props:
        opcoes["export_animation_mode"] = "ACTIONS"
    bpy.ops.export_scene.gltf(**opcoes)
    print(f"[exportado] {os.path.relpath(caminho, RAIZ)} ({os.path.getsize(caminho) / 1024:.0f} KB)")
