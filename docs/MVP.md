# Vila Cisterna: especificação do MVP

Jogo de sobrevivência em 3D, com câmera livre em terceira pessoa, para navegador. A humanidade vive no subsolo porque a superfície se tornou letal. O jogador é um subidor: alguém que sobe por pouco tempo, protegido por EPI, para coletar recursos. Este MVP cobre uma vila subterrânea, os túneis que levam até ela e uma área aberta da superfície.

Nomes de lugares e personagens são provisórios.

**Revisão 2 (2 de novembro de 2026):** a câmera lateral foi substituída por câmera livre em terceira pessoa, o mapa foi redesenhado para transmitir mundo aberto e o movimento do personagem ganhou especificação própria. Mudanças principais nas seções 0, 1, 2, 3 (nova), 5, 6 e 10; ajustes menores nas demais.

---

## 0. Instruções para o Claude Code

1. Trabalhe **uma fase por vez**, na ordem da seção 10. Não comece a fase seguinte sem cumprir o critério de avanço da fase atual.
2. Ao terminar cada fase, rode os testes do Playwright, salve os screenshots em `tests/screenshots/fase-N/` e registre em `docs/progresso.md` o que foi feito, o que falhou e as decisões tomadas.
3. Nenhum asset é modelado à mão. Todo modelo, rig, animação e textura sai de script em `tools/blender/` e é exportado em GLB.
4. Antes de usar a API de qualquer biblioteca (Babylon.js, Havok, controlador de personagem, plugin de navegação, MPFB2), consulte a documentação oficial da versão instalada. Não presuma nomes de funções ou parâmetros.
5. Itens da seção 12 (decisões pendentes) não devem ser decididos por conta própria. Siga as premissas listadas lá e avise quando uma delas bloquear o trabalho.
6. Faça commits pequenos, um por tarefa, com mensagem descritiva em português.
7. Textos do jogo (diálogos, missões, nomes) ficam em arquivos JSON em `content/`, nunca escritos direto no código.
8. Se uma validação da fase 0 falhar, use a alternativa indicada na tabela da seção 2 e registre o motivo em `docs/progresso.md`.
9. **Migração da revisão 2:** se já existe código com câmera lateral ou movimento travado em um plano, remova o travamento, substitua a câmera e refaça as fases 1 e 2 conforme esta revisão. Reaproveite o que continuar válido (entrada, física, animações, kits de cenário) e registre em `docs/progresso.md` o que foi descartado e por quê.
10. Todos os valores numéricos de câmera, movimento, EPI e economia ficam em um único arquivo de configuração (`src/config.ts`). Os valores deste documento são pontos de partida para ajuste.

---

## 1. Objetivo do MVP

Uma fatia jogável de 20 a 30 minutos, rodando no navegador. Antes de qualquer expansão, ela precisa provar seis pontos:

1. **O ciclo central é divertido:** pegar uma missão na vila, subir à superfície com tempo limitado pelo EPI, voltar antes que a proteção acabe, melhorar o equipamento e ir mais longe na subida seguinte.
2. **Controlar o personagem é agradável:** movimento leve e fluido, com câmera livre que acompanha o jogador sem atrapalhar.
3. **A vila parece viva:** NPCs com rotina própria, conversas de fundo e mudança visível entre os turnos de luz.
4. **Os personagens não têm aparência de Roblox:** malha contínua, proporção anatômica e rosto estilizado bem trabalhado.
5. **O mundo parece grande e aberto:** a vila e a superfície mostram lugares, caminhos e horizontes além do que o MVP permite alcançar. A história também deixa claro que existem outras cidades, facções e um passado.
6. **O jogo roda bem no navegador:** 60 fps em um notebook comum, com WebGPU e fallback para WebGL2.

---

## 2. Stack técnica

