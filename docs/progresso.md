# Registro de progresso

## Fase 0: validação técnica

### Feito

- Projeto Vite 8 + TypeScript 5.9 + Babylon.js 9.33.1 + Havok 1.3.14 (`@babylonjs/havok`).
- Detecção de renderizador em `src/core/motor.ts`: tenta WebGPU e cai para WebGL2; o renderizador ativo aparece no selo do canto inferior direito. `?render=webgl2` força o fallback. Se o dispositivo WebGPU cair e não voltar em 3 s, a página recarrega em WebGL2.
- Havok inicializado em `src/core/fisica.ts`; a cena de teste (`?cena=teste`) derruba caixas com física.
- Blender headless: usado o módulo `bpy` 5.2.3 do PyPI (Blender como módulo Python). Script `tools/blender/kits/parede_teste.py` gera um módulo de parede e exporta GLB, carregado no Babylon.
- Personagem com rig exportado em GLB por `tools/blender/personagens/gerar_personagem.py`, a partir de `content/npcs/<id>.json`.
- Biblioteca de 18 animações geradas por script (`tools/blender/animacoes/gerar_animacoes.py`), reproduzidas no Babylon com adaptação ao esqueleto de cada corpo (`src/core/carregador.ts`).
- `tools/blender/render_check.py` renderiza frente, lado e 3/4 (Cycles CPU), com opção de pose.
- Teste Playwright `tests/fase0.spec.ts`: abre a cena, tira screenshot e mede o fps médio por 10 s em WebGPU e WebGL2.

### Decisões e desvios

- **MPFB2 em modo headless:** a execução do código do MPFB2 foi bloqueada pela política de segurança do ambiente (código externo). Em vez de cair direto para o skin modifier, o gerador usa apenas os **dados** do MPFB2, que são CC0 (malha base HM08, targets de modelagem, rig `game_engine` e pesos), baixados de um commit fixo por `baixar_dados_mpfb2.sh`. A mistura de targets macro (gênero, idade, peso, músculo, altura, proporções, etnia) foi reimplementada seguindo a mesma regra de interpolação do MakeHuman. Resultado: corpo contínuo com anatomia real, sem aspecto de bloco. Para usar o MPFB2 original, é preciso autorizar a execução do código dele no ambiente.
- **Roupas:** geradas como cascas deslocadas a partir das faces do corpo, por região anatômica (osso dominante + marcos do corpo). Herdam os pesos do rig, então deformam junto. Faces do corpo cobertas são removidas. Remendos, costuras e sujeira ficam em cores de vértice.
- **Rosto estilizado:** cabeça 25% mais alta e olhos 15% maiores que o padrão do MakeHuman, mais seis variações sorteadas por semente (nariz, queixo, formato da cabeça, boca, maçãs do rosto), somadas às definidas no JSON. Sobrancelhas, lábios e olheiras são pintados em cores de vértice. Proporção resultante: 7,6 a 7,9 cabeças de altura.
- **Animações:** geradas por script com rotações em eixos fixos do personagem e cinemática direta acumulada. A alternativa (biblioteca CC0) não foi necessária. Ressalva: o movimento é procedural e precisa de revisão por quem joga; se ficar rígido, a alternativa da tabela da seção 2 continua válida.
- **Compressão:** o `bpy` do PyPI não inclui Draco nem meshoptimizer. A compressão fica para a fase 7 com `gltf-transform` (JavaScript).
- **WebGPU no teste headless:** o Chromium sem GPU só manteve o dispositivo WebGPU vivo com `--use-vulkan=swiftshader --disable-vulkan-surface`. `WebGPUEngine.IsSupportedAsync` não é usado porque, nesse adaptador de software, pedir um segundo adaptador invalida o primeiro.

### Medições

| Renderizador | fps médio (10 s) | Observação |
| --- | --- | --- |
| WebGPU (SwiftShader) | 1,9 | CPU do container, sem GPU |
| WebGL2 (SwiftShader) | 2,7 | CPU do container, sem GPU |

Os números acima medem renderização por software e só servem para comparar versões entre si. **O critério de 60 fps em notebook comum não pode ser verificado neste ambiente**: precisa ser medido em máquina com GPU (Chrome e Firefox, GPU integrada). O teste `npm test` faz essa medição quando rodado localmente.

### Critério de avanço

- Personagem sem aspecto de bloco: atendido (ver `tests/screenshots/fase-0/render_*.png` e `poses/`).
- Screenshot automático: atendido nos dois renderizadores.
- 60 fps: pendente de medição em hardware real (premissa: avançar e medir na máquina do usuário).

## Fase 1: movimento e câmera

