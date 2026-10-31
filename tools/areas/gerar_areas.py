"""Gera os layouts das áreas do MVP em content/areas/*.json.

Uso: python3 tools/areas/gerar_areas.py

As áreas são descritas aqui com funções de montagem (piso contínuo, paredes, colunas) e
posições escolhidas à mão para o desenho de fase; a decoração repetitiva usa sorteio com
semente fixa. Coordenadas do jogo: x lateral, y para cima, z profundidade (positivo se afasta
da câmera). O jogador anda em z = 0.
"""
from __future__ import annotations

import json
import os
import random

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DESTINO = os.path.join(RAIZ, "content", "areas")
R = random.Random(7)

AMBAR = [1.0, 0.68, 0.36]
FRIA = [0.55, 1.0, 0.9]
DOURADA = [1.0, 0.86, 0.55]
VERMELHA = [1.0, 0.12, 0.06]
MUSGO = [0.3, 0.95, 0.75]


class Area:
    def __init__(self, id_, nome, mundo, estetica, kit, inicio, fim, **extra):
        self.d = dict(id=id_, nome=nome, mundo=mundo, estetica=estetica, kit=kit, inicio=inicio, fim=fim,
                      solidos=[], escadas=[], pecas=[], fundo=[], saidas=[], entradas={}, luzes=[],
                      coletaveis=[], interativos=[], zonas=[], marcos=[], **extra)

    def solido(self, x, y, w, h, **k):
        self.d["solidos"].append(dict(x=round(x, 3), y=round(y, 3), w=round(w, 3), h=round(h, 3), **k))

    def plataforma(self, x0, x1, topo, esp=0.3, **k):
        self.solido((x0 + x1) / 2, topo - esp / 2, x1 - x0, esp, **k)

    def peca(self, m, x, y=0.0, z=0.0, r=0, e=None, fundo=False):
        p = dict(m=m, x=round(x, 3), y=round(y, 3), z=round(z, 3))
        if r:
            p["r"] = r
        if e is not None:
            p["e"] = e
        self.d["fundo" if fundo else "pecas"].append(p)

    def escada(self, x, y0, y1, tipo="escada", visual=True):
        self.d["escadas"].append(dict(x=x, y0=y0, y1=y1, tipo=tipo))
        if visual and tipo == "escada":
            self.peca("escada_mao", x, y0, 0.35, e=[1, y1 - y0 + 0.9, 1])

    def luz(self, x, y, z, cor, i, alcance=14, **k):
        self.d["luzes"].append(dict(x=x, y=y, z=z, cor=cor, i=i, alcance=alcance, **k))

    def saida(self, x, y, destino, entrada, rotulo, tipo="porta"):
        self.d["saidas"].append(dict(x=x, y=y, destino=destino, entrada=entrada, rotulo=rotulo, tipo=tipo))

    def entrada(self, nome, x, y=0.0):
        self.d["entradas"][nome] = dict(x=x, y=y)

    def coletavel(self, id_, item, x, y=0.0, qtd=1):
        self.d["coletaveis"].append(dict(id=id_, item=item, x=x, y=y, qtd=qtd))

    def interativo(self, id_, tipo, x, y=0.0, **k):
        self.d["interativos"].append(dict(id=id_, tipo=tipo, x=x, y=y, **k))

    def salvar(self):
        os.makedirs(DESTINO, exist_ok=True)
        with open(os.path.join(DESTINO, f"{self.d['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(self.d, f, ensure_ascii=False, indent=1)
        print(f"{self.d['id']}: {len(self.d['pecas'])} peças, {len(self.d['fundo'])} de fundo, "
              f"{len(self.d['solidos'])} sólidos, {len(self.d['luzes'])} luzes")


def piso(a: Area, modulo, x0, x1, passo=6.0, z=-3.0):
    x = x0 + passo / 2
    while x < x1 + passo / 2 - 0.01:
        a.peca(modulo, x, 0, z)
        x += passo


def linha(a: Area, modulo, x0, x1, passo, y=0.0, z=0.0, fundo=True, e=None):
    x = x0 + passo / 2
    while x < x1 - 0.01:
        a.peca(modulo, x, y, z, e=e, fundo=fundo)
        x += passo


# ====================================================================== vila

def capela():
    a = Area("capela", "Capela da Vigília", "vila", "capela", "capela", -150, -78)
    a.solido(-114, -0.5, 72, 1)
    a.solido(-150.5, 8, 1, 18)
    piso(a, "piso_capela", -150, -78)
    linha(a, "parede_capela", -150, -78, 6, z=5.5)
    a.peca("altar", -142, 0, 2.6)
    a.peca("facho", -142, 0, 2.2)
    for x in (-140, -128, -116):
        a.peca("vitral", x, 2.4, 5.45)
    for i, x in enumerate(range(-134, -101, 5)):
        a.peca("banco_madeira", x, 0, 1.3)
        a.peca("banco_madeira", x + 1, 0, 2.6)
    a.peca("maquina_velha", -96, 0, 3.2)
    a.peca("porta_capela", -80, 0, 1.8)
    a.peca("cano", -110, 7.2, 5.0)
    a.peca("cano", -96, 7.2, 5.0)
    a.peca("caixote", -88, 0, 2.8)
    a.peca("caixote", -87.2, 0, 3.3, r=20)
    a.peca("saco", -89.5, 0, 2.6)
    a.luz(-142, 8.5, 2.2, DOURADA, 2.6, 16, tipo="foco")
    a.luz(-128, 3.0, 4.2, [0.9, 0.55, 0.3], 0.9, 10)
    a.luz(-112, 4.5, 0.5, AMBAR, 0.9, 13)
    a.luz(-94, 4.5, 0.5, AMBAR, 0.8, 13)
    for x in (-128, -112, -94):
        a.peca("lampada", x, 5.6, 0.8)
    a.interativo("sermao", "ambiente", -130, som="sermao")
    a.entrada("inicio", -100)
    a.d["marcos"].append(dict(id="capela", x=-114, rotulo="Capela da Vigília"))
    return a


def praca():
    a = Area("praca", "Praça do Reservatório", "vila", "praca", "cisterna", -78, 52)
    a.solido(-13, -0.5, 130, 1)
    piso(a, "piso", -78, 52)
    linha(a, "parede_fundo", -78, 52, 6, z=9)
    for x in range(-72, 52, 12):
        a.peca("coluna", x, 0, 4.5)
    for x in (-50, 14):
        a.peca("coluna", x, 0, -5.5)
    a.peca("placa_reservatorio", -36, 5.6, 8.85)
    a.peca("sede_conselho", -63, 0, 2.4)
    for x in (-73, -44, 24, 38):
        a.peca("casa_fundo", x, 0, 6.2)
    a.peca("barraca_lona", -25, 0, 1.6)
    a.peca("barraca_lona", -14, 0, 1.6)
    a.peca("foto_ceu", -14.6, 1.25, 1.85)
    a.peca("foto_ceu", -13.6, 1.25, 1.85)
    a.peca("cozinha", -4, 0, 2.3)
    a.peca("mesa", -7, 0, 2.6)
    a.peca("banco", -8, 0, 2.2)
    a.peca("barraca_caravana", 5, 0, 1.4)
    a.peca("caixote", 8.5, 0, 2.2)
    a.peca("caixote", 9.3, 0, 2.6, r=15)
    a.peca("caixote", 8.9, 1.0, 2.4, r=40)
    a.peca("bomba", 18, 0, 2.6)
    a.peca("poca", 15, 0, 1.0)
    a.peca("poca", -40, 0, 0.6)
    a.peca("muro_subidores", 31, 0, 3.4)
    a.peca("mascara_darci_muro", 33.0, 1.5, 3.2)
    a.peca("banco", -10, 0, 3.0)
    a.peca("banco", 25, 0, 2.4)
    a.peca("banco", 10.5, 0, 2.6)
    a.peca("banco", -28, 0, 3.4)
    for x in (-48, -24, 0):
        a.peca("varal", x, 4.6, 3.6)
    a.peca("barril", -30, 0, 3.2)
    a.peca("barril", 12, 0, 3.4)
    a.peca("entulho", -76, 0, 2.0)
    # acesso ao Duto Norte
    a.plataforma(44, 52, 5.0, esp=0.25)
    a.peca("plataforma_metal", 46, 5.0, 0.0)
    a.peca("plataforma_metal", 50, 5.0, 0.0)
    a.escada(43, 0, 5.0)
    a.peca("escotilha", 49.5, 5.0, 1.0)
    a.saida(49.5, 5.0, "duto_norte", "vila", "Descer pelo Duto Norte")
    a.entrada("duto", 48.5, 5.0)
    a.entrada("inicio", -40)
    for x in range(-70, 50, 10):
        a.peca("lampada", x, 7.4, 1.2 + (x % 3))
    for x in range(-66, 50, 18):
        a.luz(x, 6.2, 0.6, AMBAR, 1.1, 18)
    a.luz(-63, 3.2, 1.0, AMBAR, 0.9, 9)
    a.luz(31, 4.0, 1.5, [1.0, 0.6, 0.35], 0.8, 8)
    a.interativo("balcao_cotas", "conselho", -61, z=2.0, rotulo="Balcão de cotas")
    a.interativo("muro", "muro", 31, rotulo="Muro dos Subidores")
    a.interativo("fotos", "fotos", -14, rotulo="Fotos do céu")
    a.interativo("fila", "fila", -55)
    a.d["marcos"].append(dict(id="praca", x=-13, rotulo="Praça do Reservatório"))
    return a


def galerias():
    a = Area("galerias", "Galerias Secas", "vila", "galerias", "gueto", 52, 140)
    a.solido(96, -0.5, 88, 1)
    a.solido(140.5, 8, 1, 18)
    piso(a, "piso", 52, 140)
    linha(a, "parede_rocha", 52, 140, 6, z=8.5)
    linha(a, "teto_galeria", 52, 140, 6, z=-3, fundo=False)
    tipos = ["barraco_a", "barraco_b", "barraco_c"]
    x = 55.0
    while x < 136:
        a.peca(R.choice(tipos), x, 0, 4.6)
        x += R.uniform(3.2, 4.0)
    # segundo nível: passarelas na faixa do jogador
    for x0, x1 in ((64, 84), (104, 128)):
        a.plataforma(x0, x1, 3.2, esp=0.2)
        xx = x0 + 2
        while xx < x1:
            a.peca("passarela", xx, 3.2, -0.2)
            xx += 4
        xx = x0 + 1.6
        while xx < x1 - 1:
            a.peca(R.choice(tipos), xx, 3.2, 4.6)
            xx += R.uniform(3.2, 4.0)
    a.escada(66, 0, 3.2)
    a.escada(126, 0, 3.2)
    # terceiro nível (exploração)
    a.plataforma(110, 122, 6.4, esp=0.2)
    for xx in (112, 116, 120):
        a.peca("passarela", xx, 6.4, -0.2)
    a.escada(121, 3.2, 6.4)
    a.coletavel("galerias_componente_alto", "componente", 113, 6.4)
    a.peca("pichacao", 60, 1.0, 8.4)
    a.peca("pichacao", 92, 1.0, 8.4)
    a.peca("pichacao_b", 115, 2.0, 4.55)
    a.peca("pichacao_b", 74, 5.2, 4.55)
    for x in range(55, 140, 6):
        a.peca("fiacao", x, 5.8, 1.5)
    a.peca("oficina", 100, 0, 1.6)
    for xb in (80, 108, 128):
        a.peca("banco", xb, 0, 2.4)
    a.peca("banca_filtros", 86, 0, 1.4)
    a.peca("caixote", 58, 0, 2.2)
    a.peca("saco", 59, 0, 2.6)
    a.peca("barril", 132, 0, 2.4)
    a.peca("entulho", 136, 0, 1.8)
    for x in range(58, 138, 9):
        a.peca("tubo_fluor", x, 8.6 if x % 2 else 5.9, 1.0)
    for i, x in enumerate(range(60, 138, 16)):
        a.luz(x, 5.5, 0.8, FRIA, 0.75, 14, piscar=(i % 2 == 0))
    a.luz(100, 2.6, 1.2, [0.9, 0.7, 0.45], 0.8, 7)
    a.interativo("banca_filtros", "banca", 86, rotulo="Filtros recondicionados")
    a.d["marcos"].append(dict(id="galerias", x=96, rotulo="Galerias Secas"))
    return a


# ====================================================================== duto norte

def duto_norte():
    a = Area("duto_norte", "Duto Norte", "duto", "duto", "tunel", 0, 132)
    a.solido(-0.5, 8, 1, 18)
    a.solido(132.5, 8, 1, 18)
    # túnel de metrô (0 a 74)
    a.solido(37, -0.5, 74, 1)
    linha(a, "tunel_segmento", 0, 74, 6, z=-0.6, fundo=False)
    linha(a, "trilho", 0, 74, 6, z=0)
    a.peca("vagao", 46, 0, 3.4)
    a.peca("placa_metro", 14, 3.2, 5.8)
    for x in (9, 27, 52, 66):
        a.peca("musgo", x, R.uniform(1, 3), 5.5)
    a.peca("poca", 22, 0, 0.8)
    a.peca("poca", 58, 0, 1.0)
    a.peca("entulho", 33, 0, 1.5)
    a.peca("caixote", 61, 0, 1.0)
    a.solido(61, 0.5, 1, 1)  # caixote no caminho: pula ou sobe
    a.peca("cano", 30, 4.5, 4.5)
    # caverna natural (74 a 132): terreno irregular
    a.solido(80, -0.5, 12, 1)
    a.solido(82, 0.4, 4, 0.8, mat="rocha")
    a.solido(88, -2.0, 4, 4)  # degrau para o fosso
    a.solido(93, -3.5, 6, 1)  # fundo do fosso
    a.escada(95.2, -3.0, 0.8)
    a.solido(101, 0.3, 8, 1.6)  # borda do outro lado (topo 1.1)
    a.solido(108, 0.0, 6, 2.0)  # topo 1.0
    a.solido(118, -0.5, 14, 1)
    a.solido(126, 2.0, 12, 0.4)  # saliência da saída (topo 2.2)
    a.escada(119.5, 0, 2.2)
    for x, y, z, e in ((76, -0.8, 5, 1.2), (82, -0.6, 5.5, 1.4), (90, -1.0, 5, 1.3), (99, -0.4, 5.2, 1.5),
                       (106, -0.6, 5.0, 1.2), (114, -0.8, 5.5, 1.4), (124, -0.5, 5.2, 1.5), (130, 0.0, 4.5, 1.3)):
        a.peca("rocha_caverna", x, y, z, e=e)
    for x, y in ((82, 0.8), (88, -0.3), (93, -3.0), (101, 1.1), (108, 1.0), (126, 2.2)):
        a.peca("rocha_caverna", x, y - 1.6, 1.2, e=[1.4, 0.9, 0.6])
    for x in range(78, 130, 5):
        a.peca("estalactite", x + R.uniform(-1, 1), 7.5 + R.uniform(-0.5, 0.5), R.uniform(0.5, 4))
    for x in (85, 97, 104, 116, 128):
        a.peca("musgo", x, R.uniform(1.5, 4), 3.4)
        a.luz(x, 2.5, 1.5, MUSGO, 0.9, 11)
    for x in (10, 30, 50, 70):
        a.luz(x, 4, 1.0, [0.6, 0.75, 0.85], 0.55, 14)
    a.coletavel("duto_sucata_1", "sucata", 93.5, -3.0)
    a.coletavel("duto_vidro_1", "vidro", 45, 0)
    a.entrada("vila", 3)
    a.entrada("boca", 127, 2.2)
    a.saida(1.0, 0, "praca", "duto", "Subir para a Praça")
    a.saida(130.5, 2.2, "boca_do_poco", "duto", "Seguir para a Boca do Poço")
    a.d["marcos"].append(dict(id="duto", x=40, rotulo="Duto Norte"))
    return a


# ====================================================================== boca do poço

def boca_do_poco():
    a = Area("boca_do_poco", "Boca do Poço", "boca", "boca", "eclusa", 0, 42)
    a.solido(21, -0.5, 42, 1)
    a.solido(-0.5, 6, 1, 14)
    a.solido(42.5, 6, 1, 14)
    linha(a, "piso_eclusa", 0, 42, 6, z=-3, fundo=False)
    linha(a, "parede_eclusa", 0, 42, 6, z=6)
    for x in (5, 7, 9):
        a.peca("armario_epi", x, 0, 5.4)
    a.peca("banco", 7, 0, 3.6)
    a.peca("painel_controle", 13, 0, 5.4)
    for x in (19, 21.5, 24):
        a.peca("chuveiro", x, 0, 1.6)
    a.peca("placa_eclusa", 29, 4.3, 5.9)
    a.peca("porta_eclusa", 36, 0, 3.0)
    for x in (4, 16, 28, 38):
        a.peca("luz_alerta", x, 6.3, 3.0)
        a.luz(x, 5.8, 2.0, VERMELHA, 1.4, 14, piscar=x in (16, 38))
    a.luz(8, 3.2, 1.0, [0.9, 0.85, 0.75], 0.6, 8)
    a.interativo("armario", "armario", 7, rotulo="Armário de EPI")
    a.interativo("chuveiros", "descontaminacao", 21.5)
    a.entrada("duto", 2)
    a.entrada("superficie", 34)
    a.saida(0.6, 0, "duto_norte", "boca", "Voltar ao Duto Norte")
    a.saida(36, 0, "superficie_sucata", "boca", "Abrir a eclusa", tipo="eclusa")
    a.d["marcos"].append(dict(id="boca", x=20, rotulo="Boca do Poço"))
    return a


# ====================================================================== superfície

def superficie_comum(a: Area, x0, x1):
    linha(a, "chao_areia", x0, x1, 10, z=-2, fundo=False)
    for x in range(int(x0), int(x1), 55):
        a.peca("skyline", x + R.uniform(0, 30), -2, R.uniform(120, 190), e=R.uniform(1.6, 2.6), fundo=True)
    for x in range(int(x0), int(x1), 24):
        a.peca(R.choice(["predio_ruina_a", "predio_ruina_b", "predio_ruina_c"]), x + R.uniform(0, 14), -0.5,
               R.uniform(18, 50), r=R.choice([0, 180]), fundo=True)
    for x in range(int(x0), int(x1), 17):
        a.peca(R.choice(["rocha", "poste", "cerca", "duna"]), x + R.uniform(0, 10), 0, R.uniform(4, 14), fundo=True)
    a.d["zonas"].append(dict(x0=x0, x1=x1, tipo="poeira", intensidade=1.0))


def superficie_sucata():
    a = Area("superficie_sucata", "Superfície: sucata próxima", "superficie", "superficie", "superficie", 0, 140, superficie=True)
    a.solido(70, -0.5, 140, 1)
    a.solido(-0.5, 10, 1, 30)
    superficie_comum(a, 0, 140)
    a.peca("escotilha_superficie", 4, 0, 1.2)
    a.saida(4, 0, "boca_do_poco", "superficie", "Descer pela escotilha", tipo="eclusa")
    a.entrada("boca", 7)
    # obstáculos
    for x in (38, 96):
        a.peca("carro_soterrado", x, 0, -0.6)
        a.solido(x, 0.55, 4.0, 1.1)
    a.peca("predio_ruina_b", 66, 0, -0.5)
    a.plataforma(63, 69, 2.8, esp=0.25)
    a.solido(63.2, 1.4, 0.3, 2.8)
    a.escada(64, 0, 2.8)
    a.peca("duna", 80, -0.3, 1.5, e=0.7)
    a.peca("placa_estrada", 22, 0, 1.5)
    for x in (30, 52, 74, 88, 110, 124):
        a.peca("sucata_pilha", x, 0, 2.0)
    for i, x in enumerate((26, 33, 47, 57, 85, 92, 104, 117)):
        a.coletavel(f"sup_sucata_{i}", "sucata", x)
    a.coletavel("sup_vidro_0", "vidro", 66, 2.8)
    a.coletavel("sup_componente_0", "componente", 121)
    a.d["marcos"].append(dict(id="sucata", x=60, rotulo="Sucata próxima"))
    a.peca("antena", 300, -2, 165, e=1.6, fundo=True)
    return a


def superficie_marco():
    a = Area("superficie_marco", "Superfície: o Marco", "superficie", "superficie", "superficie", 140, 300, superficie=True)
    a.solido(220, -0.5, 160, 1)
    superficie_comum(a, 140, 300)
    # ruínas para escalar
    a.peca("predio_ruina_a", 172, 0, -0.4)
    a.plataforma(168, 176, 3.0)
    a.plataforma(168, 172, 6.0)
    a.solido(167.8, 3, 0.3, 6)
    a.escada(169, 0, 3.0)
    a.escada(170.5, 3.0, 6.0)
    a.plataforma(178, 182, 4.2, esp=0.3)  # salto entre lajes
    a.peca("entulho", 180, 3.9, 0.3)
    a.peca("carro_soterrado", 198, 0, -0.6)
    a.solido(198, 0.55, 4.0, 1.1)
    a.peca("carro_soterrado", 214, 0, -0.6, r=180)
    a.solido(214, 0.55, 4.0, 1.1)
    a.peca("duna", 228, -0.3, 1.2, e=0.8)
    a.peca("marco", 250, 0, 1.6)
    a.peca("ponto_amostra", 253, 0, 0.6)
    a.interativo("amostra_marco", "amostra", 253, rotulo="Colher amostra de terra")
    a.peca("predio_ruina_b", 270, 0, -0.4, r=180)
    a.plataforma(267, 273, 2.8)
    a.solido(272.8, 1.4, 0.3, 2.8)
    a.escada(268, 0, 2.8)
    for i, x in enumerate((152, 186, 206, 236, 262, 284)):
        a.coletavel(f"marco_coleta_{i}", ["componente", "vidro", "sucata"][i % 3], x)
    a.coletavel("marco_componente_alto", "componente", 170, 6.0)
    a.d["marcos"].append(dict(id="marco", x=250, rotulo="O Marco"))
    return a


def superficie_antena():
    a = Area("superficie_antena", "Superfície: a Antena", "superficie", "superficie", "superficie", 300, 470, superficie=True)
    a.solido(385, -0.5, 170, 1)
    a.solido(470.5, 10, 1, 30)
    superficie_comum(a, 300, 470)
    a.peca("predio_ruina_c", 330, 0, -0.4)
    a.plataforma(325, 335, 3.4)
    a.solido(324.8, 1.7, 0.3, 3.4)
    a.escada(326, 0, 3.4)
    a.solido(338, 1.6, 2, 3.2)  # muro caído: precisa subir pelo prédio ou contornar pulando
    a.peca("entulho", 338, 0, 0.2, e=[1.2, 3.2, 1])
    for x in (352, 372, 404, 418):
        a.peca("carro_soterrado", x, 0, -0.6, r=0 if x % 2 else 180)
        a.solido(x, 0.55, 4.0, 1.1)
    a.peca("duna", 388, -0.3, 1.4, e=0.8)
    a.peca("predio_ruina_a", 432, 0, -0.4)
    a.plataforma(428, 436, 3.0)
    a.solido(427.8, 1.5, 0.3, 3.0)
    a.escada(429, 0, 3.0)
    a.peca("antena", 452, 0, 4.0)
    a.peca("item_mascara", 447, 0, 0.6)
    a.interativo("achado_darci", "achado", 447, rotulo="Máscara e gravador de Darci")
    for i, x in enumerate((316, 346, 364, 396, 412, 440, 460)):
        a.coletavel(f"antena_coleta_{i}", ["vidro", "componente", "sucata"][i % 3], x)
    a.luz(452, 43, 6, VERMELHA, 2.0, 30, piscar=True)
    a.d["marcos"].append(dict(id="antena", x=452, rotulo="A Antena"))
    return a


def sala_teste_preservada():
    caminho = os.path.join(DESTINO, "sala_teste.json")
    return os.path.exists(caminho)


if __name__ == "__main__":
    for fabrica in (capela, praca, galerias, duto_norte, boca_do_poco, superficie_sucata, superficie_marco, superficie_antena):
        fabrica().salvar()