| Camada | Escolha | Observação |
| --- | --- | --- |
| Motor | Babylon.js com TypeScript e Vite | WebGPU com detecção de suporte e fallback para WebGL2 |
| Física | Havok (plugin oficial do Babylon) | Colisão do cenário, objetos soltos, raycasts da câmera |
| Controle do personagem | Controlador de personagem do Babylon com Havok (documentação: Physics > Character Controller) | Validar a API na versão instalada. Movimento livre em 3D, sem travamento de plano |
| Câmera | Câmera em terceira pessoa com órbita livre, implementada em `src/camera/` | Especificação completa na seção 3. Mouse capturado com Pointer Lock |
| Navegação de NPCs | Plugin de navegação Recast do Babylon | Navmesh com vários níveis (passarelas e escadas) |
| Cenário | Kits modulares gerados por script Python no Blender (headless), exportados em GLB | Um kit por estética: cisterna, gueto, capela, túnel, estação, eclusa, superfície |
| Personagens | Corpo base MPFB2; roupas e EPIs gerados por script | Validar a automação headless do MPFB2. Alternativa: corpo gerado com skin modifier + subdivision surface |
| Animações | Ciclos gerados por script no rig do MPFB2: parado, andar, correr, pular, aterrissar, agachar, giro rápido, escada, corda, interagir | Validar a qualidade. Alternativa: biblioteca de animações CC0 compatível com o rig |
| Áudio | Motor de áudio do Babylon; efeitos e vozes via ElevenLabs | Conferir se o plano da ElevenLabs permite uso comercial |
| Testes | Playwright abre o jogo, simula entradas, tira screenshots e mede fps | O Claude Code analisa as imagens e os registros e corrige antes de avançar |
| Otimização | Níveis de detalhe (LOD), thin instances, impostores no horizonte, névoa por distância, carregamento por área | O subsolo e a superfície são carregados separadamente |
| Compressão | Malhas com Draco ou meshopt, texturas em KTX2 | |
| Save | IndexedDB no navegador | Um slot no MVP |
| Publicação | Site estático no Cloudflare Pages | Repositório no GitHub |

### Estrutura de pastas sugerida

```
/
├─ CLAUDE.md                  resumo do projeto e regras da seção 0
├─ docs/
│  ├─ MVP.md                  este arquivo
│  ├─ progresso.md            registro por fase
│  └─ pos-mvp.md              ideias fora do escopo
├─ src/
│  ├─ config.ts               todos os valores ajustáveis
│  ├─ core/                   motor, cena, loop, carregamento de áreas
│  ├─ camera/                 órbita, recentralização, colisão, zonas de câmera
│  ├─ player/                 controlador, entrada, animação do jogador
│  ├─ epi/                    medidores, dreno, tempestade, abrigos, upgrades
│  ├─ world/                  áreas, transições, turnos de luz, escotilhas
│  ├─ npc/                    rotinas, navegação, conversas de fundo
│  ├─ quests/                 diálogo, missões, variáveis de estado
│  ├─ economy/                inventário, comércio, cotas de filtro
│  ├─ ui/                     HUD, bússola, inventário, diário, menu, opções
│  └─ save/                   IndexedDB
├─ content/
│  ├─ dialogos/               JSON por personagem
│  ├─ missoes/                JSON por missão
│  └─ npcs/                   JSON com rotina e aparência de cada NPC
├─ tools/blender/
│  ├─ kits/                   scripts dos módulos de cenário
│  ├─ personagens/            corpo, roupas, EPIs, variação de rosto
│  ├─ animacoes/              ciclos de animação
│  └─ render_check.py         render em 3 vistas para validação
├─ public/assets/             GLB, KTX2 e áudio gerados
└─ tests/                     Playwright: entradas simuladas, screenshots e fps
```

---

## 3. Câmera e controle

### 3.1 Comportamento da câmera

A câmera orbita livremente ao redor do personagem. O mouse (ou o analógico direito do gamepad) tem prioridade sobre qualquer ajuste automático.

