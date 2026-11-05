# Stack técnica e estrutura de pastas

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 2. Stack técnica

| Camada | Escolha | Observação |
| --- | --- | --- |
| Motor | Babylon.js com TypeScript e Vite | WebGPU com detecção de suporte e fallback para WebGL2 |
| Física | Havok (plugin oficial do Babylon) | Colisão do cenário, objetos soltos, raycasts da câmera |
| Controle do personagem | Controlador de personagem do Babylon com Havok (documentação: Physics > Character Controller) | Validar a API na versão instalada. Movimento livre em 3D, sem travamento de plano |
| Câmera | Câmera em terceira pessoa com órbita livre, implementada em `src/camera/` | Especificação completa na seção 3. Mouse capturado com Pointer Lock |
| Navegação de NPCs | Plugin de navegação Recast do Babylon | Navmesh com vários níveis (passarelas e escadas) |
| Cenário | Kits modulares gerados por script Python no Blender (headless), exportados em GLB | Um kit por estética: cisterna, gueto, capela, túnel, estação, eclusa, superfície |
| Personagens | Corpo base MPFB2; roupas e EPIs gerados por script | Validar a automação headless do MPFB2. Alternativa: corpo gerado com skin modifier + subdivision surface |
| Animações | Ciclos gerados por script no rig do MPFB2: parado, andar, correr, pular, aterrissar, agachar, giro rápido, escada, corda, interagir | Validar a qualidade. Alternativa: biblioteca de animações CC0 compatível com o rig |
| Áudio | Motor de áudio do Babylon; efeitos e vozes via ElevenLabs | Conferir se o plano da ElevenLabs permite uso comercial |
| Testes | Playwright abre o jogo, simula entradas, tira screenshots e mede fps | O Claude Code analisa as imagens e os registros e corrige antes de avançar |
| Otimização | Níveis de detalhe (LOD), thin instances, impostores no horizonte, névoa por distância, carregamento por área | O subsolo e a superfície são carregados separadamente |
| Compressão | Malhas com Draco ou meshopt, texturas em KTX2 | |
| Save | IndexedDB no navegador | Um slot no MVP |
| Publicação | Site estático no Cloudflare Pages | Repositório no GitHub |

### Estrutura de pastas sugerida

```
/
├─ CLAUDE.md                  regras permanentes e mapa da memória do projeto
├─ .claude/
│  ├─ settings.json           hook que restaura o estado após compactação
│  ├─ hooks/                  scripts dos hooks
│  ├─ rules/                  regras por pasta, carregadas sob demanda
│  └─ skills/                 /retomar e /fechar-tarefa
├─ docs/
│  ├─ estado.md               estado atual (sobrescrito a cada tarefa)
│  ├─ decisoes.md             registro de decisões
│  ├─ progresso.md            histórico da revisão 2
│  ├─ pos-mvp.md              ideias fora do escopo
│  ├─ spec/                   especificação do MVP dividida por tema
│  └─ _arquivo/               histórico antigo (não ler sem necessidade)
├─ logs/                      saídas longas de comandos (fora do git)
├─ src/
│  ├─ config.ts               todos os valores ajustáveis
│  ├─ core/                   motor, cena, loop, carregamento de áreas
│  ├─ camera/                 órbita, recentralização, colisão, zonas de câmera
│  ├─ player/                 controlador, entrada, animação do jogador
│  ├─ epi/                    medidores, dreno, tempestade, abrigos, upgrades
│  ├─ world/                  áreas, transições, turnos de luz, escotilhas
│  ├─ npc/                    rotinas, navegação, conversas de fundo
│  ├─ quests/                 diálogo, missões, variáveis de estado
│  ├─ economy/                inventário, comércio, cotas de filtro
│  ├─ ui/                     HUD, bússola, inventário, diário, menu, opções
│  └─ save/                   IndexedDB
├─ content/
│  ├─ dialogos/               JSON por personagem
│  ├─ missoes/                JSON por missão
│  └─ npcs/                   JSON com rotina e aparência de cada NPC
├─ tools/blender/
│  ├─ kits/                   scripts dos módulos de cenário
│  ├─ personagens/            corpo, roupas, EPIs, variação de rosto
│  ├─ animacoes/              ciclos de animação
│  └─ render_check.py         render em 3 vistas para validação
├─ public/assets/             GLB, KTX2 e áudio gerados
└─ tests/                     Playwright: entradas simuladas, screenshots e fps
```
