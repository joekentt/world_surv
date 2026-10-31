"""Gera a biblioteca de animações no rig game_engine e exporta em public/assets/personagens/animacoes.glb.

Todas as ações são criadas por código: cada osso recebe rotações descritas nos eixos do
personagem (X = lateral, Y = frente/trás, Z = vertical), convertidas para o espaço local
do osso. Os ciclos são em loop, a 30 quadros por segundo, sem deslocamento da raiz
(o jogo move o personagem).

Convenções (personagem olhando para -Y, esquerda em +X):
    frente(o, g): balança um membro que aponta para baixo para a frente (g > 0)
    inclina(o, g): inclina para a frente um osso que aponta para cima (g > 0)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "personagens"))
import bpy  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

import comum  # noqa: E402
import gerar_personagem as gp  # noqa: E402

FPS = 30
SAIDA = os.path.join(comum.ASSETS, "personagens", "animacoes.glb")
DEDOS = [f"{d}_{i:02d}" for d in ("index", "middle", "ring", "pinky") for i in (1, 2, 3)]

X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))


class Pose:
    """Acumula rotações por osso (em eixos do personagem) e o deslocamento da pélvis."""

    def __init__(self):
        self.rot: dict[str, Quaternion] = {}
        self.desloc = Vector((0, 0, 0))

    def girar(self, osso: str, eixo: Vector, graus: float) -> "Pose":
        q = Quaternion(eixo, math.radians(graus))
        self.rot[osso] = q @ self.rot.get(osso, Quaternion())
        return self

    # atalhos legíveis
    def frente(self, osso, g):  # membro para baixo: positivo vai para a frente (-Y)
        return self.girar(osso, X, -g)

    def inclina(self, osso, g):  # osso para cima: positivo inclina para a frente
        return self.girar(osso, X, g)

    def lado(self, osso, g):  # positivo abre para fora do corpo
        lado = 1 if osso.endswith("_l") else -1
        return self.girar(osso, Y, -g * lado)

    def torce(self, osso, g):
        return self.girar(osso, Z, g)


def base_parado(p: Pose, abertura: float = 0.0) -> Pose:
    """Braços junto ao corpo (o rig vem em pose A) e dedos relaxados."""
    for s in ("l", "r"):
        sinal = 1 if s == "l" else -1
        p.girar(f"upperarm_{s}", Y, sinal * (40 - abertura))
        p.frente(f"upperarm_{s}", 4)
        p.frente(f"lowerarm_{s}", 12)
        for d in DEDOS:
            p.girar(f"{d}_{s}", X, 0)  # marcador: dedos tratados em local
    return p


def dedos_curvos(p: Pose, graus: float, s: str):
    p.rot.setdefault("__dedos__", Quaternion())
    p.__dict__.setdefault("curvas", {})[s] = graus
    return p


def ordem_hierarquica(arm) -> list:
    saida = []

    def visitar(osso):
        saida.append(osso.name)
        for f in osso.children:
            visitar(f)
    for o in arm.data.bones:
        if o.parent is None:
            visitar(o)
    return saida


def aplicar(arm, pose: Pose, quadro: int) -> None:
    """Rotações do usuário são em eixos fixos do personagem, aplicadas depois das do pai.

    Delta global do osso: W = Q · W_pai. Rotação local no Blender: L = R⁻¹ · W_pai⁻¹ · W · R,
    em que R é a orientação de repouso do osso no espaço da armature.
    """
    globais: dict[str, Quaternion] = {}
    for nome in ordem_hierarquica(arm):
        pb = arm.pose.bones[nome]
        pb.rotation_mode = "QUATERNION"
        rest = pb.bone.matrix_local.to_3x3().to_quaternion()
        q = pose.rot.get(pb.name, Quaternion())
        w_pai = globais.get(pb.parent.name, Quaternion()) if pb.parent else Quaternion()
        w = q @ w_pai
        globais[nome] = w
        local = rest.inverted() @ w_pai.inverted() @ w @ rest
        # dedos: curva no eixo X local do osso
        curvas = getattr(pose, "curvas", {})
        lado = pb.name[-1:]
        if pb.name[:-2] in DEDOS and lado in curvas:
            local = local @ Quaternion(Vector((1, 0, 0)), math.radians(curvas[lado]))
        pb.rotation_quaternion = local
        pb.keyframe_insert("rotation_quaternion", frame=quadro)
        if pb.name == "pelvis":
            pb.location = rest.inverted() @ pose.desloc
            pb.keyframe_insert("location", frame=quadro)


def nova_acao(arm, nome: str):
    acao = bpy.data.actions.new(nome)
    acao.use_fake_user = True
    if not arm.animation_data:
        arm.animation_data_create()
    arm.animation_data.action = acao
    return acao


def ciclo(arm, nome: str, quadros: int, gerar_pose, passos: int | None = None) -> None:
    """Gera uma ação em loop amostrando gerar_pose(t), t em [0, 1)."""
    nova_acao(arm, nome)
    passos = passos or quadros
    for i in range(passos + 1):
        t = (i % passos) / passos
        aplicar(arm, gerar_pose(t), round(i * quadros / passos) + 1)
    # empilha no NLA para que o exportador encontre a ação mesmo sem estar ativa
    trilha = arm.animation_data.nla_tracks.new()
    trilha.name = nome
    trilha.strips.new(nome, 1, arm.animation_data.action)
    trilha.mute = True
    arm.animation_data.action = None


def s(t, fase=0.0):
    return math.sin(2 * math.pi * (t + fase))


def c(t, fase=0.0):
    return math.cos(2 * math.pi * (t + fase))


# ------------------------------------------------------------------ ciclos

def parado(t):
    p = base_parado(Pose())
    resp = s(t)
    p.inclina("spine_02", 1.0 + resp * 0.8)
    p.inclina("spine_03", resp * 0.8)
    p.inclina("head", -1.5 - resp * 0.6)
    p.torce("head", s(t, 0.25) * 2)
    for lado in ("l", "r"):
        p.girar(f"clavicle_{lado}", Z, resp * 0.8 * (1 if lado == "l" else -1))
        dedos_curvos(p, 22, lado)
    p.desloc = Vector((0, 0, resp * 0.004))
    return p


def andar(t, intensidade=1.0):
    p = base_parado(Pose())
    passo = s(t)
    joelho_e = max(0.0, s(t, 0.18)) * 50 + 6
    joelho_d = max(0.0, s(t, 0.68)) * 50 + 6
    p.frente("thigh_l", 24 * passo * intensidade)
    p.frente("thigh_r", -24 * passo * intensidade)
    p.frente("calf_l", -joelho_e * intensidade)
    p.frente("calf_r", -joelho_d * intensidade)
    p.frente("foot_l", (max(0.0, -s(t, 0.1)) * 18 - 4) * intensidade)
    p.frente("foot_r", (max(0.0, -s(t, 0.6)) * 18 - 4) * intensidade)
    p.frente("upperarm_l", -18 * passo * intensidade)
    p.frente("upperarm_r", 18 * passo * intensidade)
    p.frente("lowerarm_l", 8 + max(0.0, -passo) * 14)
    p.frente("lowerarm_r", 8 + max(0.0, passo) * 14)
    p.torce("spine_01", 4 * passo * intensidade)
    p.torce("spine_03", -6 * passo * intensidade)
    p.inclina("spine_02", 3)
    p.inclina("head", -2)
    p.girar("pelvis", Y, 3 * passo)
    for lado in ("l", "r"):
        dedos_curvos(p, 25, lado)
    p.desloc = Vector((0, 0, -0.012 + 0.012 * abs(c(t)) ))
    return p


def correr(t):
    p = base_parado(Pose())
    passo = s(t)
    p.frente("thigh_l", 42 * passo + 8)
    p.frente("thigh_r", -42 * passo + 8)
    p.frente("calf_l", -(max(0.0, s(t, 0.12)) * 85 + 18))
    p.frente("calf_r", -(max(0.0, s(t, 0.62)) * 85 + 18))
    p.frente("foot_l", max(0.0, -s(t, 0.05)) * 25 - 8)
    p.frente("foot_r", max(0.0, -s(t, 0.55)) * 25 - 8)
    p.frente("upperarm_l", -40 * passo)
    p.frente("upperarm_r", 40 * passo)
    p.lado("upperarm_l", -8)
    p.lado("upperarm_r", -8)
    p.frente("lowerarm_l", 75)
    p.frente("lowerarm_r", 75)
    p.inclina("spine_01", 8)
    p.inclina("spine_02", 6)
    p.torce("spine_03", -10 * passo)
    p.inclina("head", -8)
    for lado in ("l", "r"):
        dedos_curvos(p, 60, lado)
    p.desloc = Vector((0, 0, -0.03 + 0.035 * abs(c(t))))
    return p


def pular(t):
    p = base_parado(Pose(), abertura=10)
    p.frente("thigh_l", 50)
    p.frente("calf_l", -80)
    p.frente("thigh_r", 15)
    p.frente("calf_r", -45)
    p.frente("foot_l", 15)
    p.frente("upperarm_l", 40 + s(t) * 4)
    p.frente("upperarm_r", -25 + s(t) * 4)
    p.lado("upperarm_l", 25)
    p.lado("upperarm_r", 30)
    p.frente("lowerarm_l", 40)
    p.frente("lowerarm_r", 30)
    p.inclina("spine_02", 6)
    p.inclina("head", -6)
    for lado in ("l", "r"):
        dedos_curvos(p, 30, lado)
    return p


def agachar(t, andando=False):
    p = base_parado(Pose())
    passo = s(t) if andando else 0.0
    for lado, sinal in (("l", 1), ("r", -1)):
        p.frente(f"thigh_{lado}", 75 + 18 * passo * sinal)
        p.frente(f"calf_{lado}", -110 + 10 * passo * sinal)
        p.frente(f"foot_{lado}", 30)
        p.frente(f"upperarm_{lado}", 30 - 10 * passo * sinal)
        p.frente(f"lowerarm_{lado}", 50)
        dedos_curvos(p, 40, lado)
    p.inclina("spine_01", 22)
    p.inclina("spine_02", 10)
    p.inclina("head", -25)
    p.desloc = Vector((0, 0.06, -0.38 + 0.008 * s(t * (2 if andando else 1))))
    return p


def escada(t):
    """Subindo escada de costas para a câmera: mãos e pés alternados."""
    p = base_parado(Pose())
    a = s(t)
    for lado, sinal in (("l", 1), ("r", -1)):
        sobe = a * sinal
        p.frente(f"upperarm_{lado}", 140 + 25 * sobe)
        p.lado(f"upperarm_{lado}", -18)
        p.frente(f"lowerarm_{lado}", 30 - 25 * sobe)
        p.frente(f"thigh_{lado}", 45 - 35 * sobe)
        p.frente(f"calf_{lado}", -(70 - 50 * sobe))
        p.frente(f"foot_{lado}", 10)
        dedos_curvos(p, 70, lado)
    p.inclina("spine_02", 4)
    p.inclina("head", -12)
    p.desloc = Vector((0, 0, 0.02 * a))
    return p


def interagir(t):
    p = parado(0.0)
    alcance = math.sin(math.pi * min(1.0, t * 1.6))
    p.frente("upperarm_r", 60 * alcance)
    p.lado("upperarm_r", -10 * alcance)
    p.frente("lowerarm_r", -10 * alcance)
    p.inclina("spine_02", 8 * alcance)
    p.inclina("head", 6 * alcance)
    dedos_curvos(p, 22 + 40 * max(0.0, alcance - 0.7) / 0.3, "r")
    return p


def varrer(t):
    p = base_parado(Pose())
    a = s(t)
    p.inclina("spine_01", 14)
    p.inclina("spine_02", 6)
    p.torce("spine_02", 18 * a)
    p.frente("upperarm_r", 35 + 15 * a)
    p.lado("upperarm_r", -18)
    p.frente("lowerarm_r", 45)
    p.frente("upperarm_l", 55 + 15 * a)
    p.lado("upperarm_l", -25)
    p.frente("lowerarm_l", 60)
    p.frente("thigh_l", 10)
    p.frente("thigh_r", -6)
    p.frente("calf_l", -12)
    for lado in ("l", "r"):
        dedos_curvos(p, 80, lado)
    p.desloc = Vector((0, 0, -0.03))
    return p


def consertar(t):
    p = base_parado(Pose())
    golpe = max(0.0, s(t)) ** 0.6
    p.inclina("spine_01", 25)
    p.inclina("spine_02", 12)
    p.inclina("head", 12)
    p.frente("thigh_l", 20)
    p.frente("thigh_r", 5)
    p.frente("calf_l", -25)
    p.frente("calf_r", -10)
    p.frente("upperarm_r", 40 + 55 * golpe)
    p.frente("lowerarm_r", 80 - 50 * golpe)
    p.frente("upperarm_l", 55)
    p.lado("upperarm_l", -15)
    p.frente("lowerarm_l", 55)
    dedos_curvos(p, 80, "r")
    dedos_curvos(p, 40, "l")
    p.desloc = Vector((0, 0.02, -0.05))
    return p


def cozinhar(t):
    p = base_parado(Pose())
    p.inclina("spine_01", 12)
    p.inclina("spine_02", 6)
    p.inclina("head", 15)
    p.frente("upperarm_r", 45 + 8 * s(t))
    p.lado("upperarm_r", 8 * c(t))
    p.frente("lowerarm_r", 60 + 8 * c(t))
    p.frente("upperarm_l", 30)
    p.frente("lowerarm_l", 75)
    p.lado("upperarm_l", 8)
    dedos_curvos(p, 75, "r")
    dedos_curvos(p, 30, "l")
    p.desloc = Vector((0, 0, -0.01))
    return p


def rezar(t):
    p = base_parado(Pose())
    resp = s(t)
    for lado in ("l", "r"):
        p.frente(f"upperarm_{lado}", 12)
        p.lado(f"upperarm_{lado}", -10)
        p.frente(f"lowerarm_{lado}", 78)
        p.girar(f"lowerarm_{lado}", Z, -30 if lado == "l" else 30)
        dedos_curvos(p, 5, lado)
    p.inclina("spine_02", 5 + resp)
    p.inclina("neck_01", 12)
    p.inclina("head", 18 + resp * 2)
    return p


def conversar(t):
    p = parado(t)
    g1 = s(t * 2)
    g2 = s(t * 3, 0.3)
    p.frente("upperarm_r", 25 + 14 * max(0.0, g1))
    p.lado("upperarm_r", 6 + 6 * g2)
    p.frente("lowerarm_r", 55 + 20 * g1)
    p.frente("upperarm_l", 10 + 10 * max(0.0, g2))
    p.frente("lowerarm_l", 25 + 30 * max(0.0, g2))
    p.torce("head", 8 * s(t, 0.1))
    p.inclina("head", 3 * g1)
    p.torce("spine_03", 5 * g2)
    return p


def sentar(t):
    p = base_parado(Pose())
    resp = s(t)
    for lado in ("l", "r"):
        p.frente(f"thigh_{lado}", 88)
        p.lado(f"thigh_{lado}", 6)
        p.frente(f"calf_{lado}", -88)
        p.frente(f"upperarm_{lado}", 22)
        p.frente(f"lowerarm_{lado}", 45)
        dedos_curvos(p, 30, lado)
    p.inclina("spine_01", -4)
    p.inclina("spine_02", 8 + resp * 0.8)
    p.inclina("head", 6)
    p.desloc = Vector((0, 0.05, -0.43))
    return p


def acenar(t):
    p = parado(t)
    p.frente("upperarm_r", 35)
    p.lado("upperarm_r", 75)
    p.frente("lowerarm_r", 15)
    p.girar("lowerarm_r", Y, -25 * s(t * 2))
    p.girar("lowerarm_r", X, -70)
    dedos_curvos(p, 2, "r")
    return p


def brincar(t):
    p = base_parado(Pose(), abertura=20)
    pulo = abs(s(t))
    for lado, sinal in (("l", 1), ("r", -1)):
        p.frente(f"thigh_{lado}", 20 * pulo + 10 * sinal * s(t * 2))
        p.frente(f"calf_{lado}", -40 * pulo)
        p.frente(f"upperarm_{lado}", 60 + 60 * pulo)
        p.lado(f"upperarm_{lado}", 20)
        p.frente(f"lowerarm_{lado}", 20)
        dedos_curvos(p, 40, lado)
    p.inclina("head", -10 * pulo)
    p.desloc = Vector((0, 0, 0.12 * (1 - abs(c(t))) - 0.03 * pulo))
    return p


def morrer(t):
    """Cai de joelhos e tomba de lado (não é loop: o último quadro fica)."""
    k = min(1.0, t * 1.4)
    p = base_parado(Pose())
    for lado in ("l", "r"):
        p.frente(f"thigh_{lado}", 85 * k)
        p.frente(f"calf_{lado}", -120 * k)
        p.frente(f"upperarm_{lado}", 30 * k)
        p.frente(f"lowerarm_{lado}", 40 * k)
        dedos_curvos(p, 30, lado)
    p.inclina("spine_01", 35 * k)
    p.inclina("spine_02", 15 * k)
    p.inclina("head", 25 * k)
    p.girar("pelvis", Y, -25 * max(0.0, k - 0.6) / 0.4)
    p.desloc = Vector((0, 0.1 * k, -0.5 * k))
    return p


def tossir(t):
    p = parado(t)
    k = max(0.0, s(t * 3)) * (1 if t < 0.66 else 0)
    p.inclina("spine_02", 14 * k)
    p.inclina("head", 12 * k)
    p.frente("upperarm_r", 40 * k)
    p.frente("lowerarm_r", 100 * k)
    return p


ACOES = [
    ("parado", 60, parado), ("andar", 32, andar), ("correr", 20, correr), ("pular", 20, pular),
    ("agachar", 40, agachar), ("agachar_andar", 36, lambda t: agachar(t, True)), ("escada", 30, escada),
    ("interagir", 24, interagir), ("varrer", 40, varrer), ("consertar", 30, consertar),
    ("cozinhar", 40, cozinhar), ("rezar", 80, rezar), ("conversar", 90, conversar), ("sentar", 80, sentar),
    ("acenar", 30, acenar), ("brincar", 26, brincar), ("morrer", 40, morrer), ("tossir", 45, tossir),
]


def principal():
    comum.limpar_cena()
    bpy.context.scene.render.fps = FPS
    apar = {"genero": 0.5, "idade_anos": 25, "peso": 0.5, "musculo": 0.5, "altura": 0.5, "proporcoes": 0.5,
            "semente": 1, "rosto": {}}
    b = gp.vertices_personagem(apar)
    arm = gp.criar_armature(b)
    corpo = gp.construir_corpo(b, "previa_animacao")
    gp.decimar(corpo, 0.08)
    gp.vincular([corpo], arm)
    comum.atribuir(corpo, comum.material("previa_mat", (0.6, 0.6, 0.6)))
    for nome, quadros, funcao in ACOES:
        ciclo(arm, nome, quadros, funcao, passos=quadros if quadros <= 40 else quadros // 2)
    print(f"ações: {[a.name for a in bpy.data.actions]}")
    comum.exportar_glb(SAIDA, selecionados=[arm, corpo], animacoes=True)


if __name__ == "__main__":
    principal()
