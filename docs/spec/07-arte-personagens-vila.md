# Direção de arte, personagens e vida da vila

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 7. Direção de arte

**Estética: cyberpunk pós-apocalíptico** (pedido do usuário em 12/11/2026). O mundo antigo era uma metrópole de alta tecnologia: letreiros de neon, painéis holográficos, telas por toda parte, implantes e drones. O colapso apagou quase tudo. No subsolo, os sobreviventes religaram o que acharam: neon remendado, telas de tubo e LED falhando, cabos pendurados em feixes, letreiros de corporações extintas reaproveitados como parede ou teto. A tecnologia é velha, consertada e escassa, nunca limpa ou nova.

A iluminação separa os dois mundos: o subsolo é escuro, úmido e recortado por pontos de neon saturado (magenta, ciano, âmbar e verde ácido) refletidos no chão molhado; a superfície é branca, estourada e sem abrigo, com os esqueletos da metrópole e os letreiros mortos. Cada área tem uma luz e três ou quatro elementos que a identificam à primeira vista. Com a câmera livre, toda área precisa funcionar vista de qualquer ângulo, sem fundos falsos.

Os letreiros de neon também orientam: setas e nomes de destino ("DUTO NORTE", "ESTAÇÃO AURORA", "SUPERFÍCIE") marcam a rota da vila até a Boca do Poço, sem minimapa e sem texto de tutorial.

| Área | Luz e cor | Elementos de identidade |
| --- | --- | --- |
| Praça do Reservatório | Neon âmbar e magenta sobre concreto úmido, reflexos no chão | Colunas do reservatório cobertas de letreiros, mercado de lonas com telas de LED, varais com cabos, bomba d'água, Portão da Caravana com painel de alerta |
| Galerias Secas | Fluorescentes frias falhando e neon verde ácido | Barracos empilhados de chapa e painéis publicitários, feixes de fiação, pichações em tinta fluorescente, poço vertical |
| Capela da Vigília | Facho branco-dourado imitando o sol, vitrais de telas quebradas | Bancos reaproveitados, altar com fotos do céu exibidas em telas velhas |
| Duto Norte e Caverna da Fenda | Quase escuro: lanterna do capacete, musgo luminoso e sinais ciano de manutenção do metrô | Trilhos, água escorrendo, cabos de alta tensão, ponte de corda sobre o abismo |
| Estação Aurora | Luz fria e esparsa, painéis holográficos falhando, poeira suspensa | Escadas rolantes paradas, painéis de horário com caracteres corrompidos, azulejos antigos |
| Boca do Poço | Luz vermelha de alerta, névoa de descontaminação, faixas de LED | Porta de eclusa, chuveiros, armários de EPI com leitores de cota |
| Superfície | Céu branco-amarelado, poeira no ar, sombras duras | Esqueletos de arranha-céus, letreiros e outdoors mortos, carros soterrados, leito seco do rio, viaduto caído, a Antena |

Cada efeito visual que depende de WebGPU precisa de uma versão simplificada para WebGL2.

## 8. Personagens

- Corpos gerados no MPFB2, com proporção de referência de cerca de 7,5 cabeças de altura.
- Malha contínua, shading suave, membros afunilados, pescoço, ombros arredondados e mãos com pelo menos o formato de luva com polegar separado.
- Roupas em camadas, com remendos e desgaste, geradas por script sobre o corpo base. Na estética cyberpunk pós-apocalíptica entram faixas refletivas, pequenos LEDs remendados, óculos de proteção e próteses ou implantes simples em parte dos NPCs.
- EPI do subidor: traje remendado com faixas de LED, visor com reflexo e cartuchos de filtro; a tecnologia parece consertada, nunca nova.
- Rostos estilizados, com variação de idade, nariz, maxilar e olhos, para que nenhum NPC pareça cópia de outro.
- Na superfície, máscara e capacete cobrem o rosto. Na vila, capuzes, lenços e turbantes fazem parte do figurino.
- Como a câmera fica atrás do personagem a maior parte do tempo, costas, mochila e EPI recebem o mesmo nível de detalhe da frente.
- Todo personagem passa pelo `render_check.py` (frente, costas, lado e 3/4) antes de entrar no jogo.

**Critério de aceite:** nenhuma parte do corpo com aspecto de bloco ou de peças encaixadas. Se o render mostrar isso, corrija antes de exportar.

## 9. Vida da vila

- **Rotina por turno:** trabalho, fila das cotas, culto e descanso, cada NPC com seus horários e lugares definidos em `content/npcs/`.
- **Ações nos pontos de trabalho:** varrer, consertar, cozinhar, rezar, conversar em pares.
- **Movimento entre níveis:** NPCs usam passarelas e escadas, para a vila parecer ocupada também no alto.
- **Conversas de fundo:** falas curtas disparadas por proximidade, que comentam o estoque de filtros, a Vigília e o sumiço de Darci.
- **Reação ao jogador:** NPCs olham, cumprimentam e comentam o EPI sujo ou a volta de uma subida difícil.
- **Som em camadas:** gotejamento, ventiladores, mercado e o sermão distante, com volume e direção conforme a posição da câmera.
- **Partículas:** poeira caindo das frestas, vapor da bomba d'água, fumaça das cozinhas.
