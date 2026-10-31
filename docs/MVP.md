# Vila Cisterna: especificação do MVP

Jogo de sobrevivência em 2,5D para navegador. A humanidade vive no subsolo porque a superfície se tornou letal. O jogador é um subidor: alguém que sobe por pouco tempo, protegido por EPI, para coletar recursos. Este MVP cobre uma vila subterrânea, o túnel que leva até ela e um trecho da superfície.

Nomes de lugares e personagens são provisórios.

---

## 0. Instruções para o Claude Code

1. Trabalhe **uma fase por vez**, na ordem da seção 9. Não comece a fase seguinte sem cumprir o critério de avanço da fase atual.
2. Ao terminar cada fase, rode os testes do Playwright, salve os screenshots em `tests/screenshots/fase-N/` e registre em `docs/progresso.md` o que foi feito, o que falhou e as decisões tomadas.
3. Nenhum asset é modelado à mão. Todo modelo, rig, animação e textura sai de script em `tools/blender/` e é exportado em GLB.
4. Antes de usar a API de qualquer biblioteca (Babylon.js, Havok, plugin de navegação, MPFB2), consulte a documentação oficial da versão instalada. Não presuma nomes de funções ou parâmetros.
5. Itens da seção 11 (decisões pendentes) não devem ser decididos por conta própria. Siga as premissas listadas lá e avise quando uma delas bloquear o trabalho.
6. Faça commits pequenos, um por tarefa, com mensagem descritiva em português.
7. Textos do jogo (diálogos, missões, nomes) ficam em arquivos JSON em `content/`, nunca escritos direto no código.
8. Se uma validação da fase 0 falhar, use a alternativa indicada na tabela da seção 2 e registre o motivo em `docs/progresso.md`.

---

## 1. Objetivo do MVP

Uma fatia jogável de 20 a 30 minutos, rodando no navegador. Antes de qualquer expansão, ela precisa provar cinco pontos:

1. **O ciclo central é divertido:** pegar uma missão na vila, subir à superfície com tempo limitado pelo EPI, voltar antes que a proteção acabe, melhorar o equipamento e ir mais longe na subida seguinte.
2. **A vila parece viva:** NPCs com rotina própria, conversas de fundo e mudança visível entre os turnos de luz.
3. **Os personagens não têm aparência de Roblox:** malha contínua, proporção anatômica e rosto estilizado bem trabalhado.
4. **O mundo tem profundidade:** a história de uma vila pequena deixa claro que existe um mundo maior, com outras cidades, facções e um passado.
5. **O jogo roda bem no navegador:** 60 fps em um notebook comum, com WebGPU e fallback para WebGL2.

---

## 2. Stack técnica

| Camada | Escolha | Observação |
| --- | --- | --- |
| Motor | Babylon.js com TypeScript e Vite | WebGPU com detecção de suporte e fallback para WebGL2 |
| Física e colisão | Havok (plugin oficial do Babylon) | Movimento do jogador travado no plano lateral |
| Navegação de NPCs | Plugin de navegação Recast do Babylon | Validar a versão atual na fase 0 |
| Câmera | Lateral em 2,5D, mundo em 3D | Camadas de fundo em 3D reais criam paralaxe e sensação de profundidade |
| Cenário | Kits modulares gerados por script Python no Blender (headless), exportados em GLB | Um kit por estética: cisterna, gueto, capela, túnel, eclusa, superfície |
| Personagens | Corpo base MPFB2; roupas e EPIs gerados por script | Validar a automação headless do MPFB2. Alternativa: corpo gerado com skin modifier + subdivision surface |
| Animações | Ciclos gerados por script no rig do MPFB2: parado, andar, correr, pular, agachar, escada, interagir | Validar a qualidade. Alternativa: biblioteca de animações CC0 compatível com o rig |
| Áudio | Motor de áudio do Babylon; efeitos e vozes via ElevenLabs | Conferir se o plano da ElevenLabs permite uso comercial |
| Testes | Playwright abre o jogo, tira screenshots e mede fps | O Claude Code analisa as imagens e corrige antes de avançar |
| Compressão | Malhas com Draco ou meshopt, texturas em KTX2 | Áreas carregadas sob demanda |
| Save | IndexedDB no navegador | Um slot no MVP |
| Publicação | Site estático no Cloudflare Pages | Repositório no GitHub |

