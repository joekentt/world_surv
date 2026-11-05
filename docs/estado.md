# Estado atual

**Atualizado em:** 2026-11-05

**Fase atual:** revisão 2, fase 1 concluída; próxima é a fase 2 (cenário em blocos).

**Situação:** o usuário aprovou a sensação de controle condicionada a dois ajustes, ambos feitos e testados: corrida mais rápida (7 m/s) e queda ao sair pelo topo da escada. Com isso a fase 2 está liberada.

**Feito recentemente:**
- d53442c: corrida a 7 m/s com passada mais longa; velocidades de referência medidas (`tools/blender/animacoes/medir_passada.py`); superfície ampliada em 27% em `docs/spec/05-mapa.md`.
- 84f9688: saída pelo topo da escada segue a frente da escada por até 0,6 s; plataformas da sala de teste com 8 m.
- d4e119d: paredes invisíveis nas faixas antigas e volta ao último chão firme ao cair do mapa.
- b304e41 e anteriores: câmera, controle em 3D livre, sala de teste e testes da seção 3.4.

**Próximo passo:** fase 2 da revisão 2. Ler `docs/spec/08-fases.md` (fase 2) e `docs/spec/05-mapa.md`, dividir em tarefas e registrar aqui. Sugestão de ordem: (1) kit da estação e revisão dos kits por estética; (2) vila em três níveis; (3) Duto Norte, Caverna da Fenda e Galeria dos Contrabandistas; (4) Estação Aurora e Boca do Poço com a eclusa; (5) superfície de 640 × 675 m com os pontos da seção 5.2; (6) zonas de câmera, horizonte e névoa; (7) navmesh e teste de bloqueio da seção 5.3.

**Bloqueios e dúvidas para o usuário:**
- Nenhum.

**Arquivos principais tocados recentemente:**
- `src/player/jogador.ts`, `src/config.ts`, `src/world/construtor.ts`, `src/world/areas.ts`
- `tools/blender/animacoes/gerar_animacoes.py`, `tools/blender/animacoes/medir_passada.py`
- `tools/areas/gerar_areas.py` (função `sala_teste`), `tests/fase1.spec.ts`

**Como testar o que existe hoje:**
- `npm run typecheck`
- `npm test -- tests/fase1.spec.ts --reporter=line > logs/testes.log 2>&1; tail -n 40 logs/testes.log`
- No navegador: `http://localhost:5173/?area=sala_teste`

**Problemas conhecidos ainda abertos:**
- O jogo pelo menu ainda usa as faixas lineares da revisão 1 (com paredes invisíveis provisórias); serão substituídas na fase 2. Os testes das fases 2 a 7 também são da revisão 1 e serão refeitos com as fases.
- No checkout do Windows, `git status` mostra arquivos alterados só por fim de linha (CRLF). Não é trabalho pendente.
- Herdados da revisão 1: publicar no Cloudflare Pages exige conta e segredos; 60 fps só pode ser medido na máquina do usuário.
