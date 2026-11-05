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