1. **Mouse em movimento:** a câmera segue o mouse, com o personagem parado ou andando. Giro horizontal livre de 360°.
2. **Movimento relativo à câmera:** W leva o personagem para onde a câmera aponta; S, A e D levam para trás e para os lados em relação à câmera. O personagem gira suavemente até a direção do movimento.
3. **Personagem andando e mouse parado:** depois de `camera.atrasoRecentralizar` (0,8 s) sem entrada do mouse, a câmera gira gradualmente até ficar atrás das costas do personagem. O giro acelera conforme a velocidade do personagem e desacelera perto do alvo, sem tranco.
4. **Exceção, personagem andando em direção à câmera:** se o ângulo entre a frente da câmera e a direção do movimento passar de 135°, a câmera não gira de imediato, porque um giro de 180° desorienta. Ela recua acompanhando o personagem e só recentraliza se a direção se mantiver por mais de 1,5 s.
5. **Personagem parado e mouse parado:** a câmera permanece onde está.
6. **Inclinação vertical:** durante a recentralização, volta suavemente ao ângulo neutro (10° para baixo).
7. **Interrupção:** qualquer movimento do mouse cancela a recentralização na hora.

### 3.2 Enquadramento e colisão

- Ponto de foco na altura do ombro (1,55 m), centralizado. Deslocamento lateral configurável, para permitir câmera sobre o ombro no futuro.
- Distância padrão de 4,5 m; zoom pela roda do mouse entre 2,5 m e 7 m.
- Inclinação vertical limitada entre 30° para cima e 65° para baixo.
- **Colisão:** uma esfera é lançada do ponto de foco até a posição desejada da câmera. Se encontrar parede, teto ou chão, a câmera se aproxima imediatamente e volta à distância normal de forma gradual (0,3 s). A câmera nunca entra na geometria.
- NPCs e objetos pequenos não empurram a câmera; ficam translúcidos quando estão entre a câmera e o personagem.
- Com a câmera a menos de 1 m, o próprio personagem fica translúcido.
- **Zonas de câmera:** volumes no mapa ajustam distância e campo de visão. Valores iniciais: túneis estreitos 3 m; vila 4,5 m; superfície 5,5 m com campo de visão 5° maior. A transição entre zonas dura 0,5 s.
- Campo de visão de 70°, com acréscimo de 6° ao correr, suavizado.
- O ponto de foco segue o personagem com mola amortecida: sem atraso perceptível na horizontal e um atraso leve na vertical, para suavizar pulos e degraus.
- **Pointer Lock:** clicar no jogo captura o mouse; Esc libera o mouse e abre o menu.
- **Opções do jogador:** sensibilidade, inverter eixo Y, recentralização automática ligada ou desligada, atraso da recentralização.

### 3.3 Movimento leve e fluido

| Parâmetro | Valor inicial |
| --- | --- |
| Andar | 2,2 m/s |
| Correr (Shift ou analógico no máximo) | 5,5 m/s |
| Agachado | 1,3 m/s |
| Tempo até a velocidade máxima | 0,15 s |
| Tempo até parar | 0,12 s |
| Giro do personagem | até 720°/s, suavizado |
| Altura do pulo | 1,1 m, variável conforme o tempo em que o botão fica pressionado |
| Controle no ar | 60% do controle no chão |
| Tolerância para pular depois de sair da borda | 0,1 s |
| Pulo registrado antes de tocar o chão | 0,12 s |
| Degrau máximo vencido sem pulo | 0,35 m |
| Rampa máxima | 45° |
| Dreno extra do filtro ao correr | 1,3 vez o dreno normal |

Animação e resposta:

- Mistura de locomoção por velocidade (parado, andar, correr), com a velocidade de reprodução sincronizada à velocidade real para o pé não deslizar no chão.
- Transições com mistura de 0,15 s a 0,2 s.
- Inclinação leve do corpo nas curvas e animação de giro rápido em inversões acima de 150°.
- Aterrissagem leve ou pesada conforme a altura da queda.
- Escadas de mão e cordas: encaixe automático ao chegar perto e apertar interagir.
- A entrada é lida no início de cada frame. A física roda em passo fixo, com interpolação na renderização, para o movimento não tremer em telas de taxa variável.

### 3.4 Critérios verificáveis

Testes do Playwright simulam entradas e registram o ângulo horizontal da câmera e a direção do personagem a cada frame:

