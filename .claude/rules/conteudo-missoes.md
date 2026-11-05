---
paths:
  - "content/dialogos/**"
  - "content/missoes/**"
  - "content/textos/**"
  - "src/quests/**"
---

# Conteúdo, diálogos e missões

Especificação completa: `docs/spec/04-mundo-roteiro.md`. Leia antes de escrever falas ou alterar missões.

Regras:

- Textos do jogo ficam só em JSON em `content/`, preparados para receber outros idiomas.
- Nomes de lugares e personagens são provisórios; use os da especificação.
- Falas curtas. A história aparece pelo cenário e por diálogos breves, nunca por textos longos.
- Forças em jogo: Conselho da Cisterna (esconde a falta de filtros), Vigília do Sol (religiosa, prega a volta à superfície), Caravana de Qarar (fabrica os filtros), moradores das Galerias (contrabando e rotas secretas).
- Arco do MVP: "O último registro", com 4 missões principais, 2 opcionais e 3 desfechos.
- Variáveis de estado das escolhas ficam centralizadas no sistema de missões, nunca espalhadas pelos diálogos.
