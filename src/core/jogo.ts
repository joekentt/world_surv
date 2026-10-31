import { Color3, Color4, HemisphericLight, Scene, ShadowGenerator, DirectionalLight, SpotLight, Vector3, type AbstractMesh } from "@babylonjs/core";
import { Hud } from "../ui/hud";
import { Medidores } from "../ui/medidores";
import { SistemaEPI } from "../epi/epi";
import { Subida } from "../epi/subida";
import { Coletaveis } from "../world/coletaveis";
import { TurnosDeLuz } from "../world/turnos";
import { Navegacao } from "../npc/navegacao";
import { GerenciadorNpcs } from "../npc/npcs";
import { Baloes } from "../ui/baloes";
import { DialogoUI } from "../ui/dialogoUI";
import { Paineis } from "../ui/paineis";
import { Dialogo, temDialogo } from "../quests/dialogo";
import { Missoes } from "../quests/missoes";
import { Roteiro } from "../quests/roteiro";
import { aplicarEfeitos } from "../quests/efeitos";
import { carregarJogo, salvarJogo } from "../save/save";
import { textos } from "../ui/textos";
import { Audio } from "./audio";
import { Estado } from "./estado";
import { Iluminacao } from "../world/iluminacao";
import { SistemaInteracao } from "../world/interacao";
import { CameraLateral } from "../player/camera";
import { Jogador } from "../player/jogador";
import { GerenciadorAreas, AREAS } from "../world/areas";
import type { AreaCarregada } from "../world/construtor";
import type { AreaDef } from "../world/tipos";
import { BibliotecaAnimacoes, Carregador } from "./carregador";
import { Entrada } from "./entrada";
import { ligarFisica } from "./fisica";
import type { Motor } from "./motor";
import { Personagem } from "./personagem";

/**
 * Orquestra cena, jogador, câmera, áreas e sistemas. Cada sistema expõe atualizar(dt) e é
 * chamado aqui, na ordem: entrada, jogador, câmera, mundo, NPCs, EPI, interface.
 */
export class Jogo {
  cena!: Scene;
  carregador!: Carregador;
  biblioteca!: BibliotecaAnimacoes;
  entrada = new Entrada();
  camera!: CameraLateral;
  jogador!: Jogador;
  areas!: GerenciadorAreas;
  sombras!: ShadowGenerator;
  luzAmbiente!: HemisphericLight;
  sol!: DirectionalLight;
  areaAtual: AreaDef | null = null;
  hud = new Hud();
  estado = new Estado();
  audio = new Audio();
  medidores!: Medidores;
  epi!: SistemaEPI;
  coletaveis!: Coletaveis;
  subida!: Subida;
  turnos!: TurnosDeLuz;
  navegacao!: Navegacao;
  npcs!: GerenciadorNpcs;
  baloes!: Baloes;
  ui!: { dialogo: DialogoUI };
  paineis!: Paineis;
  dialogo!: Dialogo;
  missoes!: Missoes;
  roteiro!: Roteiro;
  pausado = false;
  depoisDoDialogo: (() => void) | null = null;

  get loja(): { abrir: (id: string) => void } {
    return { abrir: (id: string) => this.paineis.abrirLoja(id) };
  }

  /** Trava jogador e interação enquanto há diálogo, painel ou cena de roteiro. */
  travarParaDialogo(sim: boolean): void {
    this.entrada.bloqueada = sim;
    this.jogador.travar(sim);
    this.interacao.bloqueado = sim;
    this.camera.distanciaExtra = sim && this.dialogo?.ativo ? -2.5 : this.roteiro?.emEpilogo ? this.camera.distanciaExtra : 0;
  }

  async salvar(): Promise<void> {
    const a = this.areaAtual;
    if (a && a.mundo === "vila") this.estado.d.local = { area: a.id, entrada: "inicio" };
    try {
      await salvarJogo(this.estado.d);
      this.hud.mensagemCurta(textos("salvoAuto"), 1.5);
    } catch (e) {
      console.warn("[save] falhou", e);
    }
  }

  async carregarSave(): Promise<boolean> {
    const d = await carregarJogo();
    if (!d) return false;
    this.estado.carregar(d);
    await this.transicionar(d.local.area, d.local.entrada);
    this.roteiro.atualizarMuro();
    return true;
  }
  /** Executado uma vez ao fim da próxima transição (antes de clarear a tela). */
  aposTransicao: (() => void) | null = null;
  interacao!: SistemaInteracao;
  iluminacao!: Iluminacao;
  lanterna!: SpotLight;
  tempo = 0;
  private sistemas: { atualizar(dt: number): void }[] = [];
  private emTransicao = false;