### Estrutura de pastas sugerida

```
/
├─ CLAUDE.md                  resumo do projeto e regras da seção 0
├─ docs/
│  ├─ MVP.md                  este arquivo
│  └─ progresso.md            registro por fase
├─ src/
│  ├─ core/                   motor, cena, loop, carregamento de áreas
│  ├─ player/                 controle, câmera, animação do jogador
│  ├─ epi/                    medidores, dreno, tempestade, upgrades
│  ├─ world/                  áreas, transições, turnos de luz
│  ├─ npc/                    rotinas, navegação, conversas de fundo
│  ├─ quests/                 diálogo, missões, variáveis de estado
│  ├─ economy/                inventário, comércio, cotas de filtro
│  ├─ ui/                     HUD, inventário, diário, menu
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
└─ tests/                     Playwright: screenshots e fps
```

---

## 3. Mundo e roteiro

A vila é pequena, mas tudo nela aponta para um mundo maior: um passado que ninguém viveu, cidades que o jogador ainda não visitou e um conflito pela única coisa que mantém todos vivos, os filtros de respiração.

### Premissa

Há quatro gerações, a atmosfera perdeu a proteção contra o sol. Radiação e tempestades de poeira cáustica tornaram a superfície letal em poucas horas. Os sobreviventes desceram para minas, linhas de metrô, cisternas e galerias de drenagem. Ninguém vivo viu o céu azul: ele existe em fotos desbotadas, em hinos e nas histórias dos mais velhos.

A superfície ainda guarda o que o subsolo não produz: metal, vidro, componentes eletrônicos e sementes em cofres antigos. Quem sobe para buscar isso é chamado de **subidor**.

### A Vila Cisterna

A vila ocupa um reservatório de água de uma cidade que não existe mais, a 40 metros de profundidade. É a vila mais rasa da região: a poeira vaza pelas frestas, o ar é pior e a economia depende dos subidores. A moeda é a **cota de filtro**, uma ficha que vale um filtro de respiração. Quem controla os filtros controla a vila.

Zonas da vila:

- **Praça do Reservatório:** centro da vila, com mercado, sede do Conselho, bomba d'água e o Muro dos Subidores.
- **Galerias Secas:** o gueto, onde vive quem perdeu a cota. Barracos empilhados, filtros recondicionados vendidos no improviso, pichações.
- **Capela da Vigília:** templo improvisado em uma antiga casa de máquinas, com vitrais feitos de garrafas e um facho de luz que imita o sol.

### Forças em jogo

- **Conselho da Cisterna:** governa e distribui as cotas. Sabe que o estoque de filtros dura poucos meses e esconde isso dos moradores.
- **Vigília do Sol:** grupo religioso que vê a Queima como castigo e acredita que o sol vai perdoar quem tiver fé. Prega o retorno à superfície e cresce nas Galerias Secas.
- **Caravana de Qarar:** comerciantes de Qarar, cidade profunda de estética do Oriente Médio e primeira cidade da expansão. São os únicos que fabricam filtros novos.
- **Moradores das Galerias:** vivem de contrabando e favores. Ajudam o jogador em troca de sucata e informação.

### Protagonista

Um subidor recém-formado, aprendiz de Darci, o subidor mais experiente da vila. Darci subiu há 12 dias e não voltou. O Conselho entrega ao protagonista o EPI antigo de Darci, remendado, porque a vila precisa de alguém que suba.

### Arco do MVP: "O último registro"