### Feito

- `src/core/entrada.ts`: teclado (A/D ou setas, W/S, Espaço, Shift, Ctrl/C, E, I/Tab, J, Esc) e gamepad no mapeamento standard (analógico e direcional, A pula, B agacha, X interage, Y inventário, RB/RT corre, Start menu, Back diário), lidos uma vez por quadro com detecção de borda.
- `src/player/jogador.ts`: controle 2,5D sobre o `PhysicsCharacterController` do Havok, com Z travado. Aceleração e frenagem separadas no chão e no ar, tempo de coiote (0,1 s), buffer de pulo (0,12 s), pulo variável (soltar o botão corta a subida), agachar trocando a cápsula (com checagem de teto), escadas e cordas (de costas para a câmera, pulo solta), degraus de até 0,32 m e callbacks de queda forte e passos (usados pelo EPI e pelo áudio).
- `src/player/camera.ts`: câmera lateral em perspectiva, suavização exponencial, antecipação na direção do olhar, limites por mundo e tremor.
- `src/world/areas.ts` e `construtor.ts`: áreas em JSON (`content/areas/`), colisão por caixas estáticas do Havok e carregamento sob demanda entre áreas do mesmo mundo; transição com escurecimento entre mundos.
- Sala de teste (`?area=sala_teste`) com degraus, plataformas, escada, corda, túnel baixo e vão.
- Todos os valores de movimento estão em `content/balanceamento.json`.

### Testes (`tests/fase1.spec.ts`)

| Medição | Resultado |
| --- | --- |
| Velocidade andando | 3,2 m/s |
| Velocidade correndo | 6,2 m/s |
| Altura do pulo (botão segurado) | 1,83 m |
| Escada até 4 m e corda até 5,6 m | ok |
| Túnel de 1,2 m: em pé bloqueia, agachado passa | ok |
| Gamepad simulado (analógico + botão A) | ok |

### Decisões

- O passo da simulação é limitado a 1/20 s: em fps muito baixo o jogo desacelera em vez de atravessar paredes.
- Combate segue fora do MVP; o controle usa estados (chão, ar, escada, travado, morto), então ações novas entram como estados extras sem mexer na câmera nem na física.
- A precisão "sentida" do pulo e da corrida só se avalia jogando com GPU real; os testes automáticos garantem resposta e valores.

## Fase 2: cenário em blocos

### Feito

- `tools/blender/kits/gerar_kits.py`: sete kits gerados por script, um GLB por estética (cisterna, gueto, capela, túnel, eclusa, superfície) mais um kit comum de objetos e itens coletáveis. São 70 módulos com bisel, ruído de forma, sujeira e oclusão em cor de vértice, placas com texto real ("Reservatório Municipal nº 3", "Conselho da Cisterna", "Os que subiram", "Estação Norte", "Qarar 340", pichações).
- `tools/areas/gerar_areas.py`: layouts das oito áreas em `content/areas/` (Capela, Praça e Galerias formam o mundo da vila; Duto Norte; Boca do Poço; superfície dividida em Sucata próxima, Marco e Antena). Cada layout tem colisão, peças de frente e de fundo, escadas, luzes, saídas, entradas, coletáveis e pontos de interação.
- Carregamento sob demanda: áreas do mesmo mundo entram quando o jogador chega a 45 m da borda e saem a 70 m. Mundos diferentes se ligam por saídas com escurecimento.
- Camadas de fundo em 3D real (paredes, colunas, prédios a 18–50 m, silhueta de cidade a 120–190 m e a Antena no horizonte), que dão paralaxe pela própria perspectiva.
- Perfis de luz por estética (`src/world/iluminacao.ts`) com transição suave e seleção das luzes pontuais mais próximas (6 em WebGPU, 4 em WebGL2); luzes fluorescentes e de alerta piscam. Lanterna do capacete liga no Duto Norte.
- Sistema de interação com aviso na tela (`src/world/interacao.ts`) e HUD em HTML.

### Teste (`tests/fase2.spec.ts`)

Percurso Galerias → Praça → Capela → escotilha → Duto Norte (túnel e caverna) → Boca do Poço → eclusa → Sucata → ruínas → Marco → Antena, conferindo a carga e a descarga de áreas. Passou, com screenshots em `tests/screenshots/fase-2/`.

### Decisões

- O kit é instanciado (`createInstance`) a partir de malhas-fonte em que a conversão de eixos do glTF foi assada nos vértices; assim o layout usa diretamente x lateral, y para cima e z profundidade.
- Capela, Praça e Galerias são áreas separadas (cada uma com seu kit e layout), mas contíguas: o jogador anda entre elas sem tela de carga, e a mais distante é descarregada.
- A iluminação ainda é de bloqueio; a direção de arte final é da fase 6.

