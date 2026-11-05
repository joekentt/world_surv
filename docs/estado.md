# Estado atual

**Atualizado em:** 2026-11-05

**Fase atual:** revisão 2, fase 1 (câmera e movimento em terceira pessoa).

**Situação:** os seis testes da seção 3.4 passam (commit b304e41). Falta a aprovação do usuário da sensação de controle na sala de teste. A fase 2 só começa depois dela.

**Feito recentemente:**
- Correção da queda sem fim nas áreas antigas: paredes laterais invisíveis (a câmera ignora) e volta ao último chão firme.
- b304e41: controle em 3D livre, sala de teste e testes da seção 3.4.
- fca8998: câmera com órbita livre, recentralização, colisão por esfera, zonas e opções.
- 41df0a7: animações de aterrissar, giro rápido e corda; `render_check` com vista de costas.
- 2052e39: valores ajustáveis migrados para `src/config.ts`.
- Memória do projeto reorganizada: `docs/spec/`, `docs/estado.md`, `docs/decisoes.md`, `.claude/rules/`, `/retomar`, `/fechar-tarefa` e hook pós-compactação (commit 247537b, caminhos conferidos depois).

**Próximo passo:** receber o retorno do usuário sobre a sala de teste (`npm run dev`, depois `http://localhost:5173/?area=sala_teste`) e ajustar os valores em `src/config.ts`. Com a aprovação, iniciar a fase 2 da revisão 2 (`docs/spec/08-fases.md` e `docs/spec/05-mapa.md`).

**Bloqueios e dúvidas para o usuário:**
- Aprovação da sensação de controle na sala de teste (não no jogo pelo menu, que ainda usa as faixas estreitas da revisão 1 até a fase 2).

**Arquivos principais tocados recentemente:**
- `src/camera/cameraTerceiraPessoa.ts`, `src/camera/opcoes.ts`
- `src/player/jogador.ts`, `src/config.ts`
- `tests/fase1.spec.ts`, `content/areas/sala_teste.json`

**Como testar o que existe hoje:**
- `npm run typecheck`
- `npm test -- tests/fase1.spec.ts --reporter=line > logs/testes.log 2>&1; tail -n 40 logs/testes.log`

**Problemas conhecidos ainda abertos:**
- `git status` mostra cerca de 21 arquivos alterados, mas a diferença é só de fim de linha (CRLF). Não é trabalho pendente.
- Herdados da revisão 1: publicar no Cloudflare Pages exige conta e segredos; 60 fps só pode ser medido na máquina do usuário.
