---
name: fechar-tarefa
description: Fecha a tarefa atual do projeto Vila Cisterna, registra o estado e as decisões e faz o commit, deixando tudo pronto para /clear.
disable-model-invocation: true
---

# Fechar a tarefa

1. Rode `npm run typecheck` e os testes da fase em andamento, com saída em `logs/`. Se algo falhar, informe o usuário e não faça o commit.
2. Sobrescreva `docs/estado.md` mantendo o formato atual e no máximo 40 linhas: data, fase, situação, feito recentemente, próximo passo concreto, bloqueios, arquivos tocados, como testar e problemas abertos.
3. Acrescente no fim de `docs/progresso.md` uma entrada de até 5 linhas com o que foi feito e o resultado dos testes.
4. Para cada decisão nova, acrescente uma linha em `docs/decisoes.md` (data, decisão, motivo).
5. Se surgiu uma regra que deve valer sempre, proponha ao usuário onde colocá-la (`CLAUDE.md` ou um arquivo de `.claude/rules/`), sem editar por conta própria.
6. Faça o commit com mensagem em português, incluindo os arquivos de `docs/`.
7. Encerre dizendo: "Tarefa fechada. Rode /clear e depois /retomar."