1. **O primeiro dia:** missão na vila que ensina movimento e interação. O jogador leva uma peça de ventilador às Galerias Secas e conhece as três zonas.
2. **A primeira subida:** coletar sucata perto da Boca do Poço, a saída para a superfície. O jogador aprende o medidor de EPI e volta com pouco tempo de sobra.
3. **A escolha:** a Vigília pede uma amostra de terra do Marco, ponto intermediário da superfície, para provar que o solo está "curando". O Conselho proíbe. Para chegar lá, o jogador precisa do filtro nível 2. Ajudar ou recusar altera falas, preços e o sermão da capela.
4. **O registro de Darci:** com o filtro nível 3, o jogador alcança a Antena, ponto mais distante. Encontra a máscara e o gravador de Darci, sem sinal do corpo. A gravação revela que a Caravana reduz de propósito os filtros enviados às vilas rasas e que Darci viu luzes acesas à noite no horizonte, onde ninguém deveria estar vivo.
5. **O desfecho:** o jogador decide o destino da gravação: entregar ao Conselho, entregar à Vigília ou guardar. Cada escolha gera uma reação diferente da vila. O MVP termina na superfície, com a luz piscando no horizonte.

### Como a profundidade aparece sem exposição

A história chega pelo cenário e por falas curtas, nunca por textos longos:

- O Muro dos Subidores exibe as máscaras de quem não voltou. A de Darci aparece ou não, conforme o desfecho.
- Fotos do céu azul são vendidas no mercado como relíquias.
- Crianças brincam de "subida" com máscaras de papelão.
- A fila das cotas cresce ao longo do jogo, mostrando que o estoque está acabando.
- Placas do mundo antigo continuam nas paredes, como "Reservatório Municipal nº 3".
- O rádio da Caravana cita Qarar e outras cidades pelo nome, plantando a expansão.
- A vila tem gírias próprias, como "queimar o filtro" (gastar a proteção) e "ver o céu" (morrer na superfície).

---

## 4. Mapa do MVP

Seis áreas ligadas em sequência. Cada upgrade de EPI leva o jogador um ponto mais longe na superfície.