1. Personagem a 90° da câmera, W pressionado por 3 s, sem mouse: a diferença entre câmera e costas do personagem cai abaixo de 10° em até 2 s depois do atraso de 0,8 s.
2. Mouse girando enquanto o personagem anda: a câmera acompanha o mouse e não recentraliza durante o giro nem nos 0,8 s seguintes.
3. Personagem parado e sem mouse por 5 s: o ângulo da câmera não muda.
4. Personagem andando em direção à câmera por 1 s: a câmera não gira mais que 15°.
5. Em um túnel de 2,5 m de largura, câmera girada 360° em várias alturas: um raycast confirma que a câmera nunca fica dentro da geometria.
6. O movimento começa no frame seguinte ao da tecla pressionada.

Além dos testes, o usuário joga a sala de teste e aprova a sensação de controle.

---

## 4. Mundo e roteiro

A vila é pequena, mas tudo nela aponta para um mundo maior: um passado que ninguém viveu, cidades que o jogador ainda não visitou e um conflito pela única coisa que mantém todos vivos, os filtros de respiração.

### Premissa

Há quatro gerações, a atmosfera perdeu a proteção contra o sol. Radiação e tempestades de poeira cáustica tornaram a superfície letal em poucas horas. Os sobreviventes desceram para minas, linhas de metrô, cisternas e galerias de drenagem. Ninguém vivo viu o céu azul: ele existe em fotos desbotadas, em hinos e nas histórias dos mais velhos.

A superfície ainda guarda o que o subsolo não produz: metal, vidro, componentes eletrônicos e sementes em cofres antigos. Quem sobe para buscar isso é chamado de **subidor**.

### A Vila Cisterna

A vila ocupa um reservatório de água de uma cidade que não existe mais, a 40 metros de profundidade. É a vila mais rasa da região: a poeira vaza pelas frestas, o ar é pior e a economia depende dos subidores. A moeda é a **cota de filtro**, uma ficha que vale um filtro de respiração. Quem controla os filtros controla a vila.

Zonas da vila:

- **Praça do Reservatório:** centro da vila, com mercado, sede do Conselho, bomba d'água e o Muro dos Subidores.
- **Galerias Secas:** o gueto, onde vive quem perdeu a cota. Barracos empilhados, filtros recondicionados vendidos no improviso, pichações.
- **Capela da Vigília:** templo improvisado em uma antiga casa de máquinas, com vitrais feitos de garrafas e um facho de luz que imita o sol.

### Forças em jogo

- **Conselho da Cisterna:** governa e distribui as cotas. Sabe que o estoque de filtros dura poucos meses e esconde isso dos moradores.
- **Vigília do Sol:** grupo religioso que vê a Queima como castigo e acredita que o sol vai perdoar quem tiver fé. Prega o retorno à superfície e cresce nas Galerias Secas.
- **Caravana de Qarar:** comerciantes de Qarar, cidade profunda de estética do Oriente Médio e primeira cidade da expansão. São os únicos que fabricam filtros novos.
- **Moradores das Galerias:** vivem de contrabando e favores. Ajudam o jogador em troca de sucata e informação. Conhecem rotas que o Conselho não controla.

### Protagonista

Um subidor recém-formado, aprendiz de Darci, o subidor mais experiente da vila. Darci subiu há 12 dias e não voltou. O Conselho entrega ao protagonista o EPI antigo de Darci, remendado, porque a vila precisa de alguém que suba.

### Arco do MVP: "O último registro"

1. **O primeiro dia:** missão na vila que ensina movimento, câmera e interação. O jogador leva uma peça de ventilador às Galerias Secas, passa pelas passarelas e conhece as três zonas.
2. **A primeira subida:** coletar sucata nas ruínas próximas à Boca do Poço. O jogador aprende o medidor de EPI, a bússola e os abrigos e volta com pouco tempo de sobra.
3. **A escolha:** a Vigília pede uma amostra de terra do Marco para provar que o solo está "curando". O Conselho proíbe. Para chegar lá, o jogador precisa do filtro nível 2. Ajudar ou recusar altera falas, preços e o sermão da capela. Ao concluir, os moradores das Galerias revelam a Galeria dos Contrabandistas, que dá acesso à Escotilha Oeste.
4. **O registro de Darci:** com o filtro nível 3, o jogador alcança a Antena. Encontra a máscara e o gravador de Darci, sem sinal do corpo. A gravação revela que a Caravana reduz de propósito os filtros enviados às vilas rasas e que Darci viu luzes acesas à noite no horizonte, onde ninguém deveria estar vivo.
5. **O desfecho:** o jogador decide o destino da gravação: entregar ao Conselho, entregar à Vigília ou guardar. Cada escolha gera uma reação diferente da vila. O MVP termina no alto da Antena, com a luz piscando no horizonte.

