# Riscos e mitigação

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 11. Riscos e mitigação

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| MPFB2 não funciona bem em modo headless | Atraso nos personagens | Corpo gerado por skin modifier ou corpo base CC0 |
| Animações geradas por script ficam rígidas | Personagens com movimento de robô | Biblioteca de animações CC0 compatível com o rig, validada na fase 0 |
| Câmera atravessa paredes ou se perde nos túneis | Jogo desconfortável no subsolo | Colisão por esfera, zonas de câmera, teste automatizado no corredor de 2,5 m |
| Movimento pesado ou personagem deslizando | Controle desagradável | Parâmetros no `config.ts`, velocidade da animação sincronizada à velocidade real, aprovação do usuário na fase 1 |
| Superfície aberta pesa no navegador | Queda de fps em notebooks | Carregamento separado do subsolo, LOD, impostores, névoa, thin instances, sombras limitadas |
| 20 NPCs pesam no navegador | Queda de fps na vila | Instancing, níveis de detalhe, animação reduzida fora da tela |
| Navegador sem WebGPU | Visual inferior | Fallback WebGL2 testado desde a fase 0, com versão simplificada de cada efeito |
| Download grande | Carregamento lento | Malhas comprimidas (Draco ou meshopt), texturas KTX2, áreas carregadas sob demanda |
| Escopo do mundo aberto crescendo | MVP sem fim | Superfície limitada à área da seção 5.2, conteúdo concentrado em três pontos e duas escotilhas; ideias novas vão para `docs/pos-mvp.md` |
| Limite de uso do plano Pro | Fases interrompidas no meio | Tarefas pequenas, com critério verificável e registro em `docs/progresso.md` |