  constructor(readonly motor: Motor) {}

  async iniciar(areaInicial: string, entradaInicial = "inicio"): Promise<Scene> {
    const cena = new Scene(this.motor.engine);
    this.cena = cena;
    cena.clearColor = new Color4(0.04, 0.035, 0.03, 1);
    cena.ambientColor = new Color3(0.2, 0.2, 0.2);
    await ligarFisica(cena);
    this.carregador = new Carregador(cena);
    this.camera = new CameraLateral(cena);
    this.luzAmbiente = new HemisphericLight("ambiente", new Vector3(0.1, 1, -0.4), cena);
    this.luzAmbiente.intensity = 0.35;
    this.luzAmbiente.groundColor = new Color3(0.12, 0.1, 0.08);
    this.sol = new DirectionalLight("sol", new Vector3(-0.4, -1, 0.5), cena);
    this.sol.position = new Vector3(0, 30, -20);
    this.sol.intensity = 0;
    this.sombras = new ShadowGenerator(this.motor.qualidade === "alta" ? 2048 : 1024, this.sol);
    this.sombras.usePercentageCloserFiltering = true;
    this.sombras.bias = 0.002;

    this.areas = new GerenciadorAreas(cena, this.carregador, {
      qualidade: this.motor.qualidade,
      sombras: (m: AbstractMesh) => { m.receiveShadows = true; },
    });
    this.areas.aoCarregar = (a) => this.aoCarregarArea(a);
    this.areas.aoDescarregar = (a) => {
      this.iluminacao.removerLuzes(a.luzes);
      this.interacao.removerPrefixo(`${a.def.id}:`);
      this.coletaveis.aoDescarregar(a);
      this.aoAreaDescarregada?.(a);
    };
    this.iluminacao = new Iluminacao(cena, this.luzAmbiente, this.sol, this.motor.qualidade);
    this.aoTransicao = (sim) => this.hud.escurecer(sim);
    const audioPronto = this.audio.iniciar();
    this.biblioteca = await BibliotecaAnimacoes.carregar(this.carregador);
    const per = await Personagem.criar(cena, this.carregador, this.biblioteca, "protagonista");
    per.malhas.forEach((m) => this.sombras.addShadowCaster(m));
    const def = AREAS[areaInicial];
    const ent = def.entradas?.[entradaInicial] ?? { x: (def.inicio + def.fim) / 2, y: 0 };
    this.jogador = new Jogador(cena, per, this.entrada, ent.x, ent.y);
    this.interacao = new SistemaInteracao(this.entrada, this.hud, () => this.jogador.pes);
    this.medidores = new Medidores(this.hud.raiz, this.estado);
    this.epi = new SistemaEPI(this, this.medidores);
    this.coletaveis = new Coletaveis(this, cena);
    this.subida = new Subida(this);
    this.jogador.aoPisar = () => this.somPasso();
    this.turnos = new TurnosDeLuz(this.estado);
    this.baloes = new Baloes(cena, this.hud.raiz);
    this.navegacao = new Navegacao(cena);
    try {
      await this.navegacao.iniciar();
      this.navegacao.construir("vila", this.areas.areasDoMundo("vila"));
    } catch (e) {
      console.warn("[navegacao] Recast indisponível, NPCs andam em linha reta", e);
    }
    this.npcs = new GerenciadorNpcs(this, this.turnos, this.navegacao, this.baloes);
    this.ui = { dialogo: new DialogoUI(this.hud.raiz, this.entrada, () => this.audio.tocar("clique", 0.4)) };
    this.paineis = new Paineis(this, this.hud.raiz);
    this.paineis.ligarVolume();
    this.dialogo = new Dialogo(this);
    this.missoes = new Missoes(this);
    this.roteiro = new Roteiro(this);
    this.npcs.aoFalar = (n) => {
      if (temDialogo(n.def.id)) void this.dialogo.iniciar(n.def.id, n.def.nome);
    };
    this.jogador.aoPular = () => this.audio.tocar("pulo", 0.35, 0.9 + Math.random() * 0.2);
    this.lanterna = new SpotLight("lanterna", new Vector3(0, 1.75, -0.2), new Vector3(1, -0.25, 0), Math.PI / 3.2, 6, cena);
    this.lanterna.diffuse = new Color3(1, 0.92, 0.75);
    this.lanterna.intensity = 0;
    this.lanterna.range = 16;
    this.jogador.tetoAcima = (x, y) => this.areas.solidos().some((s) =>
      Math.abs(s.x - x) < s.w / 2 + 0.25 && s.y - s.h / 2 < y && s.y + s.h / 2 > y - 0.6 && Math.abs(s.z ?? 0) < 1);
    await this.areas.entrarMundo(def.mundo, ent.x);
    this.jogador.teleportar(ent.x, ent.y);
    this.atualizarAreaAtual();
    this.camera.seguir(ent.x, ent.y, 1, 0, true);

    await audioPronto;
    cena.onBeforeRenderObservable.add(() => this.quadro());
    this.expor();
    return cena;
  }

