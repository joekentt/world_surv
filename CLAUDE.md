# Vila Cisterna

Jogo de sobrevivência em 3D com câmera livre em terceira pessoa, para navegador (Babylon.js + TypeScript + Vite + Havok). A humanidade vive no subsolo; o jogador é um subidor que sobe à superfície por pouco tempo, protegido por EPI. A especificação vigente é a revisão 2 (2/11/2026).

## Memória do projeto

A conversa é apagada a cada `/clear` e resumida a cada compactação. O que precisa sobreviver fica nestes arquivos:

| Arquivo | Conteúdo | Como usar |
| --- | --- | --- |
| `docs/estado.md` | Fase, tarefa atual, próximo passo, bloqueios | Importado no fim deste arquivo. Sobrescreva ao fechar cada tarefa |
| `docs/spec/` | Especificação do MVP dividida por tema | Leia só o arquivo da tarefa atual (índice em `docs/spec/README.md`) |
| `docs/decisoes.md` | Decisões tomadas e o motivo | Procure com Grep antes de decidir algo que pareça já discutido |
| `docs/progresso.md` | Histórico da revisão 2 | Nunca leia inteiro: use Grep ou as últimas entradas |
| `docs/_arquivo/` | Especificação completa e histórico da revisão 1 | Só com Grep, quando precisar de um detalhe antigo |
| `.claude/rules/` | Regras de cada pasta do código | Carregam sozinhas quando você lê ou edita arquivos daquela pasta |

## Ciclo de trabalho

1. Início da sessão ou depois de `/clear`: o usuário roda `/retomar`.
2. Uma tarefa por sessão. Uma tarefa é um item da fase atual em `docs/spec/08-fases.md`, pequeno o bastante para terminar com folga. Se for grande, divida e registre as partes em `docs/estado.md`.
3. Fim da tarefa: o usuário roda `/fechar-tarefa` e depois `/clear`.
4. Checkpoint: depois de cada avanço importante numa tarefa longa, atualize `docs/estado.md` antes de continuar. Assim uma compactação inesperada não perde o progresso.

## Higiene de contexto

Saídas longas e imagens são o que mais enche a janela de contexto.

- Comando com saída longa grava em `logs/` (pasta ignorada pelo git; crie com `mkdir -p logs` num clone novo) e você lê só o fim ou os erros. Exemplos: `npm run assets > logs/assets.log 2>&1; tail -n 30 logs/assets.log` e `npm test -- tests/fase1.spec.ts --reporter=line > logs/testes.log 2>&1; tail -n 40 logs/testes.log`.
- Rode só os testes da fase ou do arquivo alterado. A suíte inteira, só ao fechar uma fase.
- Screenshots: abra só os necessários para o critério da tarefa, no máximo 4 por rodada. Para revisar mais, use um subagente que devolva só o veredito e os problemas.
- Não leia arquivos grandes inteiros: use Grep e leitura por trecho. Nunca leia GLB, KTX2 ou outros binários. Os scripts maiores são `tools/blender/kits/gerar_kits.py` (cerca de 900 linhas), `tools/blender/personagens/gerar_personagem.py` (850), `tools/blender/animacoes/gerar_animacoes.py` e `tools/areas/gerar_areas.py` (500 cada): leia só a função que vai alterar.
- Use `git diff --ignore-cr-at-eol` e `git status` com moderação: o checkout no Windows marca arquivos como alterados só pelo fim de linha (CRLF).
- Buscas amplas pelo código: use um subagente de exploração e traga só a conclusão.

## Regras permanentes

1. Uma fase por vez, na ordem de `docs/spec/08-fases.md`. Só avance quando o critério da fase atual for cumprido.
2. Ao fim de cada fase: rodar o Playwright, salvar screenshots em `tests/screenshots/fase-N/` e registrar em `docs/progresso.md`.
3. Nenhum asset é modelado à mão: modelos, rigs, animações e texturas saem de scripts em `tools/blender/`, exportados em GLB.
4. Antes de usar a API de uma biblioteca, conferir a documentação ou os `.d.ts` da versão instalada.
5. Decisões pendentes (seção 12, em `docs/spec/01-objetivo-escopo-premissas.md`) não são tomadas por conta própria: seguir as premissas listadas.
6. Todos os valores de câmera, movimento, EPI e economia ficam em `src/config.ts`.
7. Textos do jogo ficam em JSON em `content/`, nunca no código.
8. Commits pequenos, um por tarefa, com mensagem em português.
9. Se uma validação falhar, usar a alternativa de `docs/spec/02-stack.md` e registrar o motivo em `docs/decisoes.md`.
10. Ideias fora do escopo vão para `docs/pos-mvp.md`, sem implementar.

## Comandos

```bash
npm install
npm run dev                 # http://localhost:5173 (?cena=teste, ?area=sala_teste, ?render=webgl2, ?qualidade=baixa)
npm run typecheck
npm test                    # Playwright (Chromium headless com SwiftShader)
npm run assets              # regenera todos os GLB (precisa do bpy, ver abaixo)
```

Assets: `python3 -m venv /opt/bpyenv && /opt/bpyenv/bin/pip install bpy==5.2.3`, depois
`bash tools/blender/personagens/baixar_dados_mpfb2.sh` (dados CC0 da malha base) e `npm run assets`.

## Convenções

- Eixos no jogo: Y para cima; na superfície, a Boca do Poço fica na origem e o norte é +Z. Movimento livre em 3D.
- Valores ajustáveis: `src/config.ts` (arquivo único).
- Personagens: `content/npcs/<id>.json` define aparência e rotina; o GLB é gerado a partir dele.

## Ao compactar

Preserve no resumo: fase e tarefa atuais, arquivos alterados nesta sessão, erros ainda não resolvidos, comandos de teste usados e decisões que ainda não foram registradas em `docs/decisoes.md`.

## Estado atual

@docs/estado.md
