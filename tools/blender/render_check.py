"""Renderiza um GLB em três vistas (frente, lado e 3/4) e salva uma imagem única para validação.

Uso:
    python tools/blender/render_check.py <arquivo.glb> <saida.png> [--pose <acao>] [--quadro N]
                                         [--ocultar prefixo1,prefixo2] [--perto]

--pose aplica uma ação de um GLB de animações (public/assets/personagens/animacoes.glb)
ao esqueleto, para conferir deformação. --perto enquadra só a cabeça.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import comum  # noqa: E402


def opcao(args, nome, padrao=None):
    if nome in args:
        i = args.index(nome)
        return args[i + 1]
    return padrao


def principal() -> None:
    args = comum.argumentos()
    entrada, saida = os.path.abspath(args[0]), os.path.abspath(args[1])
    perto = "--perto" in args
    ocultar = [p for p in (opcao(args, "--ocultar", "") or "").split(",") if p]
    comum.limpar_cena()
    bpy.ops.import_scene.gltf(filepath=entrada)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.endswith("_lod1")
            and not o.name.lower().startswith("icosphere")]
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o not in objs:
            o.hide_render = True
    for o in objs:
        if any(o.name.startswith(p) for p in ocultar):
            o.hide_render = True
    pose = opcao(args, "--pose")
    if pose:
        aplicar_pose(pose, int(opcao(args, "--quadro", "1")))
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.hide_render:
            continue
        ev = o.evaluated_get(deps)
        m = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()
    arr = np.array([tuple(p) for p in pts])
    mn, mx = arr.min(axis=0), arr.max(axis=0)
    centro = Vector(((mn + mx) / 2).tolist())
    altura = float(mx[2] - mn[2])
    if perto:
        topo = float(mx[2])
        centro = Vector((centro.x, centro.y, topo - 0.13))
        altura = 0.32

    cena = bpy.context.scene
    cena.render.engine = "CYCLES"
    cena.cycles.device = "CPU"
    cena.cycles.samples = 24
    cena.cycles.use_denoising = False
    cena.render.resolution_x = 420
    cena.render.resolution_y = 640
    cena.render.film_transparent = False
    mundo = bpy.data.worlds.new("mundo")
    cena.world = mundo
    mundo.use_nodes = True
    mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.33, 0.36, 1)
    mundo.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    for nome, rot, energia in (("chave", (0.9, 0.0, -0.6), 3.5), ("recorte", (1.2, 0.0, 2.6), 2.0)):
        luz = bpy.data.lights.new(nome, "SUN")
        luz.energy = energia
        o = bpy.data.objects.new(nome, luz)
        o.rotation_euler = rot
        cena.collection.objects.link(o)
    cam_dados = bpy.data.cameras.new("cam")
    cam_dados.type = "ORTHO"
    cam_dados.ortho_scale = altura * 1.15
    cam = bpy.data.objects.new("cam", cam_dados)
    cena.collection.objects.link(cam)
    cena.camera = cam
    # Exportado em glTF e reimportado: o personagem continua olhando para -Y.
    vistas = {"frente": Vector((0, -1, 0)), "lado": Vector((1, 0, 0)), "tres_quartos": Vector((0.7, -0.7, 0)).normalized()}
    imagens = []
    tmp = saida + ".tmp"
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    for nome, direcao in vistas.items():
        cam.location = centro + direcao * 6
        cam.rotation_euler = (direcao * -1).to_track_quat("-Z", "Y").to_euler()
        cena.render.filepath = f"{tmp}_{nome}.png"
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(cena.render.filepath)
        px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
        imagens.append(px)
        bpy.data.images.remove(img)
        os.remove(cena.render.filepath)
    junta = np.concatenate(imagens, axis=1)
    out = bpy.data.images.new("check", junta.shape[1], junta.shape[0], alpha=True)
    out.pixels = junta.ravel()
    out.filepath_raw = saida
    out.file_format = "PNG"
    out.save()
    print(f"[render_check] {saida}")


def aplicar_pose(acao: str, quadro: int) -> None:
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    lib = os.path.join(comum.ASSETS, "personagens", "animacoes.glb")
    antes = set(bpy.data.actions.keys())
    bpy.ops.import_scene.gltf(filepath=lib)
    novos = [o for o in bpy.context.scene.objects if o.type == "ARMATURE" and o != arm]
    alvo = None
    for a in bpy.data.actions:
        if a.name not in antes and a.name.split("_")[0] == acao.split("_")[0] and a.name.startswith(acao):
            alvo = a
            break
    if alvo is None:
        raise SystemExit(f"ação {acao} não encontrada")
    # copia a pose quadro a quadro, osso a osso (rotação local relativa ao repouso)
    fonte = novos[0]
    fonte.animation_data_create()
    fonte.animation_data.action = alvo
    if hasattr(fonte.animation_data, "action_slot") and alvo.slots:
        fonte.animation_data.action_slot = alvo.slots[0]
    bpy.context.scene.frame_set(quadro)
    for pb in arm.pose.bones:
        if pb.name in fonte.pose.bones:
            fb = fonte.pose.bones[pb.name]
            pb.rotation_mode = "QUATERNION"
            fb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = fb.rotation_quaternion
            if pb.name in ("pelvis",):
                pb.location = fb.location
    for o in list(bpy.context.scene.objects):
        if o in novos or (o.parent in novos):
            o.hide_render = True


if __name__ == "__main__":
    principal()