Tarefas opcionais: reabrir a Escotilha Leste (abre um segundo ponto de retorno) e recuperar um cofre de sementes na Torre d'Água.

### Como a profundidade aparece sem exposição

A história chega pelo cenário e por falas curtas, nunca por textos longos:

- O Muro dos Subidores exibe as máscaras de quem não voltou. A de Darci aparece ou não, conforme o desfecho.
- Fotos do céu azul são vendidas no mercado como relíquias.
- Crianças brincam de "subida" com máscaras de papelão.
- A fila das cotas cresce ao longo do jogo, mostrando que o estoque está acabando.
- Placas do mundo antigo continuam nas paredes, como "Reservatório Municipal nº 3".
- O rádio da Caravana cita Qarar e outras cidades pelo nome, plantando a expansão.
- A vila tem gírias próprias, como "queimar o filtro" (gastar a proteção) e "ver o céu" (morrer na superfície).

---

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

Área jogável de cerca de 500 × 530 m. Coordenadas em metros, com a Boca do Poço na origem e o norte no eixo Z positivo.

| Ponto | Posição (x, z) | Função |
| --- | --- | --- |
| Boca do Poço | (0, 0) | Saída principal e retorno seguro |
| Ruínas próximas | Raio de 40 a 100 m ao norte da Boca | Sucata, carros soterrados, prédios com interior que servem de abrigo |
| Escotilha Oeste | (-140, 90) | Retorno alternativo, aberta pelo lado de dentro na missão 3 |
| Escotilha Leste | (150, 60) | Retorno alternativo, aberta na tarefa opcional |
| Leito seco do rio | Faixa leste-oeste entre z = 150 e z = 170 | Obstáculo natural com duas travessias |
| O Marco | (-40, 200) | Monumento em uma praça antiga, objetivo da missão 3 |
| Torre d'Água | (-180, 300) | Marco visual e tarefa opcional |
| Viaduto caído | De (120, 260) a (40, 300) | Rota elevada até a colina da Antena |
| A Antena | (30, 380), colina 25 m acima | Objetivo da missão 4 e mirante final |
| Limite jogável | x de -250 a 250, z de -80 a 450 | Parede de tempestade permanente: o dreno do EPI cresce rapidamente além dela |

Elementos de mundo aberto na superfície:

- **Horizonte:** impostores da cidade em ruínas até cerca de 2 km, montanhas ao fundo e névoa por distância. À noite, a luz piscando a nordeste.
- **Abrigos:** interiores de prédios reduzem o dreno do filtro em 50%, sem zerar. Planejar a rota entre abrigos faz parte do jogo.
- **Bússola no pulso do EPI:** indica a direção da Boca do Poço e das escotilhas abertas.
- **Tempestade de poeira:** além de acelerar o dreno, reduz a visibilidade e esconde os marcos, deixando a bússola como única referência.

### 5.3 Regra de bloqueio por EPI

Cada ponto deve ser alcançável apenas com o filtro exigido. Regra: a ida e volta correndo pela rota mais curta precisa ultrapassar o tempo de filtro do nível anterior e caber no tempo do nível exigido com pelo menos 30 s de folga.

| Destino | Distância em linha reta | Ida e volta correndo (5,5 m/s) | Filtro exigido | Filtro efetivo correndo (tempo ÷ 1,3) |
| --- | --- | --- | --- | --- |
| Ruínas próximas | 80 a 100 m | 29 a 36 s | Básico (90 s) | 69 s |
| O Marco | 204 m | 74 s | Nível 2 (150 s) | 115 s |
| A Antena | 381 m | 139 s | Nível 3 (240 s) | 185 s |

