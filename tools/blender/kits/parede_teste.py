"""Fase 0: módulo de parede de concreto do reservatório, gerado por script."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import bpy  # noqa: E402,F401  (no módulo bpy, bmesh só existe depois de importar bpy)
import bmesh  # noqa: E402
import comum  # noqa: E402

comum.limpar_cena()
bm = bmesh.new()
comum.caixa(bm, (0, 0, 1.5), (4.0, 0.4, 3.0))
for i in range(-1, 2):  # pilastras
    comum.caixa(bm, (i * 1.8, -0.25, 1.5), (0.35, 0.2, 3.0))
comum.caixa(bm, (0, -0.3, 2.85), (4.0, 0.3, 0.3))  # viga
parede = comum.objeto_de_bmesh("parede_concreto", bm)
comum.biselar(parede, 0.03)
comum.aplicar_modificadores(parede)
comum.deformar_ruido(parede, escala=2.0, forca=0.015)
comum.suavizar(parede, 35)
comum.cor_vertice_desgaste(parede, sujeira=(0.45, 0.42, 0.38), forca=0.7)
comum.atribuir(parede, comum.material("concreto_umido", (0.55, 0.52, 0.48), 0.85))
comum.exportar_glb(os.path.join(comum.ASSETS, "teste", "parede.glb"))
