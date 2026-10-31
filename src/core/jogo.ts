import { Color3, Color4, HemisphericLight, Scene, ShadowGenerator, DirectionalLight, Vector3, type AbstractMesh } from "@babylonjs/core";
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
    this.biblioteca = await BibliotecaAnimacoes.carregar(this.carregador);
    const per = await Personagem.criar(cena, this.carregador, this.biblioteca, "protagonista");
    per.malhas.forEach((m) => this.sombras.addShadowCaster(m));
    const def = AREAS[areaInicial];
    const ent = def.entradas?.[entradaInicial] ?? { x: (def.inicio + def.fim) / 2, y: 0 };
    this.jogador = new Jogador(cena, per, this.entrada, ent.x, ent.y);
    this.jogador.tetoAcima = (x, y) => this.areas.solidos().some((s) =>
      Math.abs(s.x - x) < s.w / 2 + 0.25 && s.y - s.h / 2 < y && s.y + s.h / 2 > y - 0.6 && Math.abs(s.z ?? 0) < 1);
    await this.areas.entrarMundo(def.mundo, ent.x);
    this.jogador.teleportar(ent.x, ent.y);
    this.atualizarAreaAtual();
    this.camera.seguir(ent.x, ent.y, 1, 0, true);

    cena.onBeforeRenderObservable.add(() => this.quadro());
    this.expor();
    return cena;
  }

  registrar(s: { atualizar(dt: number): void }): void {
    this.sistemas.push(s);
  }

  private quadro(): void {
    // Passo máximo de 1/20 s: com fps muito baixo o jogo fica mais lento, mas a física continua estável.
    const dt = Math.min(this.motor.engine.getDeltaTime() / 1000, 0.05);
    this.tempo += dt;
    this.entrada.atualizar();
    this.jogador.atualizar(dt);
    const p = this.jogador.pes;
    const [min, max] = this.areas.limites();
    this.camera.limiteMin = min;
    this.camera.limiteMax = max;
    this.camera.seguir(p.x, p.y, this.jogador.personagem.lado, dt);
    if (!this.emTransicao) void this.areas.atualizar(p.x);
    this.atualizarAreaAtual();
    for (const s of this.sistemas) s.atualizar(dt);
  }

  private atualizarAreaAtual(): void {
    const a = this.areas.areaEm(this.jogador.pes.x);
    if (a && a !== this.areaAtual) {
      this.areaAtual = a;
      this.aoMudarArea?.(a);
    }
  }

  aoMudarArea: ((a: AreaDef) => void) | null = null;

  private aoCarregarArea(a: AreaCarregada): void {
    if (a.def.escadas) {
      const todas = [...this.areas.carregadas.values()].flatMap((c) => c.def.escadas ?? []);
      this.jogador.escadas = todas;
    }
    this.aoAreaCarregada?.(a);
  }

  aoAreaCarregada: ((a: AreaCarregada) => void) | null = null;

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
  }
}