As distâncias reais seguem o navmesh e ficam maiores que a linha reta. Um teste automatizado calcula a rota mais curta até cada ponto, considerando as escotilhas abertas em cada momento da história. O teste falha se a regra for quebrada. Exemplo do que o teste deve capturar: com a Escotilha Oeste aberta, a ida ao Marco pela Boca e a volta pela escotilha somam cerca de 353 m (64 s), o que caberia no filtro básico. Por isso essa escotilha só abre depois da missão 3.

---

## 6. Sistemas de jogo

| Sistema | O que entra no MVP |
| --- | --- |
| Movimento e câmera | Câmera livre em terceira pessoa e movimento conforme a seção 3. Teclado com mouse e gamepad |
| EPI | Dois medidores: filtro (ar) e integridade da roupa. O filtro drena com o tempo na superfície, mais rápido ao correr e mais devagar em abrigos; a roupa perde integridade com poeira e quedas. Com um deles zerado, o personagem recebe dano contínuo |
| Morte | O jogador acorda na vila e perde o que coletou na subida |
| Tempestade de poeira | Evento roteirizado com sirene de aviso: acelera o dreno e reduz a visibilidade |
| Upgrades | Filtro nível 2, filtro nível 3, roupa reforçada e cilindro extra. Tempos iniciais de filtro: 90 s (básico), 150 s (nível 2) e 240 s (nível 3) |
| Escotilhas | Pontos de retorno alternativos, abertos pelo lado de dentro ao longo da história |
| Coleta e inventário | Sucata, componentes, vidro e amostras. Mochila com limite de peso |
| Economia | Cota de filtro como moeda: vender recursos, comprar upgrades e filtros de reposição |
| Diálogo e missões | Diálogo com escolhas e variáveis de estado. 4 missões principais e 2 tarefas opcionais |
| NPCs | 20 moradores com rotina por turno de luz, 6 deles com nome e diálogo |
| Turnos de luz | Ciclo de dia e noite artificial no subsolo: as lâmpadas da vila baixam no turno de descanso. Na superfície, a hora do dia acompanha o mesmo relógio |
| Interface | Medidores de EPI, bússola, inventário, diário de missões, menu e opções de câmera |
| Save | Automático ao entrar na vila |

---

## 7. Direção de arte

A iluminação separa os dois mundos: o subsolo é quente, próximo e cheio de pontos de luz; a superfície é branca, estourada e sem abrigo. Cada área tem uma luz e três ou quatro elementos que a identificam à primeira vista. Com a câmera livre, toda área precisa funcionar vista de qualquer ângulo, sem fundos falsos.

| Área | Luz e cor | Elementos de identidade |
| --- | --- | --- |
| Praça do Reservatório | Lâmpadas âmbar, concreto úmido | Colunas do reservatório, varais, bomba d'água, mercado de lonas, Portão da Caravana |
| Galerias Secas | Fluorescentes frias e falhando, tom verde-azulado | Barracos empilhados de chapa, fiação aparente, pichações, poço vertical |
| Capela da Vigília | Facho branco-dourado imitando o sol, vitrais coloridos | Bancos de madeira reaproveitada, altar com fotos do céu |
| Duto Norte e Caverna da Fenda | Quase escuro: lanterna do capacete e musgo luminoso | Trilhos de metrô, água escorrendo, ponte de corda sobre o abismo |
| Estação Aurora | Luz fria e esparsa, poeira suspensa | Escadas rolantes paradas, painéis de horário apagados, azulejos antigos |
| Boca do Poço | Luz vermelha de alerta, névoa de descontaminação | Porta de eclusa, chuveiros, armários de EPI |
| Superfície | Céu branco-amarelado, poeira no ar, sombras duras | Ruínas de prédios, carros soterrados, leito seco do rio, viaduto caído, a Antena |

Cada efeito visual que depende de WebGPU precisa de uma versão simplificada para WebGL2.

---

## 8. Personagens