## Fase 3: EPI e superfície

### Feito

- `src/epi/epi.ts`: filtro (segundos de ar) e integridade da roupa. Na superfície, o filtro drena 1 s/s e a roupa perde integridade com a poeira; quedas fortes rasgam a roupa. Com qualquer um zerado, a saúde cai 9 por segundo; saúde zerada é a morte. Alertas sonoros de filtro baixo cada vez mais frequentes, respiração do filtro que acelera, mochila pesada (acima de 75%) deixa o subidor mais lento.
- Tempestade de poeira: sirene, aviso de 9 s, 26 s de tempestade com dreno ×2,6 no filtro e ×3,5 na roupa, poeira fechando a visão (névoa e cor), vento empurrando o jogador e tremor de câmera. Intervalo sorteado entre 70 e 120 s, nunca antes de 40 s na superfície.
- `src/epi/subida.ts`: a eclusa da Boca do Poço consome um filtro de reposição, instala filtro novo e repara a roupa; sem filtro, não abre. Na volta, descontaminação com chuveiro. Ao morrer: animação, tela "Você viu o céu.", o jogador acorda na Praça e perde o que coletou na subida.
- `src/world/coletaveis.ts`: sucata, componentes e vidro com peso; na superfície os recursos voltam a cada subida, fora dela somem para sempre. Limite de 20 kg na mochila.
- `src/ui/medidores.ts`: contador circular de ar com número grande, barra da roupa, saúde que só aparece quando há dano, vinheta vermelha, ícone de tempestade, mochila (kg) e cotas.
- `tools/audio/gerar_sons.py`: 27 sons gerados por síntese (sirene, passos em concreto, areia e metal, vento, tempestade, goteira, ventiladores, zumbido de fluorescente, multidão, sermão, respiração do filtro, eclusa, chuveiro, rádio e outros), tocados pelo AudioEngineV2 do Babylon com volume por distância.
- Estado central serializável (`src/core/estado.ts`), base do save da fase 5.

### Teste (`tests/fase3.spec.ts`)

Subida pela eclusa, dreno de filtro e roupa, coleta, mochila cheia, aviso e tempestade (dreno medido: 2,63 s de filtro por segundo), filtro zerado até a morte, perda dos itens e despertar na vila, nova subida, volta com descontaminação e eclusa travada sem filtro. Passou.

### Decisões

- Cada subida consome um filtro de reposição (comprado com cotas); isso amarra a economia ao ciclo central.
- Itens de missão (máscara, gravador, amostra) não se perdem na morte, para não travar o roteiro.
- Vozes ficam pendentes: a seção 2 pede conferir se o plano da ElevenLabs permite uso comercial antes de gerar.
- "Tensa e compreensível sem tutorial" depende de teste com pessoas; o HUD foi desenhado para isso (número de segundos, cores, pulsação, sirene), e as falas de Ondina na eclusa (fase 5) explicam o EPI dentro da história.

## Fase 4: vila viva

### Feito

- 20 moradores gerados a partir de `content/npcs/` (6 nomeados: Mirela, Teodoro, Samira, Bento, Nita e Ondina), cada um com corpo, rosto, roupa e cobertura de cabeça próprios, mais LOD a 30% dos triângulos no mesmo GLB.
- `src/world/turnos.ts`: ciclo de quatro turnos (primeiro turno, segundo turno, vigília e descanso), 150 s cada; no descanso as lâmpadas e a luz ambiente baixam.
- `src/npc/navegacao.ts`: malha de navegação do plugin Recast do `@babylonjs/addons` 9.33.1, gerada dos dados das áreas (piso e pegadas de barracas, bancos, colunas, casas e barracos). O addon baixa o Recast de um CDN por padrão; aqui a biblioteca (`@recast-navigation/core` e `generators` 0.43.0, versão que o addon espera) é injetada pelo npm.
- `src/npc/npcs.ts`: cada NPC segue a rotina do turno (trabalho, fila das cotas, culto, descanso), anda pelo caminho calculado, executa a ação do posto (varrer, consertar, cozinhar, rezar, conversar, sentar, brincar) virado para o lado certo, entra em casa no descanso e reage ao jogador com aceno e fala (que muda depois de uma subida difícil ou de uma morte). Conversas de fundo por proximidade entre dois NPCs parados, com balões; falas em `content/dialogos/conversas_fundo.json`, algumas condicionadas a escolhas do jogador.
- A fila das cotas ganha figurantes conforme as missões são concluídas e as subidas se acumulam.
- Otimização: a simulação roda para todos, mas o modelo 3D só é criado a até 48 m do jogador; animação pausada a mais de 26 m; LOD por distância; cenário instanciado (`createInstance`).