  /** Teleporta o jogador e posiciona a câmera sem suavização. */
  teleportar(x: number, y = 0): void {
    this.jogador.teleportar(x, y);
    this.camera.seguir(x, y, this.jogador.personagem.lado, 0, true);
  }

  registrar(s: { atualizar(dt: number): void }): void {
    this.sistemas.push(s);
  }

  private quadro(): void {
    // Passo máximo de 1/20 s: com fps muito baixo o jogo fica mais lento, mas a física continua estável.
    const dt = Math.min(this.motor.engine.getDeltaTime() / 1000, 0.05);
    this.entrada.atualizar();
    this.ui.dialogo.atualizar();
    this.paineis.atualizarInput();
    this.hud.atualizar(dt);
    if (this.pausado) {
      this.cena.physicsEnabled = false;
      return;
    }
    this.cena.physicsEnabled = true;
    this.tempo += dt;
    this.jogador.atualizar(dt);
    const p = this.jogador.pes;
    const [min, max] = this.areas.limites();
    this.camera.limiteMin = min;
    this.camera.limiteMax = max;
    this.camera.seguir(p.x, p.y, this.jogador.personagem.lado, dt);
    if (!this.emTransicao) void this.areas.atualizar(p.x);
    this.atualizarAreaAtual();
    this.interacao.atualizar();
    // lanterna do capacete: aponta para onde o personagem olha
    const lado = this.jogador.personagem.lado;
    this.lanterna.position.set(p.x + lado * 0.15, p.y + 1.7, -0.25);
    this.lanterna.direction.set(lado, -0.22, 0.12);
    const querLanterna = this.iluminacao.perfil.lanterna ? 9 : 0;
    this.lanterna.intensity += (querLanterna - this.lanterna.intensity) * Math.min(1, dt * 3);
    this.lanterna.setEnabled(this.lanterna.intensity > 0.05);
    this.iluminacao.atualizar(dt, new Vector3(p.x, p.y + 1, 0), this.tempo);
    this.epi.atualizar(dt);
    this.turnos.atualizar(dt);
    this.iluminacao.fatorLampadas = this.turnos.fatorLuz;
    this.npcs.atualizar(dt);
    this.baloes.atualizar();
    this.roteiro.atualizar(dt);
    this.coletaveis.atualizar(dt);
    this.audio.atualizar(dt, p.x, p.y);
    this.estado.d.tempoJogo += dt;
    for (const s of this.sistemas) s.atualizar(dt);
  }

  private atualizarAreaAtual(): void {
    const a = this.areas.areaEm(this.jogador.pes.x);
    if (a && a !== this.areaAtual) {
      const anterior = this.areaAtual;
      this.areaAtual = a;
      this.iluminacao.definirPerfil(a.estetica, !anterior || anterior.mundo !== a.mundo);
      if (anterior?.id !== a.id) this.hud.anunciarArea(a.nome);
      const epi = a.mundo === "superficie" || a.mundo === "boca";
      this.jogador.personagem.mostrar("_epi", epi);
      this.jogador.personagem.mostrar("_roupa", !epi);
      if (a.superficie && !this.epi.ativo && !this.subida.emSequencia) {
        this.epi.equipar();
        this.epi.entrarSuperficie();
      } else if (!a.superficie && this.epi.ativo) this.epi.sairSuperficie();
      this.ambienteSonoro(a);
      this.estado.avisar(`area:${a.id}`);
      if (a.mundo === "vila" && anterior && anterior.mundo !== "vila" && !this.roteiro?.emEpilogo) void this.salvar();
      if (anterior && anterior.mundo === "superficie" && a.mundo !== "superficie") {
        this.estado.definirFlag("voltou_recente", true);
        this.estado.definirFlag("voltou_dificil", this.epi.filtro < this.estado.capacidadeFiltro() * 0.25);
        setTimeout(() => this.estado.definirFlag("voltou_recente", false), 150_000);
      }
      this.aoMudarArea?.(a);
    }
  }

