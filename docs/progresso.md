# Registro de progresso

Histórico da revisão 2. O da revisão 1 está em `docs/_arquivo/progresso_revisao1.md`. Acrescente cada tarefa no fim, em até 5 linhas. Não leia este arquivo inteiro: use Grep ou as últimas entradas.

# Revisão 2 da especificação (2/11/2026): câmera livre em terceira pessoa

## Migração (seção 0, regra 9)

### Descartado e por quê

- `src/player/camera.ts` (câmera lateral 2,5D): substituída por `src/camera/cameraTerceiraPessoa.ts`.
- Travamento do jogador em z = 0 e o controle lateral de `src/player/jogador.ts`: o controle foi reescrito para movimento livre em 3D relativo à câmera.
- `content/balanceamento.json`: a regra 10 pede um único arquivo de configuração em `src/config.ts`. Os valores foram movidos para lá. Os tempos de filtro voltaram aos da especificação (90, 150 e 240 s; cilindro de 45 s): o ajuste anterior (75 s e 30 s) valia para o mapa lateral e será refeito com a regra de bloqueio da seção 5.3 na fase 2.
- A sala de teste lateral foi trocada por uma sala em 3D.

### Reaproveitado

Entrada (teclado e gamepad), física Havok, personagens, biblioteca de animações, kits de cenário, EPI, NPCs, missões, economia, save, áudio, pós-processamento e partículas. As áreas antigas da vila e da superfície continuam carregando, mas ainda são as faixas lineares da revisão 1: serão refeitas na fase 2 (vila em três níveis, Duto Norte com desvios, Estação Aurora, superfície de 500 × 530 m). Até lá, os testes `fase2` a `fase7` descrevem a revisão 1 e não foram rodados de novo.

### Fase 0, ajustes da revisão 2

- `render_check.py` passa a renderizar quatro vistas (frente, costas, lado e 3/4), como pede a seção 8, e descomprime GLB com meshopt antes de importar (o `bpy` do PyPI não traz esse decodificador).
- Animações novas da seção 2: `aterrissar_leve`, `aterrissar_pesado`, `giro_rapido` e `corda`. Ações de uma vez (aterrissar, giro, interagir, morrer) agora terminam na última pose em vez de voltar à primeira.
- A vista de costas mostrou fios finos ligando mão e queixo nas peças de roupa e EPI: eram faces com arestas de até 74 cm criadas na geração das peças. Uma limpeza remove faces com arestas acima de 10 cm (no corpo base a maior tem 5 cm). Os 21 personagens foram regenerados.

## Fase 1 (revisão 2): câmera e movimento em terceira pessoa

### Feito

- **Câmera** (`src/camera/cameraTerceiraPessoa.ts`), seções 3.1 e 3.2: órbita livre de 360° com mouse (Pointer Lock) e analógico direito; inclinação entre 30° para cima e 65° para baixo; zoom pela roda de 2,5 a 7 m; foco no ombro (1,55 m) com mola rígida na horizontal e macia na vertical; recentralização atrás das costas depois de 0,8 s sem mouse, com giro que acelera com a velocidade do personagem, desacelera perto do alvo e entra sem tranco; exceção para quem anda em direção à câmera (mais de 135°: só recua junto e espera 1,5 s); inclinação volta a 10° durante a recentralização; qualquer movimento do mouse cancela na hora. Colisão por esfera lançada do foco (`shapeCast` do Havok): aproxima na hora e volta em 0,3 s. Zonas de câmera (túnel 3 m, vila 4,5 m, superfície 5,5 m e +5° de campo de visão) com transição de 0,5 s. Campo de visão de 70° com +6° ao correr. NPCs entre a câmera e o personagem ficam translúcidos; o personagem também fica, com a câmera a menos de 1 m. Gancho `alvoTravado` para mira e travamento de alvo no futuro.
- **Opções** no menu de pausa: sensibilidade, inverter Y, recentralização ligada ou desligada e atraso. Ficam salvas no navegador. Clicar no jogo captura o mouse; Esc libera e abre o menu.
- **Controle** (`src/player/jogador.ts`), seção 3.3: movimento relativo à câmera; aceleração até a máxima em 0,15 s e parada em 0,12 s; giro de até 720°/s suavizado; pulo de 1,1 m variável; 60% de controle no ar; tolerância de borda de 0,1 s e buffer de pulo de 0,12 s; degrau de até 0,35 m sem pulo; rampa de até 45°; giro rápido em inversões acima de 150°; aterrissagem leve ou pesada (acima de 3 m); inclinação nas curvas; escadas de mão e cordas com encaixe ao apertar interagir (de baixo ou de cima); física em passo fixo de 1/60 s com interpolação do modelo.
- **Animação:** mistura de locomoção por velocidade (parado, andar e correr tocando juntos), com velocidade de reprodução proporcional à velocidade real.
- **Sala de teste** (`?area=sala_teste`): corredor de 2,5 m com teto, área aberta, escadaria até 2 m, rampas de 30°, 40° e 50°, degraus de 0,30 m e 0,40 m, plataformas de pulo, túnel de 1,2 m, escada de mão de 5 m, corda de 6 m e pilares para orbitar a câmera.

