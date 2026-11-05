/**
 * Todos os valores ajustáveis do jogo (seção 0, regra 10): câmera, movimento, EPI, economia,
 * turnos e NPCs. Tempos em segundos, distâncias em metros, ângulos em graus, pesos em kg,
 * preços em cotas de filtro. Os valores da especificação são pontos de partida para ajuste.
 */
export const CFG = {
  "movimento": {
    "andar": 2.2,
    "correr": 5.5,
    "agachado": 1.3,
    "tempoAteMaxima": 0.15,
    "tempoAteParar": 0.12,
    "giroMaximoGrausPorSegundo": 720,
    "suavizacaoGiro": 14,
    "alturaPulo": 1.1,
    "alturaPuloMinima": 0.45,
    "gravidade": -22,
    "controleNoAr": 0.6,
    "tempoCoiote": 0.1,
    "bufferPulo": 0.12,
    "degrauMaximo": 0.35,
    "rampaMaximaGraus": 45,
    "velocidadeEscada": 2.0,
    "velocidadeCorda": 1.5,
    "raioEncaixeEscada": 1.0,
    "saidaTopoEscada": 0.75,
    "saidaTopoCorda": 0.9,
    "tempoSaidaEscada": 0.6,
    "alturaCapsula": 1.7,
    "alturaAgachado": 1.05,
    "raioCapsula": 0.3,
    "quedaPesada": 3.0,
    "velocidadeQuedaDano": 13,
    "danoRoupaPorQueda": 12,
    "velocidadeMaxQueda": 30,
    "margemForaDoMapa": 12,
    "profundidadeFaixaAntiga": 6,
    "inclinacaoCurvaGraus": 9,
    "giroRapidoGraus": 150,
    "passoFisica": 0.016666666666666666,
    "colarNoChao": 2.5,
    "maxPassosPorQuadro": 5,
    "velocidadeReferenciaAndar": 1.3,
    "velocidadeReferenciaCorrer": 4.0
  },
  "camera": {
    "alturaFoco": 1.55,
    "deslocamentoLateral": 0,
    "distancia": 4.5,
    "distanciaMinima": 2.5,
    "distanciaMaxima": 7,
    "passoZoom": 0.5,
    "inclinacaoNeutraGraus": 10,
    "inclinacaoMinGraus": -30,
    "inclinacaoMaxGraus": 65,
    "sensibilidade": 0.0025,
    "sensibilidadeGamepad": 2.6,
    "inverterY": false,
    "recentralizar": true,
    "atrasoRecentralizar": 0.8,
    "anguloCostasGraus": 135,
    "tempoCostas": 1.5,
    "velocidadeRecentralizarBase": 0.6,
    "velocidadeRecentralizarPorMetro": 0.45,
    "velocidadeInclinacao": 2.0,
    "raioColisao": 0.25,
    "tempoVoltarDistancia": 0.3,
    "distanciaTranslucidoPersonagem": 1.0,
    "fovGraus": 70,
    "acrescimoFovCorrida": 6,
    "suavizacaoFov": 6,
    "molaHorizontal": 40,
    "molaVertical": 9,
    "transicaoZona": 0.5,
    "zonas": {
      "tunel": {
        "distancia": 3,
        "fovExtra": 0
      },
      "vila": {
        "distancia": 4.5,
        "fovExtra": 0
      },
      "superficie": {
        "distancia": 5.5,
        "fovExtra": 5
      }
    }
  },
  "epi": {
    "filtroBasico": 90,
    "filtroNivel2": 150,
    "filtroNivel3": 240,
    "cilindroExtra": 45,
    "drenoFiltroPorSegundo": 1,
    "roupaMaxima": 100,
    "roupaReforcada": 160,
    "drenoRoupaPoeira": 0.35,
    "multiplicadorReforcada": 0.6,
    "saudeMaxima": 100,
    "danoSemProtecao": 9,
    "regeneracaoSaude": 4,
    "alertaFiltro": 0.3,
    "criticoFiltro": 0.12,
    "multiplicadorCorrida": 1.3,
    "multiplicadorAbrigo": 0.5
  },
  "tempestade": {
    "intervaloMin": 70,
    "intervaloMax": 120,
    "aviso": 9,
    "duracao": 26,
    "multiplicadorFiltro": 2.6,
    "multiplicadorRoupa": 3.5,
    "empurraoVento": 1.6,
    "primeiraNaoAntesDe": 40
  },
  "inventario": {
    "pesoMaximo": 20,
    "itens": {
      "sucata": {
        "peso": 2.0,
        "preco": 1
      },
      "componente": {
        "peso": 1.0,
        "preco": 3
      },
      "vidro": {
        "peso": 1.5,
        "preco": 2
      },
      "amostra_terra": {
        "peso": 0.5,
        "preco": 0
      },
      "peca_ventilador": {
        "peso": 3.0,
        "preco": 0
      },
      "filtro_reposicao": {
        "peso": 0.5,
        "preco": 0
      },
      "mascara_darci": {
        "peso": 1.0,
        "preco": 0
      },
      "gravador_darci": {
        "peso": 0.5,
        "preco": 0
      },
      "foto_ceu": {
        "peso": 0.1,
        "preco": 0
      }
    }
  },
  "economia": {
    "cotasIniciais": 4,
    "filtrosIniciais": 2,
    "precoFiltroReposicao": 3,
    "upgrades": {
      "filtro2": 14,
      "filtro3": 26,
      "roupa_reforcada": 12,
      "cilindro_extra": 10
    },
    "descontoAliado": 0.2,
    "acrescimoHostil": 0.25
  },
  "turnos": {
    "duracaoTurno": 150,
    "ordem": [
      "primeiro_turno",
      "segundo_turno",
      "vigilia",
      "descanso"
    ],
    "luzDescanso": 0.32
  },
  "npc": {
    "velocidadeAndar": 1.25,
    "raioConversaFundo": 6,
    "intervaloConversa": 9,
    "raioReacao": 3.2,
    "distanciaAnimacaoReduzida": 26,
    "distanciaLod": 16
  },
  "coleta": {
    "tempoColeta": 0.6,
    "raioInteracao": 1.4
  }
};

export type Config = typeof CFG;
