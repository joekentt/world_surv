# Direção de arte, personagens e vida da vila

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

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

## 8. Personagens

- Corpos gerados no MPFB2, com proporção de referência de cerca de 7,5 cabeças de altura.
- Malha contínua, shading suave, membros afunilados, pescoço, ombros arredondados e mãos com pelo menos o formato de luva com polegar separado.
- Roupas em camadas, com remendos e desgaste, geradas por script sobre o corpo base.
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