- Corpos gerados no MPFB2, com proporção de referência de cerca de 7,5 cabeças de altura.
- Malha contínua, shading suave, membros afunilados, pescoço, ombros arredondados e mãos com pelo menos o formato de luva com polegar separado.
- Roupas em camadas, com remendos e desgaste, geradas por script sobre o corpo base.
- Rostos estilizados, com variação de idade, nariz, maxilar e olhos, para que nenhum NPC pareça cópia de outro.
- Na superfície, máscara e capacete cobrem o rosto. Na vila, capuzes, lenços e turbantes fazem parte do figurino.
- Como a câmera fica atrás do personagem a maior parte do tempo, costas, mochila e EPI recebem o mesmo nível de detalhe da frente.
- Todo personagem passa pelo `render_check.py` (frente, costas, lado e 3/4) antes de entrar no jogo.

**Critério de aceite:** nenhuma parte do corpo com aspecto de bloco ou de peças encaixadas. Se o render mostrar isso, corrija antes de exportar.

---

## 9. Vida da vila

- **Rotina por turno:** trabalho, fila das cotas, culto e descanso, cada NPC com seus horários e lugares definidos em `content/npcs/`.
- **Ações nos pontos de trabalho:** varrer, consertar, cozinhar, rezar, conversar em pares.
- **Movimento entre níveis:** NPCs usam passarelas e escadas, para a vila parecer ocupada também no alto.
- **Conversas de fundo:** falas curtas disparadas por proximidade, que comentam o estoque de filtros, a Vigília e o sumiço de Darci.
- **Reação ao jogador:** NPCs olham, cumprimentam e comentam o EPI sujo ou a volta de uma subida difícil.
- **Som em camadas:** gotejamento, ventiladores, mercado e o sermão distante, com volume e direção conforme a posição da câmera.
- **Partículas:** poeira caindo das frestas, vapor da bomba d'água, fumaça das cozinhas.

---

## 10. Fases de produção

### Fase 0: Validação técnica

Tarefas:
- Criar o projeto com Vite, TypeScript e Babylon.js.
- Implementar a detecção de WebGPU com fallback para WebGL2 e mostrar na tela qual renderizador está ativo.
- Inicializar o Havok e o controlador de personagem em uma cena de teste.
- Gerar no Blender headless um módulo de parede, exportar em GLB e carregar no Babylon.
- Gerar um corpo no MPFB2 em modo headless já com rig e exportar em GLB. Se não funcionar, usar skin modifier.
- Gerar por script um ciclo de caminhada e reproduzi-lo no Babylon.
- Criar o `render_check.py`.
- Criar o teste do Playwright que abre a página, tira screenshot e mede o fps médio por 10 segundos, nos dois renderizadores.

Entrega: motor com WebGPU e fallback, pipeline Blender → GLB e um personagem MPFB2 andando no navegador.

**Avança se:** o personagem não tem aspecto de bloco, roda a 60 fps e o screenshot automático funciona.

### Fase 1: Câmera e movimento em terceira pessoa

Tarefas: câmera conforme as seções 3.1 e 3.2; controlador de personagem com os parâmetros da seção 3.3; mistura de animações de locomoção; Pointer Lock; teclado com mouse e gamepad; menu de opções da câmera; sala de teste com corredor estreito de 2,5 m, área aberta, escadas, rampas, plataformas, escada de mão e corda; testes automatizados da seção 3.4.

**Avança se:** os seis testes da seção 3.4 passam e o usuário aprova a sensação de controle na sala de teste.

### Fase 2: Cenário em blocos

Tarefas: kits modulares gerados no Blender para cada estética; a vila em três níveis, o Duto Norte com os dois desvios, a Estação Aurora, a Boca do Poço e a superfície com os pontos da seção 5.2, todos com geometria simples; zonas de câmera; impostores do horizonte e névoa; carregamento separado de subsolo e superfície, com a eclusa como transição; navmesh e teste de bloqueio da seção 5.3.

**Avança se:** o personagem percorre das Galerias Secas até a Antena sem travar; a superfície roda a 60 fps no hardware mínimo; o teste de bloqueio passa; e do alto da Antena e das passarelas da vila o horizonte e os marcos ficam visíveis em screenshot.

### Fase 3: EPI e superfície

Tarefas: medidores de filtro e roupa; dreno na superfície, ao correr e em abrigos; bússola; tempestade de poeira com sirene e perda de visibilidade; dano contínuo e morte; coleta e inventário com limite de peso; escotilhas como pontos de retorno; eclusa da Boca do Poço com descontaminação.

