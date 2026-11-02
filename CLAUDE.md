# Vila Cisterna

Jogo de sobrevivência em 3D com câmera livre em terceira pessoa, para navegador (Babylon.js + TypeScript + Vite + Havok).
A especificação vigente é a revisão 2 (2/11/2026); a revisão 1, em 2,5D, está no histórico do git.
Especificação completa em `docs/MVP.md`; registro por fase em `docs/progresso.md`.

## Regras de trabalho (seção 0 do MVP)

1. Uma fase por vez, na ordem da seção 10. Só avance quando o critério da fase atual for cumprido.
2. Ao fim de cada fase: rodar o Playwright, salvar screenshots em `tests/screenshots/fase-N/` e registrar em `docs/progresso.md` o que foi feito, o que falhou e as decisões.
3. Nenhum asset é modelado à mão: modelos, rigs, animações e texturas saem de scripts em `tools/blender/`, exportados em GLB.
4. Antes de usar a API de uma biblioteca, conferir a documentação ou os `.d.ts` da versão instalada.
5. Decisões pendentes (seção 12) não são tomadas por conta própria: seguir as premissas listadas.
6. Commits pequenos, um por tarefa, com mensagem em português.
7. Textos do jogo ficam em JSON em `content/`, nunca no código.
8. Se uma validação da fase 0 falhar, usar a alternativa da seção 2 e registrar o motivo.
9. Migração da revisão 2: sem travamento de plano, câmera em terceira pessoa, fases 1 e 2 refeitas; o que foi descartado fica registrado em `docs/progresso.md`.
10. Todos os valores de câmera, movimento, EPI e economia ficam em `src/config.ts`.

## Comandos

```bash
npm install
npm run dev                 # http://localhost:5173 (?cena=teste, ?render=webgl2)
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
