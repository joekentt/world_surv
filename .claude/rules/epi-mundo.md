---
paths:
  - "src/epi/**"
  - "src/world/**"
  - "src/economy/**"
  - "content/areas/**"
  - "tools/areas/**"
---

# EPI, mundo e economia

Especificação completa: `docs/spec/05-mapa.md` (mapa e regra de bloqueio) e `docs/spec/06-sistemas.md` (sistemas). Leia o arquivo correspondente antes de mudar valores ou posições.

Invariantes:

- Filtro: 90 s (básico), 150 s (nível 2), 240 s (nível 3). Correr multiplica o dreno por 1,3; abrigos reduzem o dreno em 50%.
- Regra de bloqueio: a ida e volta correndo até cada ponto ultrapassa o filtro do nível anterior e cabe no nível exigido com pelo menos 30 s de folga. O teste de rotas não pode quebrar.
- A Escotilha Oeste só abre depois da missão 3. Aberta antes, permite chegar ao Marco com o filtro básico.
- A Escotilha Leste abre na tarefa opcional.
- Subsolo e superfície são carregados separadamente; a eclusa da Boca do Poço é a transição.
- `tools/areas/gerar_areas.py` é longo: leia só a função que vai alterar.
