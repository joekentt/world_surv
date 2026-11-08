# Estado atual

**Atualizado em:** 2026-11-05

**Fase atual:** revisão 2, fase 2 (cenário em blocos): tarefas 1, 2, 3 e 8 concluídas.

**Situação:** fase 1 fechada (controle aprovado com corrida a 7 m/s e correção da escada; suíte completa passa). Na fase 2, a base de áreas em 3D está pronta (8cb9bd2).

**Feito recentemente:**
- 8cb9bd2: áreas em 3D (fase 2, tarefa 1).
- d53442c: corrida a 7 m/s com passada mais longa; velocidades de referência medidas (`tools/blender/animacoes/medir_passada.py`); superfície ampliada em 27% em `docs/spec/05-mapa.md`.
- 84f9688: saída pelo topo da escada segue a frente da escada por até 0,6 s; plataformas da sala de teste com 8 m.
- d4e119d: paredes invisíveis nas faixas antigas e volta ao último chão firme ao cair do mapa.
- b304e41 e anteriores: câmera, controle em 3D livre, sala de teste e testes da seção 3.4.

**Tarefas da fase 2** (spec: `docs/spec/08-fases.md` e `docs/spec/05-mapa.md`):
1. Áreas em 3D: caixa de limites, carregamento pela distância, caixas sobrepostas. **Feita.**
2. Vila Cisterna em três níveis, em blocos. **Feita** (79ee07b): `?area=vila_cisterna`, gerador `tools/areas/subsolo_vila.py`, mundo "subsolo", teste `tests/fase2_vila.spec.ts` (~11 min).
3. Duto Norte com a Caverna da Fenda e a Galeria dos Contrabandistas. **Feita** (4b33485): `tools/areas/subsolo_duto.py`, áreas `duto_tunel`, `duto_fenda`, `duto_contrabandistas`; caixa reservada `estacao_aurora` em x 141–200, z 195–215, y −25; Boca do Poço prevista em (178, −25, 205) do subsolo (superfície = x − 178, z − 205). Teste `tests/fase2_duto.spec.ts` (~12 min).
4. Estação Aurora e Boca do Poço (poço de 25 m, eclusa como transição de carregamento).
5. Superfície de 640 × 675 m com os pontos da seção 5.2.
6. Kits por estética (incluindo o da estação), zonas de câmera, impostores do horizonte e névoa.
7. Navmesh em vários níveis e teste de bloqueio da seção 5.3; refazer `tests/fase2.spec.ts`.
8. Personagens e animações menos robóticos (pedido do usuário em 8/11/2026). Animações e transições **feitas** (merge 3b1e707: pernas por IK, rolagem do pé, curvas assimétricas, mistura suavizada; referências andar 1,91 e correr 6,61 m/s). EPI refeito e roupas da vila com folga, camadas e remendos (merges b05c03a e dd3f6d9). **Feita.** Pendências para a fase 6: marca leve de dedos na ponta das botas; segunda camada pouco visível em alguns NPCs.

**Modo de trabalho (pedido do usuário):** as tarefas são delegadas a subagentes; a sessão principal revisa a entrega (testes, screenshots, critérios da especificação) antes do commit. Para rodar dois em paralelo, um usa worktree e `PORTA_TESTE` diferente de 5173.

**Próximo passo:** tarefa 4 (Estação Aurora e Boca do Poço com a eclusa) e tarefa 5 (superfície), por subagentes. Ler a seção 5.1 em `docs/spec/05-mapa.md` e a seção 7 em `docs/spec/07-arte-personagens-vila.md`.

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
