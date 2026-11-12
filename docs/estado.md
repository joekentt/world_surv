# Estado atual

**Atualizado em:** 2026-11-12

**Fase atual:** revisão 2, fase 2 (cenário em blocos) **fechada**. Próxima: fase 3 (EPI e superfície), aguardando o usuário.

**Situação:** todas as tarefas da fase 2 estão no branch (último merge 18357fb). Suíte inteira: 32 testes passam (1,2 h). Screenshots em `tests/screenshots/fase-2/`.

**Feito na fase 2:**
- 8cb9bd2: áreas em 3D (caixa de limites, carregamento pela distância, caixas sobrepostas).
- 79ee07b: Vila Cisterna em três níveis (`?area=vila_cisterna`, `tools/areas/subsolo_vila.py`).
- 4b33485: Duto Norte, Caverna da Fenda e Galeria dos Contrabandistas (`tools/areas/subsolo_duto.py`).
- 645c0c4: Estação Aurora, Boca do Poço e eclusa entre mundos (`tools/areas/subsolo_estacao.py`).
- Superfície aberta (`tools/areas/superficie.py`, mundo `superficie_aberta`).
- 74810e3: navmesh em vários níveis (`src/npc/navegacaoNiveis.ts`), teste da seção 5.3 (`tests/fase2_bloqueio.spec.ts`) e percurso Galerias → Antena (`tests/fase2.spec.ts`).
- 18357fb: kits da revisão 2 (`tools/blender/kits/kits_r2.py`), horizonte (`src/world/horizonte.ts`), tempestade (`src/world/tempestade.ts`), zonas de câmera.
- 3b1e707, b05c03a, dd3f6d9: animações com IK e rolagem do pé; EPI e roupas da vila refeitos.

**Critérios da fase 2:** percurso Galerias → Antena sem travar (passa); teste de bloqueio (passa: ruínas 36,4 s, Marco 72,9 s, Antena 141,7 s); horizonte e marcos visíveis da Antena e das passarelas (screenshots `percurso_01` e `percurso_02`); 60 fps no hardware mínimo só pode ser medido na máquina do usuário.

**Modo de trabalho (pedido do usuário):** as tarefas são delegadas a subagentes; a sessão principal revisa a entrega (testes, screenshots, critérios da especificação) antes do commit. Para rodar dois em paralelo, um usa worktree e `PORTA_TESTE` diferente de 5173.

**Em andamento (12/11):** retorno do usuário: pelo menu o jogo abria as faixas da revisão 1 (mapa retangular, sem saída visível). Subagente troca o "Novo jogo" para a Vila Cisterna nova e põe letreiros de neon com a rota até a eclusa (`tests/fase2_rota.spec.ts`). Direção de arte mudou para cyberpunk pós-apocalíptico (seção 7 reescrita; arte final na fase 6).

**Próximo passo:** com o aval do usuário, fase 3 (EPI e superfície), dividida em tarefas em `docs/spec/08-fases.md`. O usuário pode medir os fps da superfície em `http://localhost:5173/?area=superficie_aberta`.

**Bloqueios e dúvidas para o usuário:**
- Aval para iniciar a fase 3 e medição dos fps da superfície na máquina dele.

**Pendências para a fase 6 (arte final):** barracos e pichações das Galerias; fachadas das ruínas em malha; porta da eclusa do lado da superfície; fresta luminosa do Portão da Caravana; marca de dedos nas botas; segunda camada de roupa pouco visível em alguns NPCs.

**Como testar o que existe hoje:**
- `npm run typecheck`
- `npm test -- tests/fase2.spec.ts --reporter=line > logs/testes.log 2>&1; tail -n 40 logs/testes.log`
- No navegador: `?area=vila_cisterna`, `?area=duto_tunel`, `?area=estacao_aurora`, `?area=superficie_aberta`, `?area=sala_teste`

**Problemas conhecidos ainda abertos:**
- O "Novo jogo" do menu ainda usa as faixas lineares da revisão 1 (com paredes invisíveis), porque NPCs e missões dependem delas; o mundo novo passa a ser o do menu quando as fases 4 e 5 refizerem NPCs e missões. Os testes das fases 3 a 7 ainda são da revisão 1.
- No checkout do Windows, `git status` mostra arquivos alterados só por fim de linha (CRLF). Não é trabalho pendente.
- Herdados da revisão 1: publicar no Cloudflare Pages exige conta e segredos; 60 fps só pode ser medido na máquina do usuário.
