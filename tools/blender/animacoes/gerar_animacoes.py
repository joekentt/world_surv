"""Gera a biblioteca de animações no rig game_engine e exporta em public/assets/personagens/animacoes.glb.

Todas as ações são criadas por código: cada osso recebe rotações descritas nos eixos do
personagem (X = lateral, Y = frente/trás, Z = vertical), convertidas para o espaço local
do osso. Os ciclos são em loop, a 30 quadros por segundo, sem deslocamento da raiz
(o jogo move o personagem).

Convenções (personagem olhando para -Y, esquerda em +X):
    frente(o, g): balança um membro que aponta para baixo para a frente (g > 0)
    inclina(o, g): inclina para a frente um osso que aponta para cima (g > 0)

Locomoção (parado, andar, correr, agachar, aterrissar): as pernas saem de IK. Cada pose diz
onde fica o tornozelo e a inclinação do pé; o pé rola do calcanhar para a bola e para a ponta,
e o pé de apoio recua exatamente à velocidade de referência do ciclo, então não desliza.
As curvas usam chaves com tempos assimétricos (spline de Hermite), não seno puro.
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
# mão semiaberta: o indicador curva menos que o mínimo, e a falange do meio mais que as outras
FATOR_DEDO = {"index": 0.7, "middle": 0.9, "ring": 1.05, "pinky": 1.2}
FATOR_FALANGE = {"01": 0.75, "02": 1.15, "03": 0.85}

X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))

APAR_NEUTRA = {"genero": 0.5, "idade_anos": 25, "peso": 0.5, "musculo": 0.5, "altura": 0.5, "proporcoes": 0.5,
               "semente": 1, "rosto": {}}


class Pose:
    """Acumula rotações por osso (em eixos do personagem), o deslocamento da pélvis e os alvos dos pés."""

    def __init__(self):
        self.rot: dict[str, Quaternion] = {}
        self.desloc = Vector((0, 0, 0))
        # lado -> (tornozelo alvo, inclinação do pé, inclinação dos dedos), resolvido por IK
        self.pes: dict[str, tuple] = {}

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

    def rola(self, osso, g):  # positivo abaixa o lado esquerdo (+X)
        return self.girar(osso, Y, g)


# ------------------------------------------------------------------ curvas

def spline(x: float, pts: list):
    """Hermite cúbica por pontos (x, y) ordenados; y pode ser número ou Vector. As tangentes são as da
    parábola pelos três pontos vizinhos, o que respeita espaçamentos desiguais entre as chaves."""
    n = len(pts)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    i = 0
    while pts[i + 1][0] < x:
        i += 1

    def tangente(k):
        if k == 0:
            return (pts[1][1] - pts[0][1]) / (pts[1][0] - pts[0][0])
        if k == n - 1:
            return (pts[k][1] - pts[k - 1][1]) / (pts[k][0] - pts[k - 1][0])
        h0, h1 = pts[k][0] - pts[k - 1][0], pts[k + 1][0] - pts[k][0]
        s0 = (pts[k][1] - pts[k - 1][1]) / h0
        s1 = (pts[k + 1][1] - pts[k][1]) / h1
        return (s0 * h1 + s1 * h0) / (h0 + h1)

    (x0, y0), (x1, y1) = pts[i], pts[i + 1]
    h = x1 - x0
    u = (x - x0) / h
    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    return y0 * h00 + tangente(i) * (h10 * h) + y1 * h01 + tangente(i + 1) * (h11 * h)


def curva(t: float, chaves: list, periodo: float = 1.0):
    """Curva periódica por chaves (t, valor), t em [0, periodo): o laço não tem emenda."""
    t = t % periodo
    ext = [(k - periodo, v) for k, v in chaves[-2:]] + list(chaves) + [(k + periodo, v) for k, v in chaves[:2]]
    return spline(t, ext)


def suave(a: float, b: float, x: float) -> float:
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def s(t, fase=0.0):
    return math.sin(2 * math.pi * (t + fase))


def c(t, fase=0.0):
    return math.cos(2 * math.pi * (t + fase))


# ------------------------------------------------------------------ geometria do pé e IK das pernas

G: dict = {}  # geometria do esqueleto neutro (preparar_geometria)
INC_BOLA = -32.0  # até esta inclinação o pé gira na bola; além dela, na ponta dos dedos


def preparar_geometria(arm) -> None:
    ossos = arm.data.bones
    for lado in ("l", "r"):
        a = ossos[f"foot_{lado}"].head_local.copy()
        b = ossos[f"ball_{lado}"].head_local.copy()
        p = ossos[f"ball_{lado}"].tail_local.copy()
        G[f"tornozelo_{lado}"] = a
        G[f"bola_{lado}"] = b
        G[f"ponta_{lado}"] = p
        G[f"calcanhar_{lado}"] = Vector((a.x, a.y + 0.45 * abs(b.y - a.y), 0.0))
        v = b - a
        G[f"inc_repouso_{lado}"] = math.degrees(math.atan2(v.z, -v.y))


def girar_x(v: Vector, inc: float) -> Vector:
    """Gira no plano sagital; inclinação positiva levanta a ponta do pé."""
    return Quaternion(X, math.radians(-inc)) @ v


def pe_no_chao(lado: str, x: float, ya: float, inc: float) -> tuple:
    """Tornozelo de um pé apoiado. ya é a posição em Y do calcanhar com o pé plano (âncora no chão);
    inc > 0 apoia no calcanhar, entre 0 e INC_BOLA na bola, abaixo disso na ponta dos dedos.
    Devolve (tornozelo, inclinação dos dedos)."""
    a0, b0, t0, h0 = (G[f"{n}_{lado}"] for n in ("tornozelo", "bola", "ponta", "calcanhar"))
    if inc >= 0:
        piv = Vector((a0.x, ya, h0.z))
        tz = piv + girar_x(a0 - h0, inc)
        dedo = inc
    elif inc >= INC_BOLA:
        piv = Vector((a0.x, ya + b0.y - h0.y, b0.z))
        tz = piv + girar_x(a0 - b0, inc)
        dedo = 0.0
    else:
        g = inc - INC_BOLA
        ponta = Vector((a0.x, ya + t0.y - h0.y, t0.z))
        bola = ponta - girar_x(t0 - b0, g)
        tz = bola + girar_x(a0 - b0, inc)
        dedo = g
    tz.x = x
    return tz, dedo


ALCANCE: list = []  # maior fração do comprimento da perna pedida em cada amostra (diagnóstico)


def _ang(v: Vector) -> float:
    """Ângulo sagital de um vetor que aponta para baixo: 0 = vertical, positivo = para a frente."""
    return math.atan2(-v.y, -v.z)


def resolver_pernas(arm, pose: Pose) -> None:
    """Converte os alvos dos pés em rotações de coxa, canela, pé e dedos (IK de dois ossos no plano
    sagital, com correção lateral na coxa), acrescentadas por fora das rotações já pedidas."""
    def ler():
        aplicar(arm, pose, None)
        bpy.context.view_layer.update()
        return {n: arm.pose.bones[n].head.copy() for lado in pose.pes
                for n in (f"thigh_{lado}", f"calf_{lado}", f"foot_{lado}", f"ball_{lado}")}

    pior = 0.0
    for _ in range(2):
        pos = ler()
        for lado, (alvo, _inc, _dedo) in pose.pes.items():
            q, a = pos[f"thigh_{lado}"], pos[f"foot_{lado}"]
            gama = math.atan2(alvo.x - q.x, max(0.05, q.z - alvo.z)) - math.atan2(a.x - q.x, max(0.05, q.z - a.z))
            pose.girar(f"thigh_{lado}", Y, -math.degrees(gama))
            pose.girar(f"foot_{lado}", Y, math.degrees(gama))
        pos = ler()
        for lado, (alvo, _inc, _dedo) in pose.pes.items():
            q, k, a = pos[f"thigh_{lado}"], pos[f"calf_{lado}"], pos[f"foot_{lado}"]
            l1 = math.hypot((k - q).y, (k - q).z)
            l2 = math.hypot((a - k).y, (a - k).z)
            dv = alvo - q
            bruto = math.hypot(dv.y, dv.z)
            pior = max(pior, bruto / (l1 + l2))
            d = min(max(bruto, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9995)
            alfa = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
            beta = math.acos(max(-1.0, min(1.0, (l2 * l2 + d * d - l1 * l1) / (2 * l2 * d))))
            fi = _ang(dv)
            d1 = fi + alfa - _ang(k - q)
            d2 = fi - beta - _ang(a - k)
            pose.frente(f"thigh_{lado}", math.degrees(d1))
            pose.frente(f"calf_{lado}", math.degrees(d2 - d1))
    pos = ler()
    for lado, (_alvo, inc, dedo) in pose.pes.items():
        v = pos[f"ball_{lado}"] - pos[f"foot_{lado}"]
        atual = math.degrees(math.atan2(v.z, -v.y)) - G[f"inc_repouso_{lado}"]
        pose.frente(f"foot_{lado}", inc - atual)
        pose.frente(f"ball_{lado}", dedo - inc)
    ALCANCE.append(pior)


def apoiar(p: Pose, lado: str, x: float, ya: float, inc: float) -> None:
    """Pé parado no chão (âncora ya, ver pe_no_chao)."""
    tz, dedo = pe_no_chao(lado, x, ya, inc)
    p.pes[lado] = (tz, inc, dedo)


def posar(arm, pose: Pose, quadro: int | None = None) -> None:
    if pose.pes:
        resolver_pernas(arm, pose)
    aplicar(arm, pose, quadro)


# ------------------------------------------------------------------ marcha (andar, correr, agachado)

class Marcha:
    """Trajetória de um pé ao longo do ciclo (u = 0 no toque do calcanhar).

    Apoio (u < apoio): a âncora recua à velocidade v; o pé toca com a ponta levantada, fica plano,
    solta o calcanhar e sai pela ponta. Balanço: spline pelas chaves (fração do caminho em Y, altura
    do tornozelo) e pela inclinação do pé, emendada com tangentes iguais às do apoio.
    """

    def __init__(self, v, quadros, apoio, plano, calcanhar, inc_toque, inc_saida, y_toque, chaves_balanco,
                 chaves_inc):
        self.v, self.quadros, self.duracao, self.apoio = v, quadros, quadros / FPS, apoio
        self.plano, self.calcanhar = plano, calcanhar
        self.inc_toque, self.inc_saida, self.y_toque = inc_toque, inc_saida, y_toque
        self.chaves_balanco, self.chaves_inc = chaves_balanco, chaves_inc

    def inc_apoio(self, u):
        if u < self.plano:
            return self.inc_toque * (1 - u / self.plano) ** 2
        if u < self.calcanhar:
            return 0.0
        return -self.inc_saida * ((u - self.calcanhar) / (self.apoio - self.calcanhar)) ** 1.6

    def no_apoio(self, lado, x, u):
        inc = self.inc_apoio(u)
        tz, dedo = pe_no_chao(lado, x, self.y_toque + self.v * self.duracao * u, inc)
        return tz, inc, dedo

    def pe(self, lado: str, x: float, u: float) -> tuple:
        u %= 1.0
        D = self.apoio
        if u <= D:
            return self.no_apoio(lado, x, u)
        e = 0.015
        antes = [D - 2 * e, D - e, D]
        depois = [1.0, 1.0 + e, 1.0 + 2 * e]
        pa = {k: self.no_apoio(lado, x, k) for k in antes}
        pd = {k: self.no_apoio(lado, x, k - 1.0) for k in depois}
        y0, y1 = pa[D][0].y, pd[1.0][0].y
        chaves = ([(k, pa[k][0]) for k in antes]
                  + [(D + f * (1 - D), Vector((x, y0 + fy * (y1 - y0), z))) for f, fy, z in self.chaves_balanco]
                  + [(k, pd[k][0]) for k in depois])
        tz = spline(u, chaves)
        incs = ([(k, pa[k][1]) for k in antes] + [(D + f * (1 - D), g) for f, g in self.chaves_inc]
                + [(k, pd[k][1]) for k in depois])
        inc = spline(u, incs)
        sb = (u - D) / (1 - D)
        dedo = pa[D][2] + (inc - pa[D][2]) * suave(0.0, 0.35, sb)
        return tz, inc, dedo


# ------------------------------------------------------------------ aplicação

def base_parado(p: Pose, abertura: float = 0.0) -> Pose:
    """Braços junto ao corpo (o rig vem em pose A) e dedos relaxados. Usada pelas ações de trabalho."""
    for lado in ("l", "r"):
        sinal = 1 if lado == "l" else -1
        p.girar(f"upperarm_{lado}", Y, sinal * (40 - abertura))
        p.frente(f"upperarm_{lado}", 4)
        p.frente(f"lowerarm_{lado}", 12)
    return p


COTOVELO_REPOUSO = 43.0  # o rig vem com o cotovelo dobrado 43° para a frente


def cotovelo(p: Pose, lado: str, graus: float) -> Pose:
    """Dobra o cotovelo até `graus` (0 = braço reto)."""
    return p.frente(f"lowerarm_{lado}", graus - COTOVELO_REPOUSO)


def base_relaxado(p: Pose, abertura: float = 12.0, cotovelo_graus: float = 18.0) -> Pose:
    """Braços soltos: afastados do tronco, cotovelos um pouco dobrados, palmas para as coxas."""
    for lado in ("l", "r"):
        sinal = 1 if lado == "l" else -1
        p.girar(f"upperarm_{lado}", Y, sinal * (41.8 - abertura))
        p.frente(f"upperarm_{lado}", 2)
        p.torce(f"upperarm_{lado}", -sinal * 6)
        cotovelo(p, lado, cotovelo_graus)
        p.lado(f"lowerarm_{lado}", 4)
        p.frente(f"hand_{lado}", 6)
        p.lado(f"hand_{lado}", -4)
    return p


def dedos_curvos(p: Pose, graus: float, lado: str):
    p.__dict__.setdefault("curvas", {})[lado] = graus
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


def aplicar(arm, pose: Pose, quadro: int | None) -> None:
    """Aplica a pose e grava chave no quadro (sem chave se quadro for None). Rotações do usuário são em eixos fixos do personagem, aplicadas depois das do pai.

    Delta global do osso: W = Q · W_pai. Rotação local no Blender: L = R⁻¹ · W_pai⁻¹ · W · R,
    em que R é a orientação de repouso do osso no espaço da armature.
    """
    globais: dict[str, Quaternion] = {}
    curvas = getattr(pose, "curvas", {})
    for nome in ordem_hierarquica(arm):
        pb = arm.pose.bones[nome]
        pb.rotation_mode = "QUATERNION"
        rest = pb.bone.matrix_local.to_3x3().to_quaternion()
        q = pose.rot.get(pb.name, Quaternion())
        w_pai = globais.get(pb.parent.name, Quaternion()) if pb.parent else Quaternion()
        w = q @ w_pai
        globais[nome] = w
        local = rest.inverted() @ w_pai.inverted() @ w @ rest
        # dedos: curva no eixo X local do osso, graduada por dedo e falange
        lado = pb.name[-1:]
        if pb.name[:-2] in DEDOS and lado in curvas:
            dedo, falange = pb.name[:-2].split("_")
            g = curvas[lado] * FATOR_DEDO[dedo] * FATOR_FALANGE[falange]
            local = local @ Quaternion(Vector((1, 0, 0)), math.radians(g))
        pb.rotation_quaternion = local
        if quadro is not None:
            pb.keyframe_insert("rotation_quaternion", frame=quadro)
        if pb.name == "pelvis":
            pb.location = rest.inverted() @ pose.desloc
            if quadro is not None:
                pb.keyframe_insert("location", frame=quadro)


def nova_acao(arm, nome: str):
    acao = bpy.data.actions.new(nome)
    acao.use_fake_user = True
    if not arm.animation_data:
        arm.animation_data_create()
    arm.animation_data.action = acao
    return acao


UNICAS = {"interagir", "morrer", "aterrissar_leve", "aterrissar_pesado", "giro_rapido"}


def ciclo(arm, nome: str, quadros: int, gerar_pose, passos: int | None = None) -> None:
    """Gera uma ação amostrando gerar_pose(t). Laços usam t em [0, 1) e repetem o primeiro quadro
    no fim; ações de uma vez (UNICAS) vão até t = 1, para não voltar à pose inicial no último quadro."""
    nova_acao(arm, nome)
    passos = passos or quadros
    ALCANCE.clear()
    for i in range(passos + 1):
        t = i / passos if nome in UNICAS else (i % passos) / passos
        posar(arm, gerar_pose(t), round(i * quadros / passos) + 1)
    if ALCANCE:
        print(f"IK {nome}: maior alcance pedido {max(ALCANCE):.3f} do comprimento da perna")
    # empilha no NLA para que o exportador encontre a ação mesmo sem estar ativa
    trilha = arm.animation_data.nla_tracks.new()
    trilha.name = nome
    trilha.strips.new(nome, 1, arm.animation_data.action)
    trilha.mute = True
    arm.animation_data.action = None


# ------------------------------------------------------------------ ciclos

def estabilizar_cabeca(p: Pose, giro_tronco: float, rolagem_tronco: float, olhar: float = 0.0,
                       inclina_cabeca: float = 0.0) -> None:
    """Pescoço e cabeça desfazem o giro e a rolagem do tronco: o olhar fica estável."""
    p.torce("neck_01", -0.4 * giro_tronco + 0.4 * olhar)
    p.torce("head", -0.6 * giro_tronco + 0.6 * olhar)
    p.rola("neck_01", -0.5 * rolagem_tronco)
    p.rola("head", -0.5 * rolagem_tronco)
    p.inclina("head", inclina_cabeca)


def respiracao(t: float, ciclos: int) -> float:
    """0 a 1: inspira em 40% do ciclo e solta o ar devagar."""
    return curva((t * ciclos) % 1.0, [(0.0, 0.0), (0.4, 1.0)])


def parado(t):
    """Respira, troca o apoio de uma perna para a outra e olha em volta. Pés fixos por IK."""
    p = base_relaxado(Pose(), abertura=14, cotovelo_graus=22)
    # peso: +1 na perna esquerda; segura, troca, segura (tempos desiguais)
    w = curva(t, [(0.0, 0.7), (0.2, 0.8), (0.38, 0.55), (0.52, -0.6), (0.7, -0.75), (0.86, -0.5)])
    resp = respiracao(t, 2)
    p.desloc = Vector((0.032 * w, 0.0, -0.005 - 0.008 * abs(w)))
    rol_pelvis = -3.8 * w
    p.rola("pelvis", rol_pelvis)
    p.torce("pelvis", 1.8 * w)
    p.inclina("pelvis", 1.0)
    # coluna em contraposto: ombros inclinam ao contrário do quadril
    p.rola("spine_01", 1.9 * w)
    p.rola("spine_02", 1.7 * w)
    p.rola("spine_03", 0.9 * w)
    p.torce("spine_02", -1.0 * w)
    p.inclina("spine_02", 1.0 - 0.7 * resp)
    p.inclina("spine_03", 0.5 - 0.6 * resp)
    for lado, sinal in (("l", 1), ("r", -1)):
        p.lado(f"clavicle_{lado}", 1.3 * resp - 0.6)
        # braços pendem com a gravidade e acompanham, com atraso, o peso e a respiração
        p.lado(f"upperarm_{lado}", -0.9 * w * sinal + 0.6 * resp)
        p.frente(f"upperarm_{lado}", 1.2 * s(t, 0.1 + 0.25 * sinal) - 0.5 * resp)
        cotovelo(p, f"{lado}", 18 + 2.0 * s(t, 0.2 + 0.25 * sinal) + 1.5 * resp)
        dedos_curvos(p, 13 + 3 * s(t, 0.3 * sinal), lado)
    olhar = curva(t, [(0.0, 0.0), (0.16, 5.0), (0.3, 6.0), (0.5, -1.0), (0.68, -6.0), (0.84, -4.0)])
    acena = curva(t, [(0.0, 0.0), (0.25, -2.0), (0.55, 1.5), (0.8, 0.5)])
    rol_tronco = rol_pelvis + 4.5 * w
    estabilizar_cabeca(p, giro_tronco=0.8 * w, rolagem_tronco=rol_tronco * 0.8, olhar=olhar,
                       inclina_cabeca=-1.5 + acena + 0.4 * resp)
    p.inclina("neck_01", 0.6 * resp)
    # pés: o esquerdo um pouco à frente; a perna livre dobra o joelho e solta o calcanhar
    livre_l, livre_r = max(0.0, -w), max(0.0, w)
    h0 = G["calcanhar_l"].y
    apoiar(p, "l", 0.15, h0 - 0.03, -9 * livre_l ** 2)
    apoiar(p, "r", -0.155, h0 + 0.035, -9 * livre_r ** 2)
    p.torce("thigh_l", 5)
    p.torce("thigh_r", -6)
    return p


def _pes_marcha(p: Pose, m: Marcha, t: float, largura: float) -> None:
    for lado, fase, x in (("l", 0.0, largura), ("r", 0.5, -largura)):
        p.pes[lado] = m.pe(lado, x, t - fase)


MARCHA_ANDAR = Marcha(v=1.95, quadros=24, apoio=0.53, plano=0.09, calcanhar=0.3, inc_toque=16, inc_saida=62,
                      y_toque=-0.26, chaves_balanco=[(0.2, 0.1, 0.18), (0.5, 0.55, 0.13), (0.78, 0.93, 0.1)],
                      chaves_inc=[(0.18, -30.0), (0.42, -6.0), (0.7, 6.0), (0.88, 13.0)])


def andar(t):
    p = base_relaxado(Pose(), abertura=8, cotovelo_graus=20)
    m = MARCHA_ANDAR
    _pes_marcha(p, m, t, 0.11)
    passo = (2 * t) % 1.0  # 0 em cada toque de calcanhar
    # centro de massa: mais baixo logo depois do toque, mais alto no meio do apoio
    alt = curva(passo, [(0.0, -0.058), (0.09, -0.066), (0.5, -0.01)])
    lateral = 0.02 * s(t, -0.06)  # sobre a perna de apoio
    p.desloc = Vector((lateral, 0.0, alt))
    # quadril: gira com a perna que avança e cai do lado da perna em balanço
    giro_p = -5.0 * c(t, -0.02)
    queda = curva(t, [(0.0, 0.2), (0.14, 1.0), (0.4, 0.15), (0.5, -0.2), (0.64, -1.0), (0.9, -0.15)])
    p.torce("pelvis", giro_p)
    p.rola("pelvis", -3.0 * queda)
    p.inclina("pelvis", 2.0 + 0.8 * c(2 * t, -0.1))
    # tronco: contra-rotação com atraso crescente ao subir a coluna
    giro_t = 4.5 * c(t, -0.06)
    total = giro_t - giro_p
    p.torce("spine_01", 0.3 * total)
    p.torce("spine_02", 0.35 * total)
    p.torce("spine_03", 0.35 * total)
    p.rola("spine_01", 2.0 * queda)
    p.rola("spine_02", 1.6 * queda)
    p.inclina("spine_01", 1.5)
    p.inclina("spine_02", 1.5 + 0.8 * c(2 * t, -0.15))
    estabilizar_cabeca(p, giro_t, 0.6 * queda, inclina_cabeca=-3.0 - 1.0 * c(2 * t, -0.2))
    # braços: balanço oposto às pernas; antebraço e mão atrasam (movimento secundário)
    for lado, fase in (("l", 0.5), ("r", 0.0)):
        sinal = 1 if lado == "l" else -1
        b = c(t, -fase - 0.05)
        p.frente(f"upperarm_{lado}", 14.0 * b - 2.5 * b * b)
        cotovelo(p, lado, 20 + 9 * (1 + c(t, -fase - 0.13)))
        p.frente(f"hand_{lado}", 5 * c(t, -fase - 0.2))
        p.torce(f"clavicle_{lado}", -2.5 * b * sinal)
        dedos_curvos(p, 14 + 4 * c(t, -fase - 0.15), lado)
    return p


MARCHA_CORRER = Marcha(v=6.7, quadros=20, apoio=0.17, plano=0.03, calcanhar=0.08, inc_toque=6, inc_saida=64,
                       y_toque=-0.22, chaves_balanco=[(0.18, 0.04, 0.3), (0.4, 0.38, 0.47), (0.64, 0.84, 0.37),
                                                      (0.84, 1.03, 0.17)],
                       chaves_inc=[(0.22, -62.0), (0.5, -38.0), (0.76, -4.0), (0.9, 10.0)])


def correr(t):
    p = base_relaxado(Pose(), abertura=8, cotovelo_graus=80)
    m = MARCHA_CORRER
    _pes_marcha(p, m, t, 0.065)
    passo = (2 * t) % 1.0
    D = m.apoio * 2  # fração do passo em apoio
    # mais baixo no meio do apoio, voo balístico entre a saída e o próximo toque
    alt = curva(passo, [(0.0, -0.063), (D * 0.5, -0.085), (D, -0.059), ((1 + D) / 2, -0.027)])
    queda = curva(t, [(0.0, 0.3), (0.1, 1.0), (0.25, 0.2), (0.5, -0.3), (0.6, -1.0), (0.75, -0.2)])
    p.desloc = Vector((0.012 * queda, 0.0, alt))
    giro_p = -7.0 * c(t, -0.03)
    p.torce("pelvis", giro_p)
    p.rola("pelvis", -4.0 * queda)
    p.inclina("pelvis", 5.0 + 1.5 * c(2 * t, -0.12))
    giro_t = 8.0 * c(t, -0.05)
    total = giro_t - giro_p
    p.torce("spine_01", 0.3 * total)
    p.torce("spine_02", 0.35 * total)
    p.torce("spine_03", 0.35 * total)
    p.rola("spine_01", 2.4 * queda)
    p.rola("spine_02", 2.0 * queda)
    p.inclina("spine_01", 4.0)
    p.inclina("spine_02", 3.0 + 1.2 * c(2 * t, -0.2))
    estabilizar_cabeca(p, giro_t, 0.4 * queda, inclina_cabeca=-9.0 - 1.5 * c(2 * t, -0.25))
    for lado, fase in (("l", 0.5), ("r", 0.0)):
        sinal = 1 if lado == "l" else -1
        b = c(t, -fase - 0.04)
        p.frente(f"upperarm_{lado}", 30.0 * b - 6.0 * b * b)
        p.lado(f"upperarm_{lado}", -4.0 * b - 3)
        p.torce(f"upperarm_{lado}", 6 * b * sinal)
        cotovelo(p, lado, 80 + 12 * c(t, -fase - 0.12))
        p.frente(f"hand_{lado}", 6 * c(t, -fase - 0.2) - 4)
        p.torce(f"clavicle_{lado}", -4.0 * b * sinal)
        p.lado(f"clavicle_{lado}", -1.5)
        dedos_curvos(p, 58 + 5 * c(t, -fase - 0.15), lado)
    return p


def pular(t):
    """No ar: uma perna recolhida à frente, a outra solta atrás, braços abertos para equilibrar."""
    p = base_relaxado(Pose(), abertura=26, cotovelo_graus=40)
    d = s(t)
    p.frente("thigh_l", 52 + 4 * d)
    p.frente("calf_l", -88 - 4 * d)
    p.frente("foot_l", 12)
    p.frente("thigh_r", 8 - 3 * d)
    p.frente("calf_r", -52 + 4 * s(t, 0.1))
    p.frente("foot_r", -18)
    p.lado("thigh_l", 3)
    p.lado("thigh_r", 4)
    p.frente("upperarm_l", -18 + 4 * s(t, 0.08))
    p.frente("upperarm_r", 30 + 4 * s(t, 0.08))
    p.lado("upperarm_l", 14)
    p.lado("upperarm_r", 10)
    cotovelo(p, "r", 55 + 4 * s(t, 0.15))
    p.torce("pelvis", 6)
    p.torce("spine_02", -8)
    p.inclina("spine_01", 4)
    p.inclina("spine_02", 5 + 1.5 * s(t, 0.2))
    p.inclina("head", -6)
    p.torce("head", 2)
    for lado in ("l", "r"):
        dedos_curvos(p, 30, lado)
    return p


def agachar(t, andando=False):
    """Agachado de prontidão: um pé à frente, o de trás na bola do pé; tronco inclinado, braços soltos à frente."""
    p = base_relaxado(Pose(), abertura=16, cotovelo_graus=50)
    resp = respiracao(t, 2 if andando else 1)
    if andando:
        m = MARCHA_AGACHADO
        _pes_marcha(p, m, t, 0.13)
        passo = (2 * t) % 1.0
        alt = curva(passo, [(0.0, -0.3), (0.1, -0.312), (0.5, -0.282)])
        queda = curva(t, [(0.0, 0.2), (0.15, 1.0), (0.42, 0.1), (0.5, -0.2), (0.65, -1.0), (0.92, -0.1)])
        p.desloc = Vector((0.025 * s(t, -0.06), 0.07, alt))
        giro_p = -6.0 * c(t, -0.02)
        p.torce("pelvis", giro_p)
        p.rola("pelvis", -3.0 * queda)
        giro_t = 4.0 * c(t, -0.06)
        p.torce("spine_02", 0.6 * (giro_t - giro_p))
        p.torce("spine_03", 0.4 * (giro_t - giro_p))
        p.rola("spine_02", 2.4 * queda)
        for lado, fase in (("l", 0.5), ("r", 0.0)):
            b = c(t, -fase - 0.05)
            p.frente(f"upperarm_{lado}", 22 + 12 * b)
            cotovelo(p, lado, 50 + 10 * c(t, -fase - 0.14))
            dedos_curvos(p, 32 + 4 * c(t, -fase - 0.15), lado)
        estabilizar_cabeca(p, giro_t, 0.6 * queda, inclina_cabeca=-24)
    else:
        p.desloc = Vector((0.01 * s(t), 0.08, -0.36 + 0.004 * resp))
        p.rola("pelvis", -3)
        p.torce("pelvis", -6)
        h0 = G["calcanhar_l"].y
        apoiar(p, "l", 0.17, h0 - 0.12, 0.0)
        apoiar(p, "r", -0.16, h0 + 0.16, -38.0)
        p.torce("thigh_l", 8)
        p.torce("thigh_r", -10)
        p.torce("spine_02", 4)
        p.frente("upperarm_l", 24 + 1.5 * resp)
        p.frente("upperarm_r", 30 + 1.5 * resp)
        p.lado("upperarm_l", 4)
        cotovelo(p, "r", 58)
        for lado in ("l", "r"):
            dedos_curvos(p, 32, lado)
        estabilizar_cabeca(p, 2, -1, olhar=3 * s(t, 0.1), inclina_cabeca=-26 + 1.5 * resp)
    p.inclina("pelvis", 14)
    p.inclina("spine_01", 10)
    p.inclina("spine_02", 6 - 1.2 * resp)
    p.inclina("spine_03", -0.8 * resp)
    return p


MARCHA_AGACHADO = Marcha(v=1.3, quadros=26, apoio=0.6, plano=0.1, calcanhar=0.36, inc_toque=10, inc_saida=34,
                         y_toque=-0.2, chaves_balanco=[(0.25, 0.15, 0.16), (0.55, 0.6, 0.14), (0.8, 0.95, 0.1)],
                         chaves_inc=[(0.25, -16.0), (0.55, 0.0), (0.85, 9.0)])


def escada(t):
    """Subindo escada de costas para a câmera: alcança rápido, puxa devagar; o tronco acompanha o braço."""
    p = base_parado(Pose())
    for lado, fase in (("l", 0.0), ("r", 0.5)):
        # 0 = mão embaixo, 1 = mão no alto; sobe em 35% do ciclo e desce (puxando) no resto
        a = curva(t + fase, [(0.0, 0.0), (0.35, 1.0)])
        # o pé do mesmo lado sobe com a mão do outro lado, um pouco depois dela
        pe = curva(t + fase + 0.5 - 0.08, [(0.0, 0.0), (0.38, 1.0)])
        p.frente(f"upperarm_{lado}", 112 + 52 * a)
        p.lado(f"upperarm_{lado}", -18 + 4 * a)
        p.frente(f"lowerarm_{lado}", 58 - 52 * a)
        p.frente(f"thigh_{lado}", 12 + 68 * pe)
        p.frente(f"calf_{lado}", -(22 + 88 * pe))
        p.frente(f"foot_{lado}", 10 + 6 * pe)
        dedos_curvos(p, 72 - 14 * suave(0.6, 0.95, a), lado)
    braco = curva(t, [(0.0, 0.0), (0.35, 1.0)]) - curva(t + 0.5, [(0.0, 0.0), (0.35, 1.0)])
    p.rola("spine_02", 2.5 * braco)
    p.torce("spine_02", 3 * braco)
    p.rola("pelvis", -2 * braco)
    p.inclina("spine_02", 4)
    p.inclina("head", -14 + 2 * c(2 * t, 0.1))
    p.torce("head", -3 * braco)
    p.desloc = Vector((0.012 * braco, 0, 0.018 * curva(2 * t, [(0.0, 0.0), (0.4, 1.0)])))
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


def aterrissar(t, pesado=False):
    """Pés plantados por IK: o corpo afunda logo depois do impacto, os braços seguem com atraso e
    o corpo volta a ficar de pé com suavidade."""
    prof = 1.0 if pesado else 0.42
    k = spline(t, [(0.0, 0.55), (0.12 if pesado else 0.16, 1.0), (0.5, 0.3), (1.0, 0.0)])
    kb = spline(t, [(0.0, 0.3), (0.28, 1.0), (0.65, 0.2), (1.0, 0.0)])
    p = base_relaxado(Pose(), abertura=12 + 14 * kb * prof, cotovelo_graus=20 + 25 * kb)
    p.desloc = Vector((0.0, 0.06 * k * prof, -0.012 - 0.33 * prof * k))
    h0 = G["calcanhar_l"].y
    apoiar(p, "l", 0.16, h0 - 0.05, 0.0)
    apoiar(p, "r", -0.16, h0 + 0.04, 0.0)
    p.torce("thigh_l", 6)
    p.torce("thigh_r", -6)
    p.inclina("pelvis", 12 * prof * k)
    p.inclina("spine_01", 14 * prof * k)
    p.inclina("spine_02", 6 * prof * kb)
    for lado in ("l", "r"):
        p.frente(f"upperarm_{lado}", (32 if pesado else 14) * kb)
        dedos_curvos(p, 24 + 22 * kb, lado)
    p.inclina("head", -16 * prof * k)
    return p


def giro_rapido(t):
    """Inversão brusca: pés plantados, tronco inclinado para o lado do giro, braços abertos."""
    k = math.sin(math.pi * t)
    p = base_parado(Pose(), abertura=25 * k)
    p.torce("spine_01", -25 * k)
    p.torce("spine_03", -20 * k)
    p.torce("head", -25 * k)
    p.girar("pelvis", Y, 8 * k)
    p.frente("thigh_l", 25 * k)
    p.frente("calf_l", -40 * k)
    p.frente("thigh_r", -15 * k)
    p.frente("calf_r", -20 * k)
    p.frente("upperarm_l", -20 * k)
    p.frente("upperarm_r", 30 * k)
    p.lado("upperarm_l", 30 * k)
    p.lado("upperarm_r", 20 * k)
    p.inclina("spine_02", 8 * k)
    for lado in ("l", "r"):
        dedos_curvos(p, 35, lado)
    p.desloc = Vector((0, 0, -0.06 * k))
    return p


def corda(t):
    """Subida em corda, mão sobre mão: a mão de cima puxa devagar, a de baixo sobe rápido; pernas prendem a corda."""
    p = base_parado(Pose())
    for lado, fase in (("l", 0.0), ("r", 0.5)):
        a = curva(t + fase, [(0.0, 0.0), (0.32, 1.0)])
        pe = curva(t + fase + 0.12, [(0.0, 0.0), (0.4, 1.0)])
        p.frente(f"upperarm_{lado}", 140 + 34 * a)
        p.lado(f"upperarm_{lado}", -28 + 4 * a)
        p.frente(f"lowerarm_{lado}", 42 - 36 * a)
        p.frente(f"thigh_{lado}", 36 + 16 * pe)
        p.lado(f"thigh_{lado}", -6)
        p.frente(f"calf_{lado}", -(56 + 22 * pe))
        p.frente(f"foot_{lado}", 8)
        dedos_curvos(p, 85 - 12 * suave(0.55, 0.95, a), lado)
    braco = curva(t, [(0.0, 0.0), (0.32, 1.0)]) - curva(t + 0.5, [(0.0, 0.0), (0.32, 1.0)])
    p.rola("spine_02", 3 * braco)
    p.torce("spine_02", 4 * braco)
    p.torce("pelvis", -3 * braco)
    p.inclina("spine_02", -4)
    p.inclina("head", -18 + 2 * c(2 * t, 0.1))
    p.torce("head", -4 * braco)
    p.desloc = Vector((0.01 * braco, 0, 0.015 * curva(2 * t, [(0.0, 0.0), (0.35, 1.0)])))
    return p


ACOES = [
    ("parado", 150, parado), ("andar", MARCHA_ANDAR.quadros, andar), ("correr", MARCHA_CORRER.quadros, correr),
    ("pular", 40, pular), ("agachar", 80, agachar),
    ("agachar_andar", MARCHA_AGACHADO.quadros, lambda t: agachar(t, True)), ("escada", 30, escada),
    ("interagir", 24, interagir), ("varrer", 40, varrer), ("consertar", 30, consertar),
    ("cozinhar", 40, cozinhar), ("rezar", 80, rezar), ("conversar", 90, conversar), ("sentar", 80, sentar),
    ("acenar", 30, acenar), ("brincar", 26, brincar), ("morrer", 40, morrer), ("tossir", 45, tossir),
    ("aterrissar_leve", 12, aterrissar), ("aterrissar_pesado", 26, lambda t: aterrissar(t, True)),
    ("giro_rapido", 12, giro_rapido), ("corda", 36, corda),
]


def esqueleto_neutro():
    b = gp.vertices_personagem(APAR_NEUTRA)
    arm = gp.criar_armature(b)
    preparar_geometria(arm)
    return b, arm


def principal():
    comum.limpar_cena()
    bpy.context.scene.render.fps = FPS
    b, arm = esqueleto_neutro()
    # as ações são geradas antes de prender a malha: o IK avalia o esqueleto várias vezes por quadro
    for nome, quadros, funcao in ACOES:
        ciclo(arm, nome, quadros, funcao, passos=quadros if quadros <= 40 else quadros // 2)
    corpo = gp.construir_corpo(b, "previa_animacao")
    gp.decimar(corpo, 0.08)
    gp.vincular([corpo], arm)
    comum.atribuir(corpo, comum.material("previa_mat", (0.6, 0.6, 0.6)))
    print(f"ações: {[a.name for a in bpy.data.actions]}")
    comum.exportar_glb(SAIDA, selecionados=[arm, corpo], animacoes=True)


if __name__ == "__main__":
    principal()