```
 SUPERFÍCIE
   ┌──────────────► Sucata próxima ──► O Marco ──────► A Antena
   │                (EPI básico)       (filtro nível 2)  (filtro nível 3)
═══╪═════════════════════════════════════════════════════  nível do solo
   │
 [Boca do Poço]   eclusa e descontaminação
   ▲
 [Duto Norte]     túnel de metrô antigo e trecho de caverna
   ▲
 ┌─┴───────────── VILA CISTERNA (40 m de profundidade) ────────────────┐
 │ [Capela da Vigília] ◄── [Praça do Reservatório] ◄── [Galerias Secas] │
 └─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Sistemas de jogo

| Sistema | O que entra no MVP |
| --- | --- |
| Movimento | Andar, correr, pular, agachar, subir escadas e cordas. Teclado e gamepad |
| EPI | Dois medidores: filtro (ar) e integridade da roupa. O filtro drena com o tempo na superfície; a roupa perde integridade com poeira e quedas. Com um deles zerado, o personagem recebe dano contínuo |
| Morte | O jogador acorda na vila e perde o que coletou na subida |
| Tempestade de poeira | Evento com sirene de aviso que acelera o dreno do EPI |
| Upgrades | Filtro nível 2, filtro nível 3, roupa reforçada e cilindro extra. Tempos iniciais de filtro: 90 s (básico), 150 s (nível 2) e 240 s (nível 3), a ajustar nos testes |
| Coleta e inventário | Sucata, componentes, vidro e amostras. Mochila com limite de peso |
| Economia | Cota de filtro como moeda: vender recursos, comprar upgrades e filtros de reposição |
| Diálogo e missões | Diálogo com escolhas e variáveis de estado. 4 missões principais e 2 tarefas opcionais |
| NPCs | 20 moradores com rotina por turno de luz, 6 deles com nome e diálogo |
| Turnos de luz | Ciclo de dia e noite artificial: as lâmpadas da vila baixam no turno de descanso |
| Interface | Medidores de EPI, inventário, diário de missões e menu |
| Save | Automático ao entrar na vila |

Todos os valores numéricos (tempos, preços, pesos, dano) ficam em um arquivo de configuração único, para facilitar o balanceamento.

---

## 6. Direção de arte

A iluminação separa os dois mundos: o subsolo é quente, próximo e cheio de pontos de luz; a superfície é branca, estourada e sem abrigo. Cada área tem uma luz e três ou quatro elementos que a identificam à primeira vista.

| Área | Luz e cor | Elementos de identidade |
| --- | --- | --- |
| Praça do Reservatório | Lâmpadas âmbar, concreto úmido | Colunas do reservatório, varais, bomba d'água, mercado de lonas |
| Galerias Secas | Fluorescentes frias e falhando, tom verde-azulado | Barracos empilhados de chapa, fiação aparente, pichações |
| Capela da Vigília | Facho branco-dourado imitando o sol, vitrais coloridos | Bancos de madeira reaproveitada, altar com fotos do céu |
| Duto Norte | Quase escuro: lanterna do capacete e musgo luminoso | Trilhos de metrô antigos, água escorrendo, trecho de caverna natural |
| Boca do Poço | Luz vermelha de alerta, névoa de descontaminação | Porta de eclusa, chuveiros, armários de EPI |
| Superfície | Céu branco-amarelado, poeira no ar, sombras duras | Ruínas de prédios, carros soterrados, a Antena no horizonte |

Cada efeito visual que depende de WebGPU precisa de uma versão simplificada para WebGL2.

---

## 7. Personagens

- Corpos gerados no MPFB2, com proporção de referência de cerca de 7,5 cabeças de altura.
- Malha contínua, shading suave, membros afunilados, pescoço, ombros arredondados e mãos com pelo menos o formato de luva com polegar separado.
- Roupas em camadas, com remendos e desgaste, geradas por script sobre o corpo base.
- Rostos estilizados, com variação de idade, nariz, maxilar e olhos, para que nenhum NPC pareça cópia de outro.
- Na superfície, máscara e capacete cobrem o rosto. Na vila, capuzes, lenços e turbantes fazem parte do figurino.
- Todo personagem passa pelo `render_check.py` (frente, lado e 3/4) antes de entrar no jogo.

**Critério de aceite:** nenhuma parte do corpo com aspecto de bloco ou de peças encaixadas. Se o render mostrar isso, corrija antes de exportar.

---

## 8. Vida da vila

- **Rotina por turno:** trabalho, fila das cotas, culto e descanso, cada NPC com seus horários e lugares definidos em `content/npcs/`.
- **Ações nos pontos de trabalho:** varrer, consertar, cozinhar, rezar, conversar em pares.
- **Conversas de fundo:** falas curtas disparadas por proximidade, que comentam o estoque de filtros, a Vigília e o sumiço de Darci.
- **Reação ao jogador:** NPCs olham, cumprimentam e comentam o EPI sujo ou a volta de uma subida difícil.
- **Som em camadas:** gotejamento, ventiladores, mercado e o sermão distante, com volume conforme a distância.
- **Partículas:** poeira caindo das frestas, vapor da bomba d'água, fumaça das cozinhas.

---

## 9. Fases de produção

### Fase 0: Validação técnica

Tarefas:
- Criar o projeto com Vite, TypeScript e Babylon.js.
- Implementar a detecção de WebGPU com fallback para WebGL2 e mostrar na tela qual renderizador está ativo.
- Inicializar o Havok em uma cena de teste.
- Gerar no Blender headless um módulo de parede, exportar em GLB e carregar no Babylon.
- Gerar um corpo no MPFB2 em modo headless já com rig e exportar em GLB. Se não funcionar, usar skin modifier.
- Gerar por script um ciclo de caminhada e reproduzi-lo no Babylon.
- Criar o `render_check.py`.
- Criar o teste do Playwright que abre a página, tira screenshot e mede o fps médio por 10 segundos, nos dois renderizadores.

Entrega: motor com WebGPU e fallback, pipeline Blender → GLB e um personagem MPFB2 andando no navegador.

**Avança se:** o personagem não tem aspecto de bloco, roda a 60 fps e o screenshot automático funciona.

### Fase 1: Movimento e câmera

Tarefas: controle 2,5D com andar, correr, pular, agachar e subir escadas e cordas; câmera lateral com suavização; suporte a teclado e gamepad; sala de teste com plataformas e escadas.

**Avança se:** pulo e corrida respondem com precisão no teclado e no gamepad.

### Fase 2: Cenário em blocos

Tarefas: kits modulares gerados no Blender para cada estética; as seis áreas montadas com geometria simples; transições entre áreas com carregamento sob demanda; camadas de fundo para paralaxe.

**Avança se:** o personagem percorre das Galerias Secas até a Antena sem travar.

### Fase 3: EPI e superfície

Tarefas: medidores de filtro e roupa; dreno na superfície; tempestade de poeira com sirene; dano contínuo e morte; coleta e inventário com limite de peso; eclusa da Boca do Poço como transição.

**Avança se:** uma subida completa, com volta à vila, é tensa e compreensível sem tutorial escrito.

### Fase 4: Vila viva

Tarefas: 20 NPCs com aparência variada; rotinas por turno de luz; navegação; ações nos pontos de trabalho; conversas de fundo por proximidade; reação ao jogador; otimização com instancing, níveis de detalhe e animação reduzida fora da tela.

**Avança se:** o jogo mantém 60 fps com todos os NPCs em cena no hardware mínimo definido.

### Fase 5: Missões e economia

Tarefas: sistema de diálogo com escolhas e variáveis de estado; as 4 missões principais e 2 opcionais; comércio com cotas de filtro; upgrades de EPI; save automático no IndexedDB; os três desfechos.

**Avança se:** o MVP é jogável do primeiro dia até o desfecho, nos três finais.

### Fase 6: Arte final e áudio

Tarefas: materiais finais; iluminação por área conforme a seção 6; personagens finais com roupas e EPIs; partículas; efeitos sonoros e vozes.

**Avança se:** cada área é reconhecida por um único screenshot.

### Fase 7: Polimento e publicação

Tarefas: balanceamento do EPI e da economia; compressão de malhas e texturas; testes nos navegadores-alvo; publicação no Cloudflare Pages.

**Avança se:** existe um link público jogável de 20 a 30 minutos, do início ao fim.

---

## 10. Riscos e mitigação

| Risco | Efeito | Mitigação |
| --- | --- | --- |
| MPFB2 não funciona bem em modo headless | Atraso nos personagens | Corpo gerado por skin modifier ou corpo base CC0 |
| Animações geradas por script ficam rígidas | Personagens com movimento de robô | Biblioteca de animações CC0 compatível com o rig, validada na fase 0 |
| 20 NPCs pesam no navegador | Queda de fps em notebooks | Instancing, níveis de detalhe, animação reduzida fora da tela, sombras limitadas |
| Navegador sem WebGPU | Visual inferior | Fallback WebGL2 testado desde a fase 0, com versão simplificada de cada efeito |
| Download grande | Carregamento lento | Malhas comprimidas (Draco ou meshopt), texturas KTX2, áreas carregadas sob demanda |
| Escopo crescendo | MVP sem fim | Lista "Fora do MVP" fixa; ideias novas vão para `docs/pos-mvp.md` |
| Limite de uso do plano Pro | Fases interrompidas no meio | Tarefas pequenas, com critério verificável e registro em `docs/progresso.md` |

---

## 11. Decisões pendentes e premissas em uso

Até a confirmação, siga a premissa indicada. Não altere nenhuma delas sem autorização.

| Decisão | Premissa em uso |
| --- | --- |
| Motor | Babylon.js |
| Combate | Nenhum combate no MVP. A câmera e a física da fase 1 não devem impedir a inclusão futura |
| Navegadores e hardware mínimos | Chrome e Firefox atuais em notebook com GPU integrada |
| Aparência do protagonista | Aparência fixa |
| Idioma | Português, com textos em JSON preparados para receber outros idiomas |
| Nomes definitivos | Usar os nomes provisórios deste documento |

---

## 12. Fora do MVP

Combate, outras cidades, fabricação de itens, criação de personagem, multiplayer e versão para celular.
