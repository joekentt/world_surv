# Registro de decisões

Uma linha por decisão: data, decisão e motivo. Acrescente no fim; não apague linhas antigas. Quando uma decisão substituir outra, escreva "substitui a de AAAA-MM-DD". Decisões técnicas da revisão 1 estão nas seções "Decisões" de `docs/_arquivo/progresso_revisao1.md`.

| Data | Decisão | Motivo |
| --- | --- | --- |
| 2026-10-17 | Mundo em 3D com modelos gerados por código | Pixel art no nível de Symphony of the Night não é viável por código; geometria 3D é |
| 2026-10-17 | Personagens com corpo base MPFB2 e malha contínua | Evitar a aparência quadrada (estilo Roblox) do projeto anterior |
| 2026-10-18 | Navegador como plataforma principal | Definição do usuário |
| 2026-10-18 | Babylon.js em vez de Godot e Three.js | Godot exporta para a web só com WebGL 2; Babylon tem WebGPU com fallback e traz física, navegação e áudio integrados |
| 2026-10-18 | MVP sem combate (premissa, aguarda confirmação) | Reduzir escopo; a câmera deve permitir mira no futuro |
| 2026-10-31 | Blender usado como módulo Python (`bpy` 5.2.3 do PyPI) | Execução headless sem instalar o Blender completo |
| 2026-11-02 | Câmera livre em terceira pessoa com recentralização automática (substitui a câmera lateral de 2026-10-18) | Pedido do usuário; especificação em `docs/spec/03-camera-movimento.md` |
| 2026-11-02 | Mapa redesenhado como mundo aberto, superfície de cerca de 500 × 530 m | Consequência da nova câmera; especificação em `docs/spec/05-mapa.md` |
| 2026-11-02 | Subida de degrau própria, com o `maxStepHeight` do `PhysicsCharacterController` desligado | Na versão 9.33.1 a subida embutida só funciona acima de uns 8 m/s |
| 2026-11-02 | Campo de visão de 70° interpretado como horizontal | Na vertical, 70° deixaria a imagem muito aberta em telas 16:9 |
| 2026-11-02 | Atraso da recentralização conta do mais recente entre o último movimento do mouse e o início da caminhada | Sem isso a câmera girava no primeiro passo |
| 2026-11-05 | Especificação dividida em `docs/spec/`, estado em `docs/estado.md`, regras por pasta em `.claude/rules/` | Evitar estouro e perda de contexto no Claude Code |
| 2026-11-05 | Volta ao último chão firme ao cair 12 m abaixo do sólido mais baixo do mundo; paredes invisíveis provisórias nas faixas da revisão 1 | O usuário caiu num vazio sem fim; as faixas serão substituídas na fase 2 |
| 2026-11-05 | Ao sair pelo topo de escada ou corda, o movimento segue a frente da escada por até 0,6 s enquanto a tecla continuar pressionada | Com a câmera virada, o W pressionado levava o personagem de volta à beirada; é a única exceção ao movimento relativo à câmera |
| 2026-11-05 | Corrida de 7 m/s (substitui 5,5 m/s da especificação) e superfície ampliada em 27% (cerca de 640 × 675 m; Marco a 260 m, Antena a 485 m) | Pedido do usuário; ampliar as distâncias mantém os tempos de ida e volta da regra de bloqueio da seção 5.3 com os filtros de 90, 150 e 240 s |
| 2026-11-05 | Velocidades de referência das animações medidas no Blender (`tools/blender/animacoes/medir_passada.py`): andar 1,79 m/s, correr 6,28 m/s | Os valores anteriores (1,3 e 4,0) não batiam com a passada e o pé deslizava; a corrida ganhou passada mais longa para os 7 m/s |
