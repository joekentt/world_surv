"""Sinalização de rota em neon, da praça da vila até a eclusa da Boca do Poço (revisão 2, fase 2).

Seção 7 de docs/spec/07-arte-personagens-vila.md: letreiros de neon com seta e nome do destino marcam a rota
"vila -> Duto Norte -> Estação Aurora -> Boca do Poço -> superfície", sem minimapa e sem texto de tutorial.
Uma faixa de luz-guia (LED no chão ou na parede) acompanha a rota principal: magenta na vila, ciano no duto
e âmbar na estação, no poço e na eclusa.

Os letreiros vão para `letreiros` de cada área (montados em src/world/letreiros.ts); `texto` e `sub` são
chaves de content/textos/letreiros.json (nenhum texto do jogo aqui). As faixas de luz são caixas só visuais
(`semColisao`) com os materiais emissivos neon_* de src/world/construtor.ts: não mudam a colisão nem o navmesh.

Não usa números aleatórios: os geradores das áreas continuam produzindo o mesmo cenário.
Convenções do letreiro: (x, y, z) é o centro da face; `r` (graus) é para onde a face legível aponta
(0 = norte/+Z, 90 = leste/+X, 180 = sul, 270 = oeste); `seta` é relativa a quem lê (esquerda, direita,
frente, sobe, desce); `verso` é a face de trás (opcional); `suspenso` é a altura até onde sobem os cabos.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from subsolo_vila import V, r3  # noqa: E402

# perfis do piso do Duto Norte (subsolo_duto.py): (coordenada ao longo do trecho, altura)
PERFIL_N = [(45.0, 0.0), (58.0, 0.0), (98.0, -5.0), (160.0, -5.0), (195.0, -10.0), (209.0, -10.0)]
PERFIL_E = [(4.0, -10.0), (30.0, -10.0), (90.0, -20.0), (118.0, -20.0), (133.0, -25.0), (141.0, -25.0)]
ALT_DUTO = 5.5                       # altura livre do túnel
PASSAGENS_FENDA = ((101.5, 104.5), (153.5, 156.5))   # vãos na parede leste do trecho norte (z)


def piso(perfil, s):
    """Altura do piso do duto na coordenada s ao longo do trecho (interpolação do perfil)."""
    for (s0, y0), (s1, y1) in zip(perfil, perfil[1:]):
        if s0 <= s <= s1:
            return y0 + (y1 - y0) * (s - s0) / (s1 - s0)
    return perfil[0][1] if s < perfil[0][0] else perfil[-1][1]


def letreiro(a, id_, texto, x, y, z, r, largura, altura, cor, seta=None, sub=None, verso=None, suspenso=None):
    d = dict(id=id_, texto=texto, x=r3(x), y=r3(y), z=r3(z), r=r, largura=largura, altura=altura, cor=cor)
    if seta:
        d["seta"] = seta
    if sub:
        d["sub"] = sub
    if verso:
        d["verso"] = verso
    if suspenso is not None:
        d["suspenso"] = r3(suspenso)
    a.d.setdefault("letreiros", []).append(d)


def guia(a, pontos, cor, larg=0.06, alt=0.06):
    """Faixa de luz ao longo da polilinha (pontos em 3D): uma caixa emissiva girada por trecho reto."""
    for (x0, y0, z0), (x1, y1, z1) in zip(pontos, pontos[1:]):
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        h = math.hypot(dx, dz)
        comp = math.hypot(h, dy)
        if comp < 1e-3:
            continue
        s = dict(x=r3((x0 + x1) / 2), y=r3((y0 + y1) / 2), z=r3((z0 + z1) / 2), w=larg, h=alt, d=r3(comp),
                 mat=f"neon_{cor}", semColisao=True)
        ry = round(math.degrees(math.atan2(dx, dz)), 2)
        rx = round(-math.degrees(math.atan2(dy, h)), 2)
        if ry:
            s["ry"] = ry
        if rx:
            s["rx"] = rx
        a.d["solidos"].append(s)


def guia_tracejada(a, pontos, cor, traco=1.2, vao=0.8, larg=0.07, alt=0.025):
    """Faixa de LED no piso em traços (como balizas de pista), ao longo da polilinha."""
    for p, q in zip(pontos, pontos[1:]):
        comp = math.dist(p, q)
        s = 0.0
        while s < comp - 0.05:
            e = min(comp, s + traco)
            ponto = lambda t: tuple(p[i] + (q[i] - p[i]) * t / comp for i in range(3))  # noqa: E731
            guia(a, [ponto(s), ponto(e)], cor, larg, alt)
            s = e + vao


def parede_do_perfil(perfil, s0, s1, ponto, acima):
    """Pontos de uma faixa na parede do duto, `acima` m sobre o piso, quebrando nos joelhos do perfil."""
    ss = [s0] + [s for s, _ in perfil if s0 < s < s1] + [s1]
    return [ponto(s, piso(perfil, s) + acima) for s in ss]


# ====================================================================== áreas

def vila(a):
    """Praça: letreiro principal sob a ponte, Galerias nas colunas e nos pórticos, Duto Norte na parede norte."""
    # principal, pendurado na viga da ponte (z = -6), visto do ponto inicial do jogo
    letreiro(a, "praca_duto", "duto_norte", 0.0, 4.45, -6.3, 180, 5.6, 1.5, "ciano", seta="frente",
             sub="rota_estacao_superficie", verso=dict(texto="vila", sub="praca", cor="magenta"), suspenso=7.2)
    # Galerias Secas: placas nas colunas (-6, -6) e (6, -6), viradas para o sul, e sobre os dois acessos
    letreiro(a, "praca_galerias_oeste", "galerias", -6.0, 3.1, -6.82, 180, 3.0, 0.85, "verde", seta="esquerda", sub="acesso_oeste")
    letreiro(a, "praca_galerias_leste", "galerias", 6.0, 3.1, -6.82, 180, 3.0, 0.85, "verde", seta="direita", sub="acesso_leste")
    letreiro(a, "galerias_acesso_oeste", "galerias", -25.75, 4.35, -0.25, 90, 3.2, 0.8, "verde", seta="desce",
             verso=dict(texto="galerias", seta="desce", cor="verde"))
    letreiro(a, "galerias_acesso_leste", "galerias", 38.0, 4.35, -12.0, 270, 3.2, 0.8, "verde", seta="desce",
             verso=dict(texto="galerias", seta="desce", cor="verde"))
    # boca do Duto Norte: sobre o pórtico, na parede norte da caverna
    letreiro(a, "boca_duto", "duto_norte", 0.0, 7.45, 44.3, 180, 6.4, 1.5, "ciano", seta="frente", sub="rota_estacao_superficie")
    # faixa magenta no piso, do ponto inicial até a boca do duto (ao lado do eixo dos trilhos)
    guia_tracejada(a, [(1.1, 0.015, -15.0), (1.1, 0.015, 45.0)], "magenta")


def duto(a):
    """Duto Norte: placas penduradas antes de cada desvio e na curva; faixa ciano na parede interna da rota."""
    def suspenso_n(id_, z, **k):
        y = piso(PERFIL_N, z)
        letreiro(a, id_, "estacao_aurora", 0.0, y + 3.9, z, 180, 5.4, 1.0, "ciano", suspenso=y + ALT_DUTO, **k)

    def suspenso_e(id_, x, **k):
        y = piso(PERFIL_E, x)
        letreiro(a, id_, "estacao_aurora", x, y + 3.9, 205.0, 270, 5.4, 1.0, "ciano", suspenso=y + ALT_DUTO, **k)

    suspenso_n("duto_antes_fenda_a", 90.0, seta="frente", sub="superficie")
    suspenso_n("duto_antes_fenda_b", 146.0, seta="frente", sub="superficie")
    suspenso_n("duto_curva", 197.0, seta="direita", sub="superficie")
    suspenso_e("duto_leste_1", 45.0, seta="frente", sub="superficie")
    suspenso_e("duto_leste_2", 95.0, seta="frente", sub="superficie")
    # sobre o portão do fim do duto
    letreiro(a, "duto_portao", "estacao_aurora", 139.45, -20.15, 205.0, 270, 4.2, 0.6, "ambar")
    # desvios: o nome da caverna sobre as passagens (verde, fora da rota)
    for i, (z0, z1) in enumerate(PASSAGENS_FENDA):
        zc = (z0 + z1) / 2
        letreiro(a, f"duto_fenda_{'ab'[i]}", "fenda", 3.93, -5.0 + 3.35, zc, 270, 3.4, 0.5, "verde")

    # faixa ciano: parede leste do trecho norte (interrompida nos vãos da Fenda) e parede sul do trecho leste
    acima = 1.3
    cortes = [45.2] + [v for p in PASSAGENS_FENDA for v in p] + [201.0]
    for z0, z1 in zip(cortes[0::2], cortes[1::2]):
        guia(a, parede_do_perfil(PERFIL_N, z0, z1, lambda s, y: (3.96, y, s), acima), "ciano")
    guia(a, parede_do_perfil(PERFIL_E, 4.0, 139.8, lambda s, y: (s, y, 201.04), acima), "ciano")


def estacao(a):
    """Estação Aurora: placa na entrada da ilha e sobre a porta do poço; faixa âmbar no piso até a porta."""
    letreiro(a, "estacao_entrada", "boca_do_poco", 156.0, -21.0, 202.0, 270, 4.8, 1.0, "ambar", seta="frente", sub="superficie",
             suspenso=-13.0)
    letreiro(a, "estacao_porta_poco", "superficie", 176.85, -21.85, 201.93, 180, 3.0, 0.7, "ambar", seta="sobe")
    y = -25.0 + 0.015
    guia_tracejada(a, [(140.3, y, 205.0), (146.0, y, 201.2), (176.85, y, 201.2), (176.85, y, 201.95)], "ambar")


def boca_estacao(a):
    """Boca do Poço (subsolo): faixas verticais no poço e no piso do topo até a eclusa; placas na casa do poço."""
    for z in (202.7, 207.3):
        guia(a, [(175.53, -25.0, z), (175.53, -0.35, z)], "ambar")
    letreiro(a, "poco_casa", "eclusa", 181.8, 1.9, 209.93, 180, 3.4, 0.9, "ambar", seta="esquerda", sub="superficie")
    letreiro(a, "poco_eclusa", "superficie", 178.0, 3.15, 220.42, 180, 3.0, 0.5, "ambar", seta="frente")
    y = 0.015
    guia_tracejada(a, [(177.0, y, 203.6), (174.6, y, 203.6), (174.6, y, 208.6), (178.0, y, 208.6), (178.0, y, 219.9)], "ambar",
                   traco=0.8, vao=0.5)


def superficie_boca(a):
    """Superfície: placa sobre a porta da eclusa e pórtico na passagem norte do pátio, apontando a volta."""
    letreiro(a, "sup_eclusa_porta", "eclusa", 0.0, 4.1, 5.12, 0, 4.4, 0.7, "ambar", seta="desce", sub="vila")
    for x in (-7.0, 7.0):  # pórtico sobre as barreiras da passagem norte (só visual)
        V(a, x - 0.12, x + 0.12, 0.9, 7.4, 13.58, 13.82, "ferro")
    V(a, -7.12, 7.12, 7.2, 7.45, 13.58, 13.82, "ferro")
    letreiro(a, "sup_portico", "eclusa", 0.0, 6.35, 13.7, 0, 5.4, 1.3, "ambar", seta="frente", sub="vila", suspenso=7.2)


SINAIS = {
    "vila_cisterna": vila,
    "duto_tunel": duto,
    "estacao_aurora": estacao,
    "boca_estacao": boca_estacao,
    "superficie_boca": superficie_boca,
}


def sinalizar(areas):
    """Aplica a sinalização às áreas que a têm e devolve a mesma lista."""
    for a in areas:
        f = SINAIS.get(a.d["id"])
        if f:
            f(a)
    return areas
