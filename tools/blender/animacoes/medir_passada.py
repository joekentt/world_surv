"""Mede a velocidade de referência dos ciclos de locomoção (andar, correr, agachar_andar).

A velocidade de referência é a velocidade do personagem em que o pé de apoio fica parado no chão.
O pé rola do calcanhar para a bola e para a ponta, então o ponto de contato muda ao longo do apoio:
para cada ponto do pé (calcanhar, bola e ponta), enquanto ele está no chão, mede-se quanto ele recua
em relação ao corpo; a média é a velocidade em que o ciclo deve ser reproduzido a 1×. O valor vai
para `velocidadeReferenciaAndar` e `velocidadeReferenciaCorrer` em src/config.ts (o agachado usa
`agachado` como referência). Também mede a cadência e o comprimento da passada.

Uso: /opt/bpyenv/bin/python tools/blender/animacoes/medir_passada.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gerar_animacoes as ga  # noqa: E402

AMOSTRAS = 120
TOLERANCIA_APOIO = 0.006  # m acima da altura de repouso do ponto


def pontos_do_pe(arm, lado: str) -> dict:
    pe = arm.pose.bones[f"foot_{lado}"]
    bola = arm.pose.bones[f"ball_{lado}"]
    calcanhar = pe.matrix @ pe.bone.matrix_local.inverted() @ ga.G[f"calcanhar_{lado}"]
    return {"calcanhar": calcanhar, "bola": bola.head.copy(), "ponta": bola.tail.copy()}


def medir(arm, quadros: int, funcao) -> float:
    duracao = quadros / ga.FPS
    repouso = {}
    for lado in ("l", "r"):
        o = arm.data.bones
        repouso[lado] = {"calcanhar": ga.G[f"calcanhar_{lado}"].z, "bola": o[f"ball_{lado}"].head_local.z,
                         "ponta": o[f"ball_{lado}"].tail_local.z}
    series = {(lado, p): [] for lado in ("l", "r") for p in ("calcanhar", "bola", "ponta")}
    for i in range(AMOSTRAS + 1):
        ga.posar(arm, funcao(i / AMOSTRAS), None)
        ga.bpy.context.view_layer.update()
        for lado in ("l", "r"):
            for nome, pos in pontos_do_pe(arm, lado).items():
                series[(lado, nome)].append(pos)
    dt = duracao / AMOSTRAS
    velocidades = []
    for (lado, nome), pts in series.items():
        chao = repouso[lado][nome] + TOLERANCIA_APOIO
        for a, b in zip(pts, pts[1:]):
            if a.z < chao and b.z < chao:
                # o personagem olha para -Y: o pé de apoio recua para +Y
                velocidades.append((b.y - a.y) / dt)
    return sum(velocidades) / len(velocidades) if velocidades else 0.0


def principal():
    ga.comum.limpar_cena()
    _, arm = ga.esqueleto_neutro()
    acoes = {nome: (q, f) for nome, q, f in ga.ACOES}
    for nome in ("andar", "correr", "agachar_andar"):
        q, f = acoes[nome]
        v = medir(arm, q, f)
        print(f"PASSADA {nome}: {v:.2f} m/s, ciclo de {q / ga.FPS:.3f} s, passada de {v * q / ga.FPS:.2f} m")


if __name__ == "__main__":
    principal()
