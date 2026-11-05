# Mapa e regra de bloqueio por EPI

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 5. Mapa do MVP

Com a câmera livre, a sensação de mundo aberto vem de seis recursos de desenho de nível, aplicados em todas as áreas:

1. **Mirantes:** pontos altos de onde se vê boa parte da área e lugares ainda inacessíveis.
2. **Marcos visíveis:** a Antena, a Torre d'Água e o facho da Capela guiam a navegação sem minimapa.
3. **Lugares visíveis e inalcançáveis:** o Portão da Caravana, o poço profundo e o horizonte da superfície mostram que o mundo continua.
4. **Circuitos em vez de linha:** mais de um caminho entre áreas e atalhos que se abrem ao longo do jogo.
5. **Verticalidade:** passarelas, poços, escadas e desníveis.
6. **Compressão e alívio:** túneis apertados que desembocam em salões amplos, para a escala ficar evidente.

### 5.1 Subsolo

| Área | Dimensões aproximadas | Estrutura e elementos de profundidade |
| --- | --- | --- |
| Vila Cisterna | Caverna de 140 × 90 m, teto a 25 m, colunas a cada 12 m | Três níveis: o piso (Praça do Reservatório e mercado), as passarelas a 8–12 m (ligam a sede do Conselho à Capela) e as Galerias Secas abaixo do piso. Das passarelas se vê a vila inteira |
| Praça do Reservatório | Área central de 50 × 40 m | Mercado de lonas, bomba d'água, Muro dos Subidores. Ao sul, o **Portão da Caravana**: túnel enorme que leva às cidades profundas, fechado no MVP e aberto só quando a Caravana chega |
| Galerias Secas | Corredores de 3 a 4 m de largura | Rede de galerias de drenagem com um poço vertical de 20 m, onde os barracos sobem em andares ligados por escadas. No fundo, uma grade sobre o **poço profundo**, com luzes fracas muito abaixo |
| Capela da Vigília | Casa de máquinas elevada a 10 m | Acesso pelas passarelas. O facho de luz é visível de quase toda a vila |
| Duto Norte | Túnel de metrô de 300 m | Rota principal entre a vila e a Estação Aurora, com dois desvios: a **Caverna da Fenda** (ponte de corda sobre um abismo de 40 m, musgo luminoso, mirante) e a **Galeria dos Contrabandistas** (passagem estreita até a Escotilha Oeste, aberta na missão 3) |
| Estação Aurora | Salão de 60 × 20 m, a 25 m de profundidade | Estação de metrô abandonada, escadas rolantes paradas, ponto de descanso antes da subida |
| Boca do Poço | Poço de ventilação de 25 m | Eclusa e descontaminação no topo, escada e elevador de carga. A eclusa serve de transição de carregamento entre subsolo e superfície |

### 5.2 Superfície

Área jogável de cerca de 640 × 675 m (ampliada em 27% em 5/11/2026, junto com a corrida de 7 m/s, para manter a regra da seção 5.3). Coordenadas em metros, com a Boca do Poço na origem e o norte no eixo Z positivo.

| Ponto | Posição (x, z) | Função |
| --- | --- | --- |
| Boca do Poço | (0, 0) | Saída principal e retorno seguro |
| Ruínas próximas | Raio de 50 a 127 m ao norte da Boca | Sucata, carros soterrados, prédios com interior que servem de abrigo |
| Escotilha Oeste | (-178, 115) | Retorno alternativo, aberta pelo lado de dentro na missão 3 |
| Escotilha Leste | (191, 76) | Retorno alternativo, aberta na tarefa opcional |
| Leito seco do rio | Faixa leste-oeste entre z = 191 e z = 216 | Obstáculo natural com duas travessias |
| O Marco | (-51, 255) | Monumento em uma praça antiga, objetivo da missão 3 |
| Torre d'Água | (-229, 382) | Marco visual e tarefa opcional |
| Viaduto caído | De (153, 331) a (51, 382) | Rota elevada até a colina da Antena |
| A Antena | (38, 484), colina 25 m acima | Objetivo da missão 4 e mirante final |
| Limite jogável | x de -318 a 318, z de -102 a 573 | Parede de tempestade permanente: o dreno do EPI cresce rapidamente além dela |

Elementos de mundo aberto na superfície:

- **Horizonte:** impostores da cidade em ruínas até cerca de 2 km, montanhas ao fundo e névoa por distância. À noite, a luz piscando a nordeste.
- **Abrigos:** interiores de prédios reduzem o dreno do filtro em 50%, sem zerar. Planejar a rota entre abrigos faz parte do jogo.
- **Bússola no pulso do EPI:** indica a direção da Boca do Poço e das escotilhas abertas.
- **Tempestade de poeira:** além de acelerar o dreno, reduz a visibilidade e esconde os marcos, deixando a bússola como única referência.

### 5.3 Regra de bloqueio por EPI

Cada ponto deve ser alcançável apenas com o filtro exigido. Regra: a ida e volta correndo pela rota mais curta precisa ultrapassar o tempo de filtro do nível anterior e caber no tempo do nível exigido com pelo menos 30 s de folga.

| Destino | Distância em linha reta | Ida e volta correndo (7 m/s) | Filtro exigido | Filtro efetivo correndo (tempo ÷ 1,3) |
| --- | --- | --- | --- | --- |
| Ruínas próximas | 102 a 127 m | 29 a 36 s | Básico (90 s) | 69 s |
| O Marco | 260 m | 74 s | Nível 2 (150 s) | 115 s |
| A Antena | 485 m | 139 s | Nível 3 (240 s) | 185 s |

As distâncias reais seguem o navmesh e ficam maiores que a linha reta. Um teste automatizado calcula a rota mais curta até cada ponto, considerando as escotilhas abertas em cada momento da história. O teste falha se a regra for quebrada. Exemplo do que o teste deve capturar: com a Escotilha Oeste aberta, a ida ao Marco pela Boca e a volta pela escotilha somam cerca de 449 m (64 s), o que caberia no filtro básico. Por isso essa escotilha só abre depois da missão 3.
