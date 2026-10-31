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