**Avança se:** uma subida completa, com volta à vila, é tensa e compreensível sem tutorial escrito.

### Fase 4: Vila viva

Tarefas: 20 NPCs com aparência variada; rotinas por turno de luz; navegação entre níveis; ações nos pontos de trabalho; conversas de fundo por proximidade; reação ao jogador; otimização com instancing, níveis de detalhe e animação reduzida fora da tela.

**Avança se:** o jogo mantém 60 fps com todos os NPCs em cena no hardware mínimo definido, vistos das passarelas.

### Fase 5: Missões e economia

Tarefas: sistema de diálogo com escolhas e variáveis de estado; as 4 missões principais e 2 opcionais; comércio com cotas de filtro; upgrades de EPI; abertura das escotilhas conforme a história; save automático no IndexedDB; os três desfechos.

**Avança se:** o MVP é jogável do primeiro dia até o desfecho, nos três finais.

### Fase 6: Arte final e áudio

Tarefas: materiais finais; iluminação por área conforme a seção 7; personagens finais com roupas e EPIs; partículas; efeitos sonoros e vozes.

**Avança se:** cada área é reconhecida por um único screenshot, tirado de pelo menos dois ângulos de câmera.

### Fase 7: Polimento e publicação

Tarefas: balanceamento da câmera, do movimento, do EPI e da economia; compressão de malhas e texturas; testes nos navegadores-alvo; publicação no Cloudflare Pages.

**Avança se:** existe um link público jogável de 20 a 30 minutos, do início ao fim.

---

## 11. Riscos e mitigação

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| MPFB2 não funciona bem em modo headless | Atraso nos personagens | Corpo gerado por skin modifier ou corpo base CC0 |
| Animações geradas por script ficam rígidas | Personagens com movimento de robô | Biblioteca de animações CC0 compatível com o rig, validada na fase 0 |
| Câmera atravessa paredes ou se perde nos túneis | Jogo desconfortável no subsolo | Colisão por esfera, zonas de câmera, teste automatizado no corredor de 2,5 m |
| Movimento pesado ou personagem deslizando | Controle desagradável | Parâmetros no `config.ts`, velocidade da animação sincronizada à velocidade real, aprovação do usuário na fase 1 |
| Superfície aberta pesa no navegador | Queda de fps em notebooks | Carregamento separado do subsolo, LOD, impostores, névoa, thin instances, sombras limitadas |
| 20 NPCs pesam no navegador | Queda de fps na vila | Instancing, níveis de detalhe, animação reduzida fora da tela |
| Navegador sem WebGPU | Visual inferior | Fallback WebGL2 testado desde a fase 0, com versão simplificada de cada efeito |
| Download grande | Carregamento lento | Malhas comprimidas (Draco ou meshopt), texturas KTX2, áreas carregadas sob demanda |
| Escopo do mundo aberto crescendo | MVP sem fim | Superfície limitada à área da seção 5.2, conteúdo concentrado em três pontos e duas escotilhas; ideias novas vão para `docs/pos-mvp.md` |
| Limite de uso do plano Pro | Fases interrompidas no meio | Tarefas pequenas, com critério verificável e registro em `docs/progresso.md` |

---

## 12. Decisões pendentes e premissas em uso

Até a confirmação, siga a premissa indicada. Não altere nenhuma delas sem autorização.

| Decisão | Premissa em uso |
| --- | --- |
| Motor | Babylon.js |
| Combate | Nenhum combate no MVP. A câmera deve permitir mira e travamento de alvo no futuro, sem reescrita |
| Enquadramento | Câmera centralizada atrás do personagem; deslocamento sobre o ombro disponível só em configuração |
| Navegadores e hardware mínimos | Chrome e Firefox atuais em notebook com GPU integrada |
| Aparência do protagonista | Aparência fixa |
| Idioma | Português, com textos em JSON preparados para receber outros idiomas |
| Nomes definitivos | Usar os nomes provisórios deste documento |

---

## 13. Fora do MVP

Combate, outras cidades, abertura do Portão da Caravana, descida pelo poço profundo, fabricação de itens, criação de personagem, multiplayer e versão para celular.
