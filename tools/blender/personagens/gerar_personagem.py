"""Gera um personagem completo (corpo, rig, rosto, cabelo, roupas e EPI) e exporta em GLB.

Uso:
    python tools/blender/personagens/gerar_personagem.py <id> [<id> ...]
    python tools/blender/personagens/gerar_personagem.py --todos

Lê a aparência de content/npcs/<id>.json. A malha base, os targets de modelagem,
o rig "game_engine" e os pesos vêm dos dados CC0 do MPFB2 (baixar com
baixar_dados_mpfb2.sh). O código do MPFB2 não é usado: este script reimplementa
o carregamento da malha, a mistura dos targets macro e a montagem do rig.

Coordenadas no Blender: Z para cima, personagem olhando para -Y, metros.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

import comum  # noqa: E402

DADOS = os.path.join(comum.RAIZ, ".cache", "mpfb2_data")
CACHE = os.path.join(comum.RAIZ, ".cache", "personagens")
NPCS = os.path.join(comum.RAIZ, "content", "npcs")
SAIDA = os.path.join(comum.ASSETS, "personagens")
RIG_NOME = "game_engine"

# ------------------------------------------------------------------ malha base

_base = None
_grupos = None


def grupos() -> dict:
    global _grupos
    if _grupos is None:
        with open(os.path.join(DADOS, "mesh_metadata", "basemesh_vertex_groups.json")) as f:
            _grupos = json.load(f)
    return _grupos


def indices_grupo(nome: str) -> np.ndarray:
    faixas = grupos()[nome]
    return np.concatenate([np.arange(a, b + 1) for a, b in faixas])


def carregar_base():
    """Lê base.obj (HM08). Retorna vértices (unidades MakeHuman, Y para cima) e faces por grupo."""
    global _base
    if _base is not None:
        return _base
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, "base.npz")
    if os.path.exists(cache):
        d = np.load(cache, allow_pickle=True)
        _base = (d["verts"], d["faces"].item())
        return _base
    verts, faces, grupo = [], {}, "default"
    with open(os.path.join(DADOS, "3dobjs", "base.obj")) as f:
        for linha in f:
            if linha.startswith("v "):
                verts.append([float(x) for x in linha.split()[1:4]])
            elif linha.startswith("g "):
                grupo = linha.split()[1]
            elif linha.startswith("f "):
                faces.setdefault(grupo, []).append([int(p.split("/")[0]) - 1 for p in linha.split()[1:]])
    verts = np.array(verts, dtype=np.float64)
    np.savez(cache, verts=verts, faces=np.array(faces, dtype=object))
    _base = (verts, faces)
    return _base


# ------------------------------------------------------------------ targets

_alvos: dict = {}
_indice_alvos: dict | None = None


def ler_alvo(rel: str):
    if rel in _alvos:
        return _alvos[rel]
    caminho = os.path.join(DADOS, "targets", rel + ".target.gz")
    idx, off = [], []
    with gzip.open(caminho, "rt") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or linha.startswith('"'):
                continue
            p = linha.split()
            idx.append(int(p[0]))
            off.append((float(p[1]), float(p[2]), float(p[3])))
    _alvos[rel] = (np.array(idx, dtype=np.int64), np.array(off, dtype=np.float64).reshape(-1, 3))
    return _alvos[rel]


def indice_alvos() -> dict:
    """nome do target -> caminho relativo (ex.: 'nose-volume-incr' -> 'nose/nose-volume-incr')."""
    global _indice_alvos
    if _indice_alvos is None:
        _indice_alvos = {}
        raiz = os.path.join(DADOS, "targets")
        for pasta in os.listdir(raiz):
            d = os.path.join(raiz, pasta)
            if not os.path.isdir(d) or pasta in ("macrodetails", "_images", "breast", "genitals", "expression"):
                continue
            for arq in os.listdir(d):
                if arq.endswith(".target.gz"):
                    _indice_alvos[arq[:-10]] = f"{pasta}/{arq[:-10]}"
    return _indice_alvos


with open(os.path.join(DADOS, "targets", "macrodetails", "macro.json")) as _f:
    MACRO = json.load(_f)


def componentes(nome: str, valor: float) -> list:
    """Mesma regra de interpolação do MakeHuman: cada faixa mistura dois extremos vizinhos."""
    saida = []
    for parte in MACRO["macrotargets"][nome]["parts"]:
        if parte["lowest"] < valor < parte["highest"]:
            pos = (valor - parte["lowest"]) / (parte["highest"] - parte["lowest"])
            if parte["low"]:
                saida.append((parte["low"], 1 - pos))
            if parte["high"]:
                saida.append((parte["high"], pos))
    return saida


def idade_para_valor(anos: float) -> float:
    """Escala de idade do MakeHuman: 0 = 1 ano, 0,1875 = 11, 0,5 = 25, 1 = 90."""
    if anos <= 11:
        return max(0.0, (anos - 1) / 10 * 0.1875)
    if anos <= 25:
        return 0.1875 + (anos - 11) / 14 * (0.5 - 0.1875)
    return min(1.0, 0.5 + (anos - 25) / 65 * 0.5)


def pilha_macro(info: dict, corte: float = 0.01) -> list:
    c = {n: componentes(n, info[n]) for n in ("gender", "age", "muscle", "weight", "proportions", "height")}
    alvos = []
    for raca, peso_raca in info["race"].items():
        if peso_raca <= 0.0001:
            continue
        for ida, wa in c["age"]:
            for gen, wg in c["gender"]:
                w = peso_raca * wa * wg
                if w > corte:
                    alvos.append((f"macrodetails/{raca}-{gen}-{ida}", w))
    for gen, wg in c["gender"]:
        for ida, wa in c["age"]:
            for mus, wm in c["muscle"]:
                for pes, wp in c["weight"]:
                    w = wg * wa * wm * wp
                    if w > corte:
                        alvos.append((f"macrodetails/universal-{gen}-{ida}-{mus}-{pes}", w))
                    for alt, wh in c["height"]:
                        w2 = w * wh
                        if w2 > corte:
                            alvos.append((f"macrodetails/height/{gen}-{ida}-{mus}-{pes}-{alt}", w2))
                    for pro, wr in c["proportions"]:
                        w2 = w * wr
                        if w2 > corte and ida != "baby":
                            alvos.append((f"macrodetails/proportions/{gen}-{ida}-{mus}-{pes}-{pro}", w2))
    return alvos


def resolver_alvo_rosto(chave: str, valor: float) -> list:
    """'nose-volume': 0.4 -> nose-volume-incr; -0.4 -> nose-volume-decr. Nomes completos também valem."""
    idx = indice_alvos()
    if "/" in chave:
        return [(chave, abs(valor))]
    if chave in idx:
        return [(idx[chave], abs(valor))]
    pares = [("-incr", "-decr"), ("-up", "-down"), ("-in", "-out"), ("-forward", "-backward"),
             ("-convex", "-concave"), ("-compress", "-uncompress")]
    for pos, neg in pares:
        nome = chave + (pos if valor >= 0 else neg)
        if nome in idx:
            return [(idx[nome], abs(valor))]
    print(f"[aviso] target de rosto desconhecido: {chave}")
    return []


# Variações de rosto sorteadas por semente, para que NPCs sem rosto definido não se repitam.
VARIACOES_ROSTO = [
    ("nose-volume", 0.6), ("nose-scale-horiz", 0.5), ("nose-scale-vert", 0.5), ("nose-hump", 0.6),
    ("nose-point-width", 0.5), ("nose-greek", 0.5), ("chin-prominent", 0.6), ("chin-width", 0.5),
    ("chin-height", 0.4), ("chin-jaw-drop", 0.4), ("head-square", 0.5), ("head-oval", 0.5), ("head-round", 0.5),
    ("head-fat", 0.4), ("mouth-scale-horiz", 0.4), ("mouth-upperlip-volume", 0.5), ("mouth-lowerlip-volume", 0.5),
    ("eye-scale", 0.3), ("eye-trans", 0.3), ("cheek-bones", 0.5), ("cheek-volume", 0.5),
    ("forehead-scale-vert", 0.4), ("eyebrows-angle", 0.5), ("ear-scale", 0.4),
]


ESTILO = {"head-scale-vert": 0.25, "head-scale-horiz": 0.15, "head-scale-depth": 0.15, "eye-scale": 0.15}


def alvos_rosto(apar: dict) -> list:
    rng = comum.semente(int(apar.get("semente", 1)))
    escolhas = dict(ESTILO)
    for k, v in apar.get("rosto", {}).items():
        escolhas[k] = escolhas.get(k, 0.0) + v
    sorteio = rng.sample(VARIACOES_ROSTO, 6)
    for chave, amp in sorteio:
        escolhas.setdefault(chave, rng.uniform(-amp, amp))
    saida = []
    for chave, valor in escolhas.items():
        if abs(valor) < 0.02:
            continue
        lados = [chave]
        if chave.split("-")[0] in ("eye", "ear", "cheek"):
            lados = ["l-" + chave, "r-" + chave]
        for c in lados:
            saida += resolver_alvo_rosto(c, valor)
    return saida


def vertices_personagem(apar: dict) -> np.ndarray:
    verts, _ = carregar_base()
    v = verts.copy()
    etnia = apar.get("etnia") or {"african": 0.33, "caucasian": 0.33, "asian": 0.33}
    info = {
        "gender": float(apar.get("genero", 0.5)),
        "age": idade_para_valor(float(apar.get("idade_anos", 25))),
        "muscle": float(apar.get("musculo", 0.5)),
        "weight": float(apar.get("peso", 0.5)),
        "proportions": float(apar.get("proporcoes", 0.5)),
        "height": float(apar.get("altura", 0.5)),
        "race": etnia,
    }
    for rel, w in pilha_macro(info) + alvos_rosto(apar):
        idx, off = ler_alvo(rel)
        v[idx] += w * off
    # MakeHuman (Y para cima, decímetros) -> Blender (Z para cima, metros)
    b = np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1) * 0.1
    corpo = indices_grupo("body")
    b[:, 2] -= b[corpo, 2].min()
    return b


# ------------------------------------------------------------------ rig

with open(os.path.join(DADOS, "rigs", "standard", f"rig.{RIG_NOME}.json")) as _f:
    RIG = json.load(_f)
with open(os.path.join(DADOS, "rigs", "standard", f"weights.{RIG_NOME}.json")) as _f:
    PESOS = json.load(_f)["weights"]


def posicao_junta(spec: dict, b: np.ndarray) -> Vector:
    if spec["strategy"] == "CUBE":
        return Vector(b[indices_grupo(spec["cube_name"])].mean(axis=0))
    if spec["strategy"] == "MEAN":
        return Vector(b[np.array(spec["vertex_indices"])].mean(axis=0))
    if spec["strategy"] == "VERTEX":
        return Vector(b[spec["vertex_index"]])
    raise ValueError(f"estratégia de junta desconhecida: {spec['strategy']}")


def criar_armature(b: np.ndarray) -> bpy.types.Object:
    arm = bpy.data.armatures.new("esqueleto")
    obj = bpy.data.objects.new("esqueleto", arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for nome, spec in RIG.items():
        eb = arm.edit_bones.new(nome)
        eb.head = posicao_junta(spec["head"], b)
        eb.tail = posicao_junta(spec["tail"], b)
        if (eb.tail - eb.head).length < 0.005:
            eb.tail = eb.head + Vector((0, 0, 0.1))
        eb.roll = spec.get("roll", 0.0)
    # O osso raiz do rig fica no chão, apontando para a frente.
    raiz = arm.edit_bones["Root"]
    raiz.head = Vector((0, 0, 0))
    raiz.tail = Vector((0, -0.25, 0))
    raiz.roll = 0
    for nome, spec in RIG.items():
        if spec.get("parent"):
            arm.edit_bones[nome].parent = arm.edit_bones[spec["parent"]]
            arm.edit_bones[nome].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


# ------------------------------------------------------------------ marcos do corpo

def marcos(b: np.ndarray) -> dict:
    m = {}
    for nome in ("joint-l-eye", "joint-r-eye", "joint-mouth", "joint-head", "joint-head-2", "joint-neck",
                 "joint-pelvis", "joint-l-ankle", "joint-l-knee", "joint-l-hand", "joint-l-elbow",
                 "joint-l-shoulder", "joint-spine-1", "joint-spine-3", "joint-l-upper-leg", "joint-jaw"):
        m[nome] = Vector(b[indices_grupo(nome)].mean(axis=0))
    cab = b[indices_grupo("body")]
    m["altura"] = float(cab[:, 2].max())
    m["olho_z"] = (m["joint-l-eye"].z + m["joint-r-eye"].z) / 2
    m["olho_x"] = abs(m["joint-l-eye"].x)
    return m


# ------------------------------------------------------------------ montagem da malha

def construir_corpo(b: np.ndarray, nome: str) -> bpy.types.Object:
    _, faces = carregar_base()
    corpo_idx = indices_grupo("body")
    mapa = -np.ones(len(b), dtype=np.int64)
    mapa[corpo_idx] = np.arange(len(corpo_idx))
    malha = bpy.data.meshes.new(nome)
    malha.from_pydata(b[corpo_idx].tolist(), [], [[int(mapa[i]) for i in f] for f in faces["body"]])
    malha.validate()
    obj = bpy.data.objects.new(nome, malha)
    bpy.context.scene.collection.objects.link(obj)
    # pesos do rig
    for osso, lista in PESOS.items():
        vg = obj.vertex_groups.new(name=osso)
        por_peso: dict = {}
        for vi, w in lista:
            if vi < len(mapa) and mapa[vi] >= 0:
                por_peso.setdefault(round(w, 4), []).append(int(mapa[vi]))
        for w, idxs in por_peso.items():
            vg.add(idxs, w, "REPLACE")
    for p in malha.polygons:
        p.use_smooth = True
    return obj


def osso_dominante(obj) -> list:
    nomes = [vg.name for vg in obj.vertex_groups]
    saida = []
    for v in obj.data.vertices:
        melhor, wmax = "", 0.0
        for g in v.groups:
            if g.weight > wmax:
                melhor, wmax = nomes[g.group], g.weight
        saida.append(melhor)
    return saida


# ------------------------------------------------------------------ peças de roupa

LADO = {"l", "r"}


def base_osso(nome: str) -> str:
    partes = nome.split("_")
    return "_".join(p for p in partes if p not in LADO)


def regioes(obj, m) -> dict:
    """Classifica cada vértice do corpo em uma região anatômica, usada pelas peças de roupa."""
    dom = osso_dominante(obj)
    reg = []
    eye_z = m["olho_z"]
    boca_z = m["joint-mouth"].z
    cabeca_y = m["joint-head"].y
    for v, d in zip(obj.data.vertices, dom):
        p, n = v.co, v.normal
        o = base_osso(d)
        if o in ("head",) or (o == "neck_01" and p.z > m["joint-neck"].z + 0.02):
            frente = n.y < -0.15 and p.y < cabeca_y - 0.01
            zc = (eye_z + m["joint-jaw"].z) / 2 + 0.005
            oval = (p.x / (m["olho_x"] + 0.05)) ** 2 + ((p.z - zc) / ((eye_z + 0.045 - zc))) ** 2
            rosto = frente and oval < 1.0
            orelha = abs(p.x) > m["olho_x"] + 0.035 and boca_z - 0.01 < p.z < eye_z + 0.03 and not frente
            if rosto:
                reg.append("rosto")
            elif orelha:
                reg.append("orelha")
            elif p.z > eye_z + 0.03 or (n.y > 0.1 and p.z > boca_z):
                reg.append("couro")
            else:
                reg.append("cabeca_baixo")
        elif o == "neck_01":
            reg.append("pescoco")
        elif o in ("spine_01", "spine_02", "spine_03", "clavicle"):
            reg.append("tronco")
        elif o == "pelvis":
            reg.append("quadril")
        elif o == "upperarm":
            reg.append("braco")
        elif o == "lowerarm":
            reg.append("antebraco")
        elif o in ("hand",) or o.split("_")[0] in ("thumb", "index", "middle", "ring", "pinky"):
            reg.append("mao")
        elif o == "thigh":
            reg.append("coxa")
        elif o == "calf":
            reg.append("canela" if p.z > m["joint-l-ankle"].z + 0.12 else "tornozelo")
        elif o in ("foot", "ball"):
            reg.append("pe")
        else:
            reg.append("tronco")
    return reg


def predicados(apar: dict, m: dict) -> list:
    """Lista de peças, da camada mais externa para a mais interna.

    Cada peça: (nome, conjunto de regiões, espessura, cor, cobre o corpo?, filtro extra opcional)
    """
    roupa = apar.get("roupa", {})
    cab = apar.get("cabeca", {}) or {}
    pecas = []
    joelho_z = m["joint-l-knee"].z
    quadril_z = m["joint-pelvis"].z
    tipo_cab = cab.get("tipo", "nenhum")
    if tipo_cab in ("capuz", "veu"):
        pecas.append(("capuz", {"couro", "orelha", "cabeca_baixo", "pescoco"}, 0.016, cab["cor"], True, None))
    elif tipo_cab == "lenco":
        pecas.append(("lenco", {"couro", "orelha", "cabeca_baixo", "pescoco"}, 0.011, cab["cor"], True, None))
    elif tipo_cab == "turbante":
        pecas.append(("turbante", {"couro"}, 0.03, cab["cor"], True,
                      lambda p, n: p.z > m["olho_z"] + 0.035 or n.y > 0.3))
    elif tipo_cab == "gorro":
        pecas.append(("gorro", {"couro"}, 0.012, cab["cor"], True, lambda p, n: p.z > m["olho_z"] + 0.05))
    elif tipo_cab == "lenco_pescoco":
        pecas.append(("lenco_pescoco", {"pescoco", "cabeca_baixo"}, 0.014, cab["cor"], True,
                      lambda p, n: p.z < m["joint-mouth"].z - 0.035))
    if roupa.get("avental"):
        pecas.append(("avental", {"tronco", "quadril", "coxa"}, 0.02, roupa["avental"], True,
                      lambda p, n: n.y < -0.35 and p.z > joelho_z + 0.05 and p.z < m["joint-spine-3"].z + 0.05))
    if roupa.get("casaco"):
        longo = roupa.get("casaco_longo", False)
        regs = {"tronco", "braco", "antebraco", "pescoco"} | ({"quadril", "coxa"} if longo else set())
        cintura = quadril_z + 0.04
        regs = regs | {"quadril"}
        pecas.append(("casaco", regs, 0.014, roupa["casaco"], True,
                      lambda p, n: (p.z > cintura or longo) and p.z > joelho_z + 0.08 and p.z < m["joint-neck"].z + 0.01))
    if roupa.get("luvas"):
        pecas.append(("luvas", {"mao"}, 0.004, roupa["luvas"], True, None))
    mangas = roupa.get("mangas", "longas")
    camisa_reg = {"tronco", "braco"} | ({"antebraco"} if mangas == "longas" else set())
    if roupa.get("camisa"):
        filtro = None
        if mangas == "curtas":
            filtro = lambda p, n: not (abs(p.x) > m["joint-l-shoulder"].x + 0.12)  # noqa: E731
        cint = quadril_z + 0.05
        f2 = (lambda p, n: p.z > cint and (filtro is None or filtro(p, n)))
        pecas.append(("camisa", camisa_reg | {"quadril"}, 0.004, roupa["camisa"], True, f2))
    if roupa.get("botas"):
        pecas.append(("botas", {"pe", "tornozelo"}, 0.009, roupa["botas"], True, None))
    if roupa.get("calca"):
        pecas.append(("calca", {"tronco", "quadril", "coxa", "canela", "tornozelo"}, 0.005, roupa["calca"], True,
                      lambda p, n: p.z < quadril_z + 0.13))
    cabelo = apar.get("cabelo", {}) or {}
    if cabelo.get("tipo") in ("curto", "preso", "raspado"):
        esp = {"curto": 0.007, "preso": 0.006, "raspado": 0.0015}[cabelo["tipo"]]
        pecas.append(("cabelo", {"couro"}, esp, cabelo["cor"], True, None))
    return pecas


def pecas_epi(apar: dict, m: dict) -> list:
    epi = apar.get("epi")
    if not epi:
        return []
    olho_z = m["olho_z"]
    return [
        ("epi_capacete", {"couro", "orelha"}, 0.034, epi["capacete"], False, lambda p, n: p.z > olho_z + 0.02 or n.y > 0.2),
        ("epi_visor", {"rosto"}, 0.026, (0.06, 0.08, 0.09), False, lambda p, n: olho_z - 0.022 < p.z < olho_z + 0.03),
        ("epi_mascara", {"rosto", "cabeca_baixo", "pescoco"}, 0.022, epi["mascara"], False, lambda p, n: p.z <= olho_z - 0.022),
        ("epi_macacao", {"tronco", "braco", "antebraco", "quadril", "coxa", "canela", "tornozelo", "pe", "mao"}, 0.016,
         epi["macacao"], False, None),
    ]


def ruido_dobras(p: Vector, escala: float = 18.0) -> float:
    return noise.noise(p * escala) * 0.5 + noise.noise(p * escala * 2.3) * 0.25


def gerar_pecas(obj, apar: dict, m: dict, nome: str) -> tuple:
    """Duplica faces do corpo por região e desloca pelas normais, criando roupas que já herdam os pesos."""
    reg = regioes(obj, m)
    pecas = predicados(apar, m)
    epi = pecas_epi(apar, m)
    malha = obj.data
    dono_face = {}
    cobre = set()
    # cada vértice: lista de peças que o cobrem
    cobertura = []
    for vi, v in enumerate(malha.vertices):
        lista = []
        for i, (pn, regs, esp, cor, cobre_corpo, filtro) in enumerate(pecas):
            if reg[vi] in regs and (filtro is None or filtro(v.co, v.normal)):
                lista.append(i)
        cobertura.append(lista)
    for poly in malha.polygons:
        vs = poly.vertices
        if not all(cobertura[v] for v in vs):
            continue  # alguma ponta fica à mostra: a face continua pele
        contagem = {}
        for v in vs:
            for i in cobertura[v]:
                contagem[i] = contagem.get(i, 0) + 1
        i = min(contagem, key=lambda k: (-contagem[k], k))
        dono_face[poly.index] = i
        if pecas[i][4]:
            cobre.add(poly.index)
    objetos = []
    for i, (pn, regs, esp, cor, cobre_corpo, filtro) in enumerate(pecas):
        faces = [f for f, d in dono_face.items() if d == i]
        if faces:
            objetos.append(duplicar_faces(obj, faces, f"{nome}_{pn}", esp, cor, pn))
    epi_objs = []
    for (pn, regs, esp, cor, _cobre, filtro) in epi:
        faces = [p.index for p in malha.polygons
                 if all(reg[v] in regs for v in p.vertices)
                 and (filtro is None or all(filtro(malha.vertices[v].co, malha.vertices[v].normal) for v in p.vertices))]
        if faces:
            epi_objs.append(duplicar_faces(obj, faces, pn, esp, cor, pn))
    # remove do corpo o que fica escondido sob roupas opacas
    bm = bmesh.new()
    bm.from_mesh(malha)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in cobre], context="FACES_ONLY")
    soltos = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=soltos, context="VERTS")
    bm.to_mesh(malha)
    bm.free()
    return objetos, epi_objs, reg


def duplicar_faces(obj, faces: list, nome: str, espessura: float, cor, tipo: str) -> bpy.types.Object:
    novo = obj.copy()
    novo.data = obj.data.copy()
    novo.name = nome
    novo.data.name = nome
    bpy.context.scene.collection.objects.link(novo)
    bm = bmesh.new()
    bm.from_mesh(novo.data)
    bm.faces.ensure_lookup_table()
    manter = set(faces)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in manter], context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()
    centro_cabeca = None
    for v in bm.verts:
        extra = espessura
        if tipo in ("calca", "camisa", "casaco", "epi_macacao", "capuz", "avental"):
            extra += ruido_dobras(v.co) * espessura * 0.6
        if tipo == "turbante":
            ang = math.atan2(v.co.y, v.co.x)
            extra += 0.006 * math.sin(v.co.z * 140 + ang * 3) + 0.02 * max(0.0, v.normal.z) + 0.01 * max(0.0, v.normal.y)
        if tipo == "lenco":
            extra += max(0.0, v.normal.y) * 0.012 + max(0.0, v.normal.z) * 0.006
        if tipo == "capuz":
            extra += max(0.0, v.normal.y) * 0.018 + max(0.0, v.normal.z) * 0.01
        if tipo == "botas" and v.co.z < 0.03:
            extra += 0.006
        if tipo == "epi_capacete":
            extra += 0.004 * max(0.0, v.normal.z)
        if tipo == "cabelo":
            extra *= 1.0 + 0.4 * max(0.0, v.normal.z)
        v.co += v.normal * extra
        if centro_cabeca is None:
            centro_cabeca = v.co.copy()
    # suaviza a casca para não carregar a microforma da pele
    if tipo not in ("botas", "luvas"):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(novo.data)
    bm.free()
    # borda com espessura (punhos, barras), sem duplicar a peça toda
    if tipo not in ("cabelo",):
        sol = novo.modifiers.new("borda", "SOLIDIFY")
        sol.thickness = min(0.006, espessura * 0.8)
        sol.offset = -1
        sol.use_rim_only = True
        sol.use_even_offset = True
        comum.aplicar_modificadores(novo)
    pintar_peca(novo, cor, tipo)
    mat = comum.material(f"{nome}_mat", (1, 1, 1), rugosidade=0.85 if not tipo.startswith("epi_visor") else 0.15,
                         metal=0.0)
    if tipo == "epi_visor":
        mat = comum.material(f"{nome}_mat", (1, 1, 1), rugosidade=0.12, metal=0.6)
    comum.atribuir(novo, mat)
    return novo


def pintar_peca(obj, cor, tipo: str) -> None:
    """Cor base + desgaste, remendos e sujeira de barra em COLOR_0."""
    malha = obj.data
    if "Col" not in malha.color_attributes:
        malha.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    attr = malha.color_attributes["Col"]
    rng = comum.semente(hash(obj.name) & 0xFFFF)
    fator = rng.choice((0.65, 0.75, 1.25, 1.35))
    desvio = rng.uniform(-0.04, 0.04)
    remendo_cor = [min(1, max(0, c * fator + desvio)) for c in cor[:3]]
    semente_r = rng.uniform(0, 100)
    for poly in malha.polygons:
        for li in poly.loop_indices:
            p = malha.vertices[malha.loops[li].vertex_index].co
            c = list(cor[:3])
            if tipo == "cabelo":
                t = 0.85 + 0.15 * noise.noise(p * 60)
                c = [x * t for x in c]
            elif tipo in ("epi_visor",):
                pass
            else:
                gasto = noise.fractal(p * 9 + Vector((semente_r, 0, 0)), 0.6, 2.0, 3)
                c = [x * (0.92 + 0.12 * gasto) for x in c]
                r = noise.noise(p * 6 + Vector((semente_r, 3, 1)))
                if tipo not in ("luvas", "cabelo", "botas") and r > 0.32:
                    c = remendo_cor[:]
                    if r < 0.35:  # costura do remendo
                        c = [x * 0.5 for x in c]
                barra = max(0.0, 1.0 - p.z / 0.3) * 0.3
                if tipo.startswith("epi_") or tipo in ("calca",):
                    sujeira = (0.42, 0.36, 0.28)
                    c = [x * (1 - barra) + s * barra for x, s in zip(c, sujeira)]
            attr.data[li].color = (*comum.lin(c), 1.0)


def pintar_pele(obj, apar: dict, m: dict) -> None:
    malha = obj.data
    if "Col" not in malha.color_attributes:
        malha.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    attr = malha.color_attributes["Col"]
    pele = apar.get("pele", (0.7, 0.5, 0.38))
    cab = (apar.get("cabelo") or {}).get("cor", (0.1, 0.08, 0.06))
    boca = m["joint-mouth"]
    labio = [pele[0] * 0.82, pele[1] * 0.55, pele[2] * 0.55]
    olho_z = m["olho_z"]
    for poly in malha.polygons:
        for li in poly.loop_indices:
            v = malha.vertices[malha.loops[li].vertex_index]
            p, n = v.co, v.normal
            c = list(pele[:3])
            frente = n.y < -0.2
            # lábios: elipse em volta da junta da boca
            dl = ((p.x - boca.x) / 0.023) ** 2 + ((p.z - boca.z) / 0.009) ** 2
            if frente and dl < 1.0 and p.y < boca.y + 0.005:
                t = min(1.0, (1.0 - dl) * 2.0) * 0.55
                c = [a * (1 - t) + b * t for a, b in zip(c, labio)]
            # sobrancelhas pintadas
            for lado in (1, -1):
                ex = m["olho_x"] * lado
                if frente and abs(p.x - ex) < 0.024 and olho_z + 0.019 < p.z < olho_z + 0.029 + 0.006 * (1 - abs(p.x - ex) / 0.024):
                    c = [x * 0.25 + y * 0.75 for x, y in zip(c, cab)]
            # bochechas levemente rosadas e olheiras
            for lado in (1, -1):
                d = ((p.x - lado * (m["olho_x"] + 0.01)) ** 2 + (p.z - (olho_z - 0.035)) ** 2) ** 0.5
                if frente and d < 0.025:
                    t = (1 - d / 0.025) * 0.18
                    c = [c[0] * (1 + t * 0.4), c[1] * (1 - t * 0.3), c[2] * (1 - t * 0.3)]
                d2 = ((p.x - lado * m["olho_x"]) ** 2 + (p.z - (olho_z - 0.012)) ** 2) ** 0.5
                if frente and d2 < 0.012:
                    c = [x * 0.9 for x in c]
            c = [x * (0.97 + 0.05 * noise.noise(p * 40)) for x in c]
            attr.data[li].color = (*comum.lin(c), 1.0)


def criar_olhos(b: np.ndarray, apar: dict, nome: str) -> bpy.types.Object:
    bm = bmesh.new()
    for g in ("helper-l-eye", "helper-r-eye"):
        pts = b[indices_grupo(g)]
        centro = pts.mean(axis=0)
        raio = float((pts[:, 0].max() - pts[:, 0].min()) / 2) * 0.98
        comum.esfera(bm, centro, raio, seg=20, aneis=12)
    obj = comum.objeto_de_bmesh(f"{nome}_olhos", bm)
    for p in obj.data.polygons:
        p.use_smooth = True
    malha = obj.data
    malha.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    attr = malha.color_attributes["Col"]
    iris = apar.get("olhos", (0.2, 0.13, 0.08))
    centros = [Vector(b[indices_grupo(g)].mean(axis=0)) for g in ("helper-l-eye", "helper-r-eye")]
    for poly in malha.polygons:
        for li in poly.loop_indices:
            p = malha.vertices[malha.loops[li].vertex_index].co
            c0 = min(centros, key=lambda c: (c - p).length)
            d = (p - c0).normalized()
            frente = -d.y
            if frente > 0.94:
                c = (0.02, 0.02, 0.02)
            elif frente > 0.80:
                c = tuple(iris)
            else:
                c = (0.86, 0.84, 0.8)
            attr.data[li].color = (*comum.lin(c), 1.0)
    vg = obj.vertex_groups.new(name="head")
    vg.add(list(range(len(malha.vertices))), 1.0, "REPLACE")
    comum.atribuir(obj, comum.material(f"{nome}_olhos_mat", (1, 1, 1), rugosidade=0.2))
    return obj


def criar_extras_rigidos(apar: dict, m: dict, nome: str, epi: bool) -> list:
    """Coque de cabelo, filtros da máscara e cilindro de ar: peças rígidas presas a um osso."""
    objs = []
    cab = apar.get("cabelo") or {}
    cabeca_topo = Vector((0, m["joint-head"].y, m["altura"]))
    if cab.get("tipo") == "preso" and (apar.get("cabeca") or {}).get("tipo") in (None, "nenhum", "lenco_pescoco", "gorro"):
        bm = bmesh.new()
        comum.esfera(bm, (0, m["joint-head"].y + 0.075, m["olho_z"] + 0.04), 0.038, 14, 10)
        o = comum.objeto_de_bmesh(f"{nome}_coque", bm)
        _rigido(o, "head", cab["cor"], f"{nome}_coque_mat")
        objs.append(o)
    if epi:
        e = apar["epi"]
        bm = bmesh.new()
        for lado in (1, -1):
            comum.cilindro(bm, (lado * 0.055, m["joint-mouth"].y - 0.055, m["joint-mouth"].z - 0.005), 0.026, 0.035, 14, eixo="Y")
        comum.cilindro(bm, (0, m["joint-mouth"].y - 0.07, m["joint-mouth"].z - 0.015), 0.018, 0.03, 10, eixo="Y")
        o = comum.objeto_de_bmesh("epi_filtros", bm)
        comum.biselar(o, 0.004)
        comum.aplicar_modificadores(o)
        _rigido(o, "head", (0.18, 0.18, 0.2), "epi_filtros_mat")
        objs.append(o)
        # cilindro de ar nas costas
        bm = bmesh.new()
        costas_y = m["joint-spine-3"].y + 0.15
        comum.cilindro(bm, (0, costas_y, m["joint-spine-3"].z - 0.05), 0.075, 0.42, 16)
        comum.cilindro(bm, (0, costas_y, m["joint-spine-3"].z + 0.18), 0.03, 0.06, 10)
        comum.caixa(bm, (0, costas_y - 0.06, m["joint-spine-3"].z - 0.05), (0.2, 0.03, 0.34))
        o = comum.objeto_de_bmesh("epi_cilindro", bm)
        comum.biselar(o, 0.006)
        comum.aplicar_modificadores(o)
        _rigido(o, "spine_03", e["capacete"], "epi_cilindro_mat")
        objs.append(o)
        # lanterna do capacete
        bm = bmesh.new()
        comum.cilindro(bm, (0, m["joint-head"].y - 0.11, m["olho_z"] + 0.085), 0.018, 0.04, 12, eixo="Y")
        o = comum.objeto_de_bmesh("epi_lanterna", bm)
        _rigido(o, "head", (0.9, 0.85, 0.6), "epi_lanterna_mat", emissao=True)
        objs.append(o)
    _ = cabeca_topo
    return objs


def _rigido(obj, osso: str, cor, nome_mat: str, emissao: bool = False) -> None:
    vg = obj.vertex_groups.new(name=osso)
    vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    for p in obj.data.polygons:
        p.use_smooth = True
    if emissao:
        comum.atribuir(obj, comum.material(nome_mat, cor, 0.3, emissao=cor, forca_emissao=3.0))
    else:
        comum.atribuir(obj, comum.material(nome_mat, cor, 0.6, metal=0.3))


# ------------------------------------------------------------------ finalização

def decimar(obj, razao: float) -> None:
    if razao >= 0.999 or len(obj.data.polygons) < 200:
        return
    mod = obj.modifiers.new("decimar", "DECIMATE")
    mod.ratio = razao
    mod.use_collapse_triangulate = True
    comum.aplicar_modificadores(obj)


def vincular(objs: list, arm) -> None:
    for o in objs:
        o.parent = arm
        mod = o.modifiers.new("esqueleto", "ARMATURE")
        mod.object = arm
        # normaliza pesos (glTF exige soma 1 e no máximo 4 influências; o exportador limita)
        bpy.context.view_layer.objects.active = o


def juntar(objs: list, nome: str):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    objs[0].name = nome
    objs[0].data.name = nome
    return objs[0]


def gerar(id_: str) -> str:
    with open(os.path.join(NPCS, f"{id_}.json"), encoding="utf-8") as f:
        dados = json.load(f)
    apar = dados["aparencia"]
    comum.limpar_cena()
    b = vertices_personagem(apar)
    m = marcos(b)
    altura = m["altura"]
    cabeca = altura - (m["joint-jaw"].z - 0.012)
    print(f"[{id_}] altura {altura:.2f} m, cabeças de altura: {altura / cabeca:.2f}")
    arm = criar_armature(b)
    corpo = construir_corpo(b, f"{id_}_corpo")
    roupas, epi, _ = gerar_pecas(corpo, apar, m, id_)
    pintar_pele(corpo, apar, m)
    comum.atribuir(corpo, comum.material(f"{id_}_pele_mat", (1, 1, 1), rugosidade=0.55))
    olhos = criar_olhos(b, apar, id_)
    extras = criar_extras_rigidos(apar, m, id_, bool(epi))
    decimar(corpo, 0.42)
    cabeca_pecas = ("_cabelo", "_lenco", "_capuz", "_turbante", "_gorro", "epi_mascara", "epi_visor", "epi_capacete")
    for o in roupas + epi:
        decimar(o, 0.6 if o.name.endswith(cabeca_pecas) else 0.35)
    todos = [corpo, olhos] + roupas + epi + extras
    vincular(todos, arm)
    epi_extras = [o for o in extras if o.name.startswith("epi_")]
    outros_extras = [o for o in extras if not o.name.startswith("epi_")]
    if epi:
        # jogador: corpo, roupa da vila e EPI ficam separados para alternar na eclusa
        corpo_final = juntar([corpo, olhos], f"{id_}_corpo")
        roupa_final = juntar(roupas + outros_extras, f"{id_}_roupa")
        epi_final = juntar(epi + epi_extras, f"{id_}_epi")
        exportar = [arm, corpo_final, roupa_final, epi_final]
    else:
        malha = juntar([corpo, olhos] + roupas + outros_extras, f"{id_}_malha")
        lod = malha.copy()
        lod.data = malha.data.copy()
        lod.name = f"{id_}_malha_lod1"
        bpy.context.scene.collection.objects.link(lod)
        lod.modifiers.clear()
        decimar(lod, 0.3)
        lod.modifiers.new("esqueleto", "ARMATURE").object = arm
        lod.parent = arm
        exportar = [arm, malha, lod]
    tris = sum(len(p.vertices) - 2 for o in exportar[1:] if not o.name.endswith("_lod1") for p in o.data.polygons)
    print(f"[{id_}] triângulos (sem LOD): {tris}")
    caminho = os.path.join(SAIDA, f"{id_}.glb")
    comum.exportar_glb(caminho, selecionados=exportar)
    return caminho


if __name__ == "__main__":
    args = comum.argumentos()
    if not args or args == ["--todos"]:
        args = sorted(a[:-5] for a in os.listdir(NPCS) if a.endswith(".json"))
    for i in args:
        gerar(i)
