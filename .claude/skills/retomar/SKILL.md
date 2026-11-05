---
name: retomar
description: Retoma o trabalho do projeto Vila Cisterna no início de uma sessão ou depois de /clear, a partir de docs/estado.md.
disable-model-invocation: true
---

# Retomar o trabalho

1. `docs/estado.md` já está no contexto, importado pelo `CLAUDE.md`. Se estiver vazio ou desatualizado em relação ao `git log`, reconstrua-o a partir de `git log --oneline -10` e das últimas entradas de `docs/progresso.md` e grave.
2. Rode `git log --oneline -5` e `git status --short`. Ignore arquivos alterados só por fim de linha (confira com `git diff --ignore-cr-at-eol --stat`).
3. Leia só o arquivo de `docs/spec/` ligado à tarefa atual (índice em `docs/spec/README.md`).
4. Responda ao usuário em até 8 linhas: fase, tarefa, o que falta, próximo passo e bloqueios.
5. Se não houver bloqueio nem decisão pendente, siga para o próximo passo. Se houver, pergunte e aguarde.
