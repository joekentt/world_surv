"""Mede a velocidade de referência dos ciclos de locomoção (andar, correr, agachar_andar).

A velocidade de referência é a velocidade do personagem em que o pé de apoio fica parado no chão:
durante o apoio (pé no ponto mais baixo do ciclo), o pé recua em relação ao corpo; a média dessa
velocidade é a velocidade em que o ciclo deve ser reproduzido a 1×. O valor vai para
`velocidadeReferenciaAndar` e `velocidadeReferenciaCorrer` em src/config.ts.

Uso: /opt/bpyenv/bin/python tools/blender/animacoes/medir_passada.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gerar_animacoes as ga  # noqa: E402

AMOSTRAS = 120
TOLERANCIA_APOIO = 0.02  # m acima do ponto mais baixo do pé


def medir(arm, nome: str, quadros: int, funcao) -> float:
    duracao = quadros / ga.FPS
    velocidades = []
    for osso in ("foot_l", "foot_r"):
        pontos = []
        for i in range(AMOSTRAS + 1):
            ga.aplicar(arm, funcao(i / AMOSTRAS), None)
            ga.bpy.context.view_layer.update()
            pb = arm.pose.bones[osso]
            pontos.append((arm.matrix_world @ pb.head).copy())
        menor = min(p.z for p in pontos)
        dt = duracao / AMOSTRAS
        for a, b in zip(pontos, pontos[1:]):
            if a.z < menor + TOLERANCIA_APOIO and b.z < menor + TOLERANCIA_APOIO:
                # o personagem olha para -Y: o pé de apoio recua para +Y
                velocidades.append((b.y - a.y) / dt)
    return sum(velocidades) / len(velocidades) if velocidades else 0.0


def principal():
    ga.comum.limpar_cena()
    apar = {"genero": 0.5, "idade_anos": 25, "peso": 0.5, "musculo": 0.5, "altura": 0.5, "proporcoes": 0.5,
            "semente": 1, "rosto": {}}
    b = ga.gp.vertices_personagem(apar)
    arm = ga.gp.criar_armature(b)
    acoes = {nome: (q, f) for nome, q, f in ga.ACOES}
    for nome in ("andar", "correr", "agachar_andar"):
        q, f = acoes[nome]
        print(f"PASSADA {nome}: {medir(arm, nome, q, f):.2f} m/s")


if __name__ == "__main__":
    principal()
