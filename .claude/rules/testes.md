---
paths:
  - "tests/**"
  - "playwright*.config.ts"
---

# Testes

- Rode só o arquivo da fase em andamento, com saída em arquivo: `npm test -- tests/faseN.spec.ts --reporter=line > logs/testes.log 2>&1; tail -n 40 logs/testes.log`. A suíte inteira, só ao fechar uma fase.
- Medições ficam em `tests/screenshots/fase-N/medicoes.json`. Leia esse arquivo em vez de procurar números no log.
- Screenshots em `tests/screenshots/fase-N/`. Abra no máximo 4 por rodada; para revisar mais, use um subagente que devolva só o veredito.
- Testes de câmera seguem a seção 3.4 de `docs/spec/03-camera-movimento.md`; o teste de rotas segue a seção 5.3 de `docs/spec/05-mapa.md`.
- Os fps medidos aqui usam renderização por software e não valem como medida de desempenho real.
