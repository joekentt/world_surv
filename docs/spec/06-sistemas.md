# Sistemas de jogo

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 6. Sistemas de jogo

| Sistema | O que entra no MVP |
| --- | --- |
| Movimento e câmera | Câmera livre em terceira pessoa e movimento conforme a seção 3. Teclado com mouse e gamepad |
| EPI | Dois medidores: filtro (ar) e integridade da roupa. O filtro drena com o tempo na superfície, mais rápido ao correr e mais devagar em abrigos; a roupa perde integridade com poeira e quedas. Com um deles zerado, o personagem recebe dano contínuo |
| Morte | O jogador acorda na vila e perde o que coletou na subida |
| Tempestade de poeira | Evento roteirizado com sirene de aviso: acelera o dreno e reduz a visibilidade |
| Upgrades | Filtro nível 2, filtro nível 3, roupa reforçada e cilindro extra. Tempos iniciais de filtro: 90 s (básico), 150 s (nível 2) e 240 s (nível 3) |
| Escotilhas | Pontos de retorno alternativos, abertos pelo lado de dentro ao longo da história |
| Coleta e inventário | Sucata, componentes, vidro e amostras. Mochila com limite de peso |
| Economia | Cota de filtro como moeda: vender recursos, comprar upgrades e filtros de reposição |
| Diálogo e missões | Diálogo com escolhas e variáveis de estado. 4 missões principais e 2 tarefas opcionais |
| NPCs | 20 moradores com rotina por turno de luz, 6 deles com nome e diálogo |
| Turnos de luz | Ciclo de dia e noite artificial no subsolo: as lâmpadas da vila baixam no turno de descanso. Na superfície, a hora do dia acompanha o mesmo relógio |
| Interface | Medidores de EPI, bússola, inventário, diário de missões, menu e opções de câmera |
| Save | Automático ao entrar na vila |
