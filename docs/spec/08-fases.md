# Fases de produção

Parte da especificação do MVP (revisão 2). Índice: `docs/spec/README.md`.

## 10. Fases de produção

### Fase 0: Validação técnica

Tarefas:
- Criar o projeto com Vite, TypeScript e Babylon.js.
- Implementar a detecção de WebGPU com fallback para WebGL2 e mostrar na tela qual renderizador está ativo.
- Inicializar o Havok e o controlador de personagem em uma cena de teste.
- Gerar no Blender headless um módulo de parede, exportar em GLB e carregar no Babylon.
- Gerar um corpo no MPFB2 em modo headless já com rig e exportar em GLB. Se não funcionar, usar skin modifier.
- Gerar por script um ciclo de caminhada e reproduzi-lo no Babylon.
- Criar o `render_check.py`.
- Criar o teste do Playwright que abre a página, tira screenshot e mede o fps médio por 10 segundos, nos dois renderizadores.

Entrega: motor com WebGPU e fallback, pipeline Blender → GLB e um personagem MPFB2 andando no navegador.

**Avança se:** o personagem não tem aspecto de bloco, roda a 60 fps e o screenshot automático funciona.

### Fase 1: Câmera e movimento em terceira pessoa

Tarefas: câmera conforme as seções 3.1 e 3.2; controlador de personagem com os parâmetros da seção 3.3; mistura de animações de locomoção; Pointer Lock; teclado com mouse e gamepad; menu de opções da câmera; sala de teste com corredor estreito de 2,5 m, área aberta, escadas, rampas, plataformas, escada de mão e corda; testes automatizados da seção 3.4.

**Avança se:** os seis testes da seção 3.4 passam e o usuário aprova a sensação de controle na sala de teste.

### Fase 2: Cenário em blocos

Tarefas: kits modulares gerados no Blender para cada estética; a vila em três níveis, o Duto Norte com os dois desvios, a Estação Aurora, a Boca do Poço e a superfície com os pontos da seção 5.2, todos com geometria simples; zonas de câmera; impostores do horizonte e névoa; carregamento separado de subsolo e superfície, com a eclusa como transição; navmesh e teste de bloqueio da seção 5.3.

**Avança se:** o personagem percorre das Galerias Secas até a Antena sem travar; a superfície roda a 60 fps no hardware mínimo; o teste de bloqueio passa; e do alto da Antena e das passarelas da vila o horizonte e os marcos ficam visíveis em screenshot.

### Fase 3: EPI e superfície

Tarefas: medidores de filtro e roupa; dreno na superfície, ao correr e em abrigos; bússola; tempestade de poeira com sirene e perda de visibilidade; dano contínuo e morte; coleta e inventário com limite de peso; escotilhas como pontos de retorno; eclusa da Boca do Poço com descontaminação.

**Avança se:** uma subida completa, com volta à vila, é tensa e compreensível sem tutorial escrito.

### Fase 4: Vila viva

Tarefas: 20 NPCs com aparência variada; rotinas por turno de luz; navegação entre níveis; ações nos pontos de trabalho; conversas de fundo por proximidade; reação ao jogador; otimização com instancing, níveis de detalhe e animação reduzida fora da tela.

**Avança se:** o jogo mantém 60 fps com todos os NPCs em cena no hardware mínimo definido, vistos das passarelas.

### Fase 5: Missões e economia

Tarefas: sistema de diálogo com escolhas e variáveis de estado; as 4 missões principais e 2 opcionais; comércio com cotas de filtro; upgrades de EPI; abertura das escotilhas conforme a história; save automático no IndexedDB; os três desfechos.

**Avança se:** o MVP é jogável do primeiro dia até o desfecho, nos três finais.

### Fase 6: Arte final e áudio

Tarefas: materiais finais; iluminação por área conforme a seção 7; personagens finais com roupas e EPIs; partículas; efeitos sonoros e vozes.

**Avança se:** cada área é reconhecida por um único screenshot, tirado de pelo menos dois ângulos de câmera.

### Fase 7: Polimento e publicação

Tarefas: balanceamento da câmera, do movimento, do EPI e da economia; compressão de malhas e texturas; testes nos navegadores-alvo; publicação no Cloudflare Pages.

**Avança se:** existe um link público jogável de 20 a 30 minutos, do início ao fim.