  aoMudarArea: ((a: AreaDef) => void) | null = null;

  usarInterativo(id: string, tipo: string): void {
    const e = this.estado;
    e.avisar(`interativo:${id}`);
    switch (tipo) {
      case "muro":
        if (e.missao("m4").estado === "ativa" && e.missao("m4").etapa === 1 && e.qtd("gravador_darci") > 0) void this.dialogo.iniciar("muro", "Muro dos Subidores");
        else this.hud.mensagemCurta(this.roteiro.textoMuro(), 5);
        break;
      case "fotos":
        this.hud.mensagemCurta(this.roteiro.textoFotos(), 4);
        break;
      case "banca":
        this.paineis.abrirLoja("nita");
        break;
      case "conselho":
        this.hud.mensagemCurta(textos("balcao"), 3);
        break;
      case "armario":
        this.hud.mensagemCurta(textos("armario", { n: e.qtd("filtro_reposicao"), s: e.capacidadeFiltro() }), 4);
        break;
      case "amostra":
        if (!(e.missao("m3").estado === "ativa" && e.missao("m3").etapa === 1)) this.hud.mensagemCurta(textos("amostraSemMissao"), 3.5);
        break;
      case "achado":
        if (e.missao("m4").estado === "ativa" && e.missao("m4").etapa === 0) void this.roteiro.achado();
        else this.hud.mensagemCurta(textos("achadoSemMissao"), 3.5);
        break;
      case "descontaminacao":
        this.hud.mensagemCurta(textos("chuveiros"), 3);
        break;
    }
  }

  /** Novo jogo: estado inicial, primeira missão e introdução. */
  async novoJogo(): Promise<void> {
    aplicarEfeitos(this, [{ missao: "m1", estado: "ativa", etapa: 0 }]);
    this.teleportar(-56);
    await this.roteiro.introducao();
  }

  private somPasso(): void {
    const est = this.areaAtual?.estetica;
    const som = est === "superficie" ? "passo_areia" : est === "boca" ? "passo_metal" : "passo_concreto";
    this.audio.tocar(som, 0.35, 0.85 + Math.random() * 0.3);
  }

  /** Camadas de som por área: laços de fundo e emissores posicionados. */
  private ambienteSonoro(a: AreaDef): void {
    const vila = a.mundo === "vila";
    this.audio.laco("ambiente_vila", vila || a.mundo === "boca" ? 0.35 : 0);
    this.audio.laco("goteira", a.mundo === "duto" ? 0.6 : vila ? 0.2 : 0);
    this.audio.laco("ambiente_superficie", a.mundo === "superficie" ? 0.5 : 0);
    this.audio.laco("vento", a.mundo === "superficie" ? 0.35 : a.mundo === "duto" ? 0.12 : 0);
    const emissores: { som: string; x: number; y: number; raio: number; volume: number }[] = [];
    for (const area of this.areas.areasDoMundo(a.mundo)) {
      for (const i of area.interativos ?? []) {
        if (i.tipo === "ambiente" && typeof i.som === "string") emissores.push({ som: i.som, x: i.x, y: 0, raio: 45, volume: 0.6 });
      }
      if (area.id === "praca") {
        emissores.push({ som: "ventilador", x: 18, y: 0, raio: 22, volume: 0.5 });
        emissores.push({ som: "multidao", x: -15, y: 0, raio: 35, volume: 0.45 });
        emissores.push({ som: "radio", x: 5, y: 0, raio: 9, volume: 0.35 });
      }
      if (area.id === "galerias") emissores.push({ som: "zumbido_fluor", x: 96, y: 0, raio: 50, volume: 0.25 }, { som: "ventilador", x: 100, y: 0, raio: 12, volume: 0.35 });
      if (area.id === "boca_do_poco") emissores.push({ som: "ventilador", x: 13, y: 0, raio: 20, volume: 0.4 });
    }
    this.audio.definirEmissores(emissores);
  }