### Teste (`tests/fase4.spec.ts`)

20 NPCs simulados e carregados, troca de turno com mais de cinco NPCs andando, descanso com luz baixa e conversa de fundo exibida. Passou.

### Medições

| Cena | fps (WebGL2, SwiftShader, sem GPU) |
| --- | --- |
| Praça com 13 moradores visíveis e 20 carregados | 2,2 |

O critério de 60 fps com todos os NPCs no hardware mínimo (notebook com GPU integrada) **não pode ser medido aqui**. Pontos de atenção para essa medição: cada morador tem 11 a 13 mil triângulos no LOD0 e é uma malha com esqueleto próprio; se faltar desempenho, reduzir a decimação do LOD0, baixar a distância do LOD e limitar o número de NPCs animados ao mesmo tempo.

## Fase 5: missões e economia

### Feito

- `src/quests/dialogo.ts` e `src/ui/dialogoUI.ts`: diálogos em árvore (JSON em `content/dialogos/`), com entrada escolhida por condição, falas digitadas, opções por teclado, gamepad ou mouse, e efeitos (missão, flag, item, cotas, loja, desfecho, save). Câmera aproxima durante a conversa.
- `src/quests/condicoes.ts` e `efeitos.ts`: a mesma linguagem de condições e efeitos serve a diálogos, gatilhos de missão, conversas de fundo e sermões.
- `src/quests/missoes.ts`: missões em `content/missoes/` com etapas para o diário, avisos na tela e gatilhos por evento (voltar da superfície, vender sucata, colher a amostra).
- Roteiro "O último registro": M1 O primeiro dia (Mirela → Nita → Teodoro → Mirela, apresenta as três zonas), M2 A primeira subida (Ondina explica o EPI dentro da história, cinco sucatas, venda ao Bento), M3 A escolha (amostra do Marco para a Vigília ou para o Conselho, ou recusar o pedido), M4 O registro de Darci (Antena, máscara e gravação). Tarefas opcionais: T1 Vidro para os vitrais (Teodoro) e T2 Peças para Nita.
- Escolha da M3 altera falas (conversas de fundo condicionadas), preços (Bento e Nita ficam 25% mais caros ou 20% mais baratos conforme o lado) e o sermão da Capela (três variantes, em balões durante a vigília).
- Economia: Bento compra sucata, componente e vidro e vende filtro de reposição; Nita vende filtro recondicionado; a Caravana (Samira) vende filtro nível 2 e 3, roupa reforçada e cilindro extra.
- Três desfechos: entregar ao Conselho (máscara vai para o Muro, cota dobrada, gravação escondida), entregar à Vigília (gravação tocada na Capela, vila dividida) ou guardar (no Muro dos Subidores; ninguém sabe). Cada um tem reação própria e epílogo na superfície, à noite, com a luz piscando no horizonte e a tela de fim.
- Profundidade de mundo sem exposição: rádio da Caravana cita Sétimo Poço, Nova Halab e Poço Seco; fotos do céu à venda; placa "Qarar 340" na superfície; gírias ("queimar o filtro", "ver o céu"); Muro dos Subidores com texto que muda conforme o desfecho.
- Interface: diário (J), inventário (I), menu de pausa (Esc) com volume e controles, lojas, tela de título com novo jogo e continuar.
- `src/save/save.ts`: um slot no IndexedDB; save automático ao entrar na vila, ao fechar a M1 e no desfecho.

### Teste (`tests/fase5.spec.ts`)

Campanha conduzida pelos diálogos e gatilhos reais: introdução, M1 completa, T1 e T2, M2 (aula de Ondina, volta com sucata, venda ao Bento pela loja), M3 com aviso de Mirela, compra do filtro nível 2, amostra do Marco e entrega à Vigília (preço do filtro: Bento 4 cotas, Nita 2), M4 com filtro nível 3, achado na Antena e gravação, save no IndexedDB conferido, e os três desfechos a partir do mesmo ponto (Vigília, Conselho e guardar), cada um terminando na superfície com a tela de fim. Passou em 2,3 min.

### Decisões

- A recusa ao pedido da Vigília também conclui a M3 (conta como lado do Conselho), para que a escolha exista mesmo sem subir ao Marco.
- O destino "guardar" fica no Muro dos Subidores: é o lugar onde a ausência da máscara de Darci tem significado.
- A subida em si não é repetida neste teste (coberta pela fase 3); o gatilho de volta é disparado direto.