### Problemas encontrados e decisões

- **Subida de degrau do Babylon não funciona em velocidade de caminhada.** O `maxStepHeight` do `PhysicsCharacterController` (9.33.1) desconta a folga de contato (0,05 m) do avanço de cada passo e pousa a cápsula na quina do degrau, rejeitando a normal inclinada; na prática só sobe acima de uns 8 m/s com passo de 1/60 s. Foi desligado e substituído por uma subida própria: raios à frente procuram um topo plano até 0,35 m, com espaço livre para a cápsula, e o modelo é suavizado para não dar tranco.
- **O `setPosition` do controlador não recalcula os contatos.** Depois de reposicionar, os contatos antigos continuavam sustentando o personagem. Todo reposicionamento passa por um método que chama o recálculo interno do controlador, o mesmo que a subida de degrau embutida usa.
- **Pairar acima do chão.** O controlador detecta apoio até ~0,1 m da superfície e mantém uma folga. No chão, o movimento passa a seguir o plano da superfície com uma pequena força contra a normal (sem frear em rampas), e o modelo é posicionado pela altura real do chão medida por raycast.
- **Atraso da recentralização:** conta a partir do mais recente entre o último movimento do mouse e o início da caminhada. Sem isso, com o mouse parado havia muito tempo, a câmera girava no primeiro passo.
- **Campo de visão de 70°:** interpretado como horizontal (`FOVMODE_HORIZONTAL_FIXED`), que é como jogos costumam expor essa opção. Na vertical, 70° deixaria a imagem muito aberta numa tela 16:9.
- **Critério 1 da seção 3.4:** com movimento relativo à câmera, apertar W faz o personagem virar para onde a câmera aponta, e a diferença cai abaixo de 10° em 0,2 s sem a câmera girar. Para testar a recentralização de fato, o teste também roda com o personagem andando numa direção fixa a 90° da câmera.

### Testes (`tests/fase1.spec.ts`)

| Critério da seção 3.4 | Resultado |
| --- | --- |
| 1. Câmera chega às costas (menos de 10°) | W relativo à câmera: 0,2 s; direção fixa a 90°: 1,62 s (limite 2,8 s) |
| 2. Mouse girando: sem recentralizar no giro nem nos 0,8 s seguintes | ok (giro de 75°) |
| 3. Parado e sem mouse por 5 s | variação de 0° |
| 4. Andando em direção à câmera por 1 s | giro de 0° (limite 15°) |
| 5. Túnel de 2,5 m, 360° em quatro inclinações | 48 posições, nenhuma dentro da geometria nem atrás de parede |
| 6. Movimento no quadro seguinte à tecla | 1,83 m/s já no primeiro quadro |

| Movimento (seção 3.3) | Medido |
| --- | --- |
| Andar / correr | 2,2 / 5,5 m/s |
| Tempo até parar (inclui um quadro de latência a poucos fps) | 0,15 s |
| Altura do pulo | 1,16 m |
| Degrau de 0,30 m / 0,40 m | sobe / barra |
| Rampa de 30° e 40° / 50° | sobe até 2 m / barra |
| Escadaria, escada de mão (5 m), corda (6 m) | ok |
| Túnel de 1,2 m: em pé / agachado | barra / passa |

### Critério de avanço

Os seis testes da seção 3.4 passam. **Falta a aprovação do usuário da sensação de controle na sala de teste**: a fase 2 só começa depois dela.

### 2026-11-05: queda sem fim nas áreas antigas

