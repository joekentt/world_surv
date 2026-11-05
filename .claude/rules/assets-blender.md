---
paths:
  - "tools/blender/**"
  - "public/assets/**"
---

# Assets gerados no Blender

Especificação completa: `docs/spec/07-arte-personagens-vila.md` (arte e personagens) e `docs/spec/02-stack.md` (pipeline e alternativas).

Regras:

- Nada é modelado à mão: todo asset sai de script Python executado com o módulo `bpy` e é exportado em GLB.
- Saída sempre em arquivo: `npm run assets > logs/assets.log 2>&1`, lendo só o fim ou as linhas de erro.
- Os scripts são longos (`kits/gerar_kits.py` tem cerca de 900 linhas, `personagens/gerar_personagem.py` 850 e `animacoes/gerar_animacoes.py` 500): leia só a função que vai alterar.
- Personagens: corpo base MPFB2, malha contínua, proporção de cerca de 7,5 cabeças, sem aspecto de bloco ou de peças encaixadas.
- Todo personagem passa pelo `render_check.py` (frente, costas, lado e 3/4) antes de ser exportado. Costas, mochila e EPI têm o mesmo nível de detalhe da frente.
- Nunca leia arquivos GLB ou KTX2. Para conferir um asset, use os renders do `render_check.py`.
