# Objetivo, escopo e premissas

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 1. Objetivo do MVP

Uma fatia jogável de 20 a 30 minutos, rodando no navegador. Antes de qualquer expansão, ela precisa provar seis pontos:

1. **O ciclo central é divertido:** pegar uma missão na vila, subir à superfície com tempo limitado pelo EPI, voltar antes que a proteção acabe, melhorar o equipamento e ir mais longe na subida seguinte.
2. **Controlar o personagem é agradável:** movimento leve e fluido, com câmera livre que acompanha o jogador sem atrapalhar.
3. **A vila parece viva:** NPCs com rotina própria, conversas de fundo e mudança visível entre os turnos de luz.
4. **Os personagens não têm aparência de Roblox:** malha contínua, proporção anatômica e rosto estilizado bem trabalhado.
5. **O mundo parece grande e aberto:** a vila e a superfície mostram lugares, caminhos e horizontes além do que o MVP permite alcançar. A história também deixa claro que existem outras cidades, facções e um passado.
6. **O jogo roda bem no navegador:** 60 fps em um notebook comum, com WebGPU e fallback para WebGL2.

## 13. Fora do MVP

Combate, outras cidades, abertura do Portão da Caravana, descida pelo poço profundo, fabricação de itens, criação de personagem, multiplayer e versão para celular.

## 12. Decisões pendentes e premissas em uso

Até a confirmação, siga a premissa indicada. Não altere nenhuma delas sem autorização.

| Decisão | Premissa em uso |
| --- | --- |
| Motor | Babylon.js |
| Combate | Nenhum combate no MVP. A câmera deve permitir mira e travamento de alvo no futuro, sem reescrita |
| Enquadramento | Câmera centralizada atrás do personagem; deslocamento sobre o ombro disponível só em configuração |
| Navegadores e hardware mínimos | Chrome e Firefox atuais em notebook com GPU integrada |
| Aparência do protagonista | Aparência fixa |
| Idioma | Português, com textos em JSON preparados para receber outros idiomas |
| Nomes definitivos | Usar os nomes provisórios desta especificação |
