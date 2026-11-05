# Câmera e movimento

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

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
| Correr (Shift ou analógico no máximo) | 7 m/s (era 5,5; alterado a pedido do usuário em 5/11/2026) |
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