- O usuário caiu num vazio sem fim ao jogar pelo menu. Causa: as áreas da revisão 1 são faixas de 6 m de profundidade sem paredes laterais e não havia proteção contra queda para fora do mapa.
- Correção: paredes invisíveis nas laterais das áreas sem `z` (camada de colisão que a câmera ignora) e volta ao último chão firme quando o personagem passa 12 m abaixo do sólido mais baixo do mundo (`CFG.movimento.margemForaDoMapa`).
- Teste novo em `tests/fase1.spec.ts`: borda em z = 2,66, câmera a 4,43 m fora da faixa, volta do vazio para (−40, 0, 0). Fase 0, fase 1 e interface: 11 testes passam.

### 2026-11-05: queda ao sair pelo topo da escada

- Retorno do usuário: ao chegar ao topo da escada de mão, o personagem caía. Reproduzido com a câmera de frente para a escada: ao sair com W pressionado, o movimento passava a seguir a câmera e levava o personagem de volta à beirada (y final 0).
- Correção: saída 0,75 m para dentro do bloco (`saidaTopoEscada`) e, enquanto o movimento continuar pressionado por até 0,6 s depois da saída (`tempoSaidaEscada`), o personagem segue para a frente da escada. Plataformas da escada e da corda na sala de teste passaram de 4 para 8 m de profundidade.
- Teste da escada em `tests/fase1.spec.ts` agora sobe com a câmera virada para a escada e mantém W depois da saída: y = 5, z = 17,63. Sem a correção, o mesmo teste falha. Fase 1: 8 testes passam.

### 2026-11-05: corrida de 7 m/s

- Retorno do usuário: a corrida estava lenta. Como 5,5 m/s também calcula a regra de bloqueio da seção 5.3, o usuário escolheu 7 m/s com a superfície ampliada em 27% (`docs/spec/05-mapa.md` atualizado: Marco a 260 m, Antena a 485 m, limite x ±318, z −102 a 573).
- Novo `tools/blender/animacoes/medir_passada.py`: mede a velocidade em que o pé de apoio não desliza. Os valores antigos (1,3 e 4,0) estavam errados; medidos: andar 1,79 m/s, correr 6,28 m/s depois de alongar a passada da corrida. A 7 m/s a reprodução fica em 1,11×.
- `animacoes.glb` regenerado (duas passadas de meshopt, como o arquivo anterior: 501 KB). Fase 0 e fase 1: 10 testes passam; corrida medida a 7,0 m/s.

### 2026-11-05: fase 1 fechada; fase 2, tarefa 1 (áreas em 3D)

- Fase 1 fechada: o usuário aprovou o controle com os ajustes de corrida e escada. Suíte completa: 20 testes passam (os 10 que falharam na primeira rodada foram `ERR_CONNECTION_REFUSED`, servidor de desenvolvimento derrubado ao interromper a rodada anterior; repetidos, passaram).
- Tarefa 1 da fase 2: `AreaDef.limites` (caixa 3D), `caixaDaArea`, `distanciaArea`; `GerenciadorAreas.areaEm`, `atualizar` e `entrarMundo` recebem ponto 3D; com caixas sobrepostas vale a de menor volume (níveis empilhados, como vila e Galerias). Faixas da revisão 1 continuam funcionando pela caixa derivada de inicio e fim.
- Gerador: `Area.caixa(min, max)`; área aninhada `sala_teste_corredor` para o teste "áreas em 3D".

### 2026-11-08: fase 2, tarefas 2 e 8 (parcial), feitas por subagentes

- Vila em três níveis (79ee07b): caverna x −70..70, z −45..45, teto 25 m; praça 50 × 40; passarelas a 8, 10 e 12 m; Capela a 10 m; Galerias a −5 m com poço até −25 m e grade sobre o poço profundo. Blocos visíveis unidos por material; blocos só visuais (`semColisao`); luzes escolhidas pelo z do jogador. Teste `fase2_vila`: 2 passam (Capela a 10,0 m; poço de 20 m e volta à praça). Revisão: aprovada para blocos.
- Animações (merge 3b1e707): IK nas pernas, rolagem do pé, parado com respiração e troca de apoio, contra-rotação do tronco, atraso de antebraço e mão, voo na corrida; pesos de locomoção por velocidade suavizada. Fase 0 e fase 1: 11 passam. Traje EPI devolvido para refazer.
