---
paths:
  - "src/npc/**"
  - "content/npcs/**"
---

# NPCs e vida da vila

Especificação completa: `docs/spec/07-arte-personagens-vila.md` (seção 9) e `docs/spec/06-sistemas.md`.

Regras:

- 20 moradores com rotina por turno de luz; 6 com nome e diálogo.
- Aparência e rotina de cada NPC ficam em `content/npcs/<id>.json`; o GLB é gerado a partir dele.
- NPCs usam passarelas e escadas; a navmesh tem vários níveis.
- Desempenho: instancing, níveis de detalhe e animação reduzida fora da tela. Meta de 60 fps com todos os NPCs visíveis das passarelas.