  private aoCarregarArea(a: AreaCarregada): void {
    this.iluminacao.registrarLuzes(a.luzes);
    void this.coletaveis.aoCarregar(a);
    for (const [i, s] of (a.def.saidas ?? []).entries()) {
      this.interacao.adicionar({
        id: `${a.def.id}:saida${i}`, x: s.x, y: s.y, rotulo: s.rotulo, raio: 1.5, prioridade: 1,
        acao: () => void this.usarSaida(s.destino, s.entrada, s.tipo ?? "porta"),
      });
    }
    for (const it of a.def.interativos ?? []) {
      if (it.tipo === "ambiente" || it.tipo === "fila") continue;
      this.interacao.adicionar({
        id: `${a.def.id}:int:${it.id}`, x: it.x, y: it.y, raio: 1.6, prioridade: 1,
        rotulo: it.rotulo ?? it.id, acao: () => this.usarInterativo(it.id, it.tipo),
      });
    }
    if (a.def.id === "praca") this.roteiro?.atualizarMuro();
    if (a.def.escadas) {
      const todas = [...this.areas.carregadas.values()].flatMap((c) => c.def.escadas ?? []);
      this.jogador.escadas = todas;
    }
    this.aoAreaCarregada?.(a);
  }

  aoAreaCarregada: ((a: AreaCarregada) => void) | null = null;
  aoAreaDescarregada: ((a: AreaCarregada) => void) | null = null;
  /** Saídas do tipo eclusa podem ser interceptadas (sequência de EPI e descontaminação). */
  aoUsarEclusa: ((destino: string, entrada: string) => Promise<boolean>) | null = null;

  async usarSaida(destino: string, entrada: string, tipo: string): Promise<void> {
    if (tipo === "eclusa" && this.aoUsarEclusa && !(await this.aoUsarEclusa(destino, entrada))) return;
    await this.transicionar(destino, entrada);
  }

  /** Transição entre mundos (porta, eclusa): escurece, troca as áreas e posiciona o jogador. */
  async transicionar(destino: string, entrada: string, antes?: () => Promise<void> | void): Promise<void> {
    if (this.emTransicao) return;
    this.emTransicao = true;
    this.jogador.travar(true);
    await this.aoTransicao?.(true);
    await antes?.();
    const def = AREAS[destino];
    const ent = def.entradas?.[entrada] ?? { x: def.inicio + 2, y: 0 };
    await this.areas.entrarMundo(def.mundo, ent.x);
    this.jogador.escadas = [...this.areas.carregadas.values()].flatMap((c) => c.def.escadas ?? []);
    this.jogador.teleportar(ent.x, ent.y);
    this.areaAtual = null;
    this.atualizarAreaAtual();
    this.camera.seguir(ent.x, ent.y, this.jogador.personagem.lado, 0, true);
    const apos = this.aposTransicao;
    this.aposTransicao = null;
    apos?.();
    await this.aoTransicao?.(false);
    this.jogador.travar(false);
    this.emTransicao = false;
  }

  aoTransicao: ((escurecer: boolean) => Promise<void>) | null = null;

  /** Ganchos para os testes do Playwright. */
  private expor(): void {
    const vc = window.__vc;
    vc.jogo = this;
    vc.estado = () => {
      const p = this.jogador.pes;
      return { x: p.x, y: p.y, estado: this.jogador.estado, agachado: this.jogador.agachado, area: this.areaAtual?.id, mundo: this.areas.mundo, vx: this.jogador.velocidade.x };
    };
    vc.tecla = (codigo: string, pressionada: boolean) => this.entrada.simular(codigo, pressionada);
    vc.teleportar = (x: number, y = 0) => this.teleportar(x, y);
    vc.npcs = () => this.npcs.contagem();
    vc.missoes = () => JSON.parse(JSON.stringify(this.estado.d.missoes));
    vc.dados = () => JSON.parse(JSON.stringify(this.estado.d));
    vc.escolher = (trecho: string) => this.ui.dialogo.escolherPorTexto(trecho);
    vc.avancar = () => this.ui.dialogo.avancarTexto();
    vc.falar = (id: string) => { const n = this.npcs.porId(id); if (n) void this.dialogo.iniciar(id, n.def.nome); };
    vc.turno = () => this.turnos.turno;
    vc.epi = () => ({ filtro: this.epi.filtro, roupa: this.epi.roupa, saude: this.epi.saude, ativo: this.epi.ativo, tempestade: this.epi.tempestade, morto: this.epi.morto });
  }
}
