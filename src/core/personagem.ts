import { TransformNode, type AbstractMesh, type AnimationGroup, type Scene } from "@babylonjs/core";
import { BibliotecaAnimacoes, type Carregador } from "./carregador";

export interface OpcoesTocar {
  loop?: boolean;
  velocidade?: number;
  transicao?: number;
}

/** Ângulo de frente: de lado, virado 25° para a câmera (que fica em -Z). */
const GIRO_CAMERA = 0.42;

/**
 * Personagem animado: instância de um GLB de public/assets/personagens com os grupos
 * de animação da biblioteca adaptados ao seu esqueleto. Usado pelo jogador e pelos NPCs.
 */
export class Personagem {
  readonly raiz: TransformNode;
  readonly malhas: AbstractMesh[] = [];
  private grupos = new Map<string, AnimationGroup>();
  private atual: string | null = null;
  private saindo: { g: AnimationGroup; w: number }[] = [];
  private entrada = 1;
  private duracaoTransicao = 0.2;
  private direcao = 1;
  private anguloAlvo = Math.PI / 2 + GIRO_CAMERA;
  /** Quando definido, substitui a orientação lateral (ex.: de costas na escada). */
  anguloForcado: number | null = null;
  pausado = false;

  private constructor(readonly id: string, raiz: TransformNode) {
    this.raiz = raiz;
  }

  static async criar(cena: Scene, carregador: Carregador, biblioteca: BibliotecaAnimacoes, id: string, nomeInstancia = id): Promise<Personagem> {
    const conteiner = await carregador.carregar(`personagens/${id}.glb`);
    const pivo = new TransformNode(nomeInstancia, cena);
    const p = new Personagem(id, pivo);
    const inst = conteiner.instantiateModelsToScene((n) => n, false, { doNotInstantiate: true });
    for (const g of inst.animationGroups) g.dispose();
    for (const n of inst.rootNodes) {
      n.parent = pivo;
      for (const m of (n as TransformNode).getChildMeshes(false)) {
        p.malhas.push(m);
        m.isPickable = false;
      }
    }
    const modelo = inst.rootNodes[0] as TransformNode;
    p.grupos = biblioteca.criarGrupos(cena, id, modelo, BibliotecaAnimacoes.repouso(conteiner));
    pivo.rotation.y = p.anguloAlvo;
    p.tocar("parado");
    return p;
  }

  get acaoAtual(): string | null {
    return this.atual;
  }

  tem(acao: string): boolean {
    return this.grupos.has(acao);
  }

  tocar(acao: string, op: OpcoesTocar = {}): void {
    const g = this.grupos.get(acao);
    if (!g) return;
    const velocidade = op.velocidade ?? 1;
    if (this.atual === acao) {
      g.speedRatio = velocidade;
      return;
    }
    const anterior = this.atual ? this.grupos.get(this.atual) : null;
    if (anterior) {
      this.saindo = this.saindo.filter((s) => s.g !== anterior && s.g !== g);
      this.saindo.push({ g: anterior, w: anterior.weight < 0 ? 1 : anterior.weight });
    }
    this.saindo = this.saindo.filter((s) => s.g !== g);
    this.atual = acao;
    this.duracaoTransicao = op.transicao ?? 0.2;
    this.entrada = this.duracaoTransicao > 0 && anterior ? 0 : 1;
    g.weight = this.entrada;
    g.start(op.loop ?? true, velocidade);
  }

  /** Direção lateral: 1 = direita (+X), -1 = esquerda. */
  virar(direcao: number): void {
    if (direcao === 0) return;
    this.direcao = Math.sign(direcao);
    this.anguloAlvo = this.direcao > 0 ? Math.PI / 2 + GIRO_CAMERA : -Math.PI / 2 - GIRO_CAMERA;
  }

  get lado(): number {
    return this.direcao;
  }

  atualizar(dt: number): void {
    const passo = this.duracaoTransicao > 0 ? dt / this.duracaoTransicao : 1;
    if (this.atual && this.entrada < 1) {
      this.entrada = Math.min(1, this.entrada + passo);
      const g = this.grupos.get(this.atual);
      if (g) g.weight = this.entrada;
    }
    for (const s of this.saindo) {
      s.w -= passo;
      if (s.w <= 0) s.g.stop();
      else s.g.weight = s.w;
    }
    this.saindo = this.saindo.filter((s) => s.w > 0);
    // giro suave
    const alvo = this.anguloForcado ?? this.anguloAlvo;
    let d = alvo - this.raiz.rotation.y;
    while (d > Math.PI) d -= Math.PI * 2;
    while (d < -Math.PI) d += Math.PI * 2;
    this.raiz.rotation.y += d * Math.min(1, dt * 12);
  }

  /** Pausa ou retoma todas as animações (NPCs fora da tela). */
  definirPausa(pausar: boolean): void {
    if (pausar === this.pausado) return;
    this.pausado = pausar;
    for (const g of this.grupos.values()) {
      if (!g.isStarted) continue;
      if (pausar) g.pause();
      else g.play(g.loopAnimation);
    }
  }

  mostrar(prefixo: string, visivel: boolean): void {
    for (const m of this.malhas) if (m.name.includes(prefixo)) m.setEnabled(visivel);
  }

  definirVisivel(v: boolean): void {
    this.raiz.setEnabled(v);
  }

  dispose(): void {
    for (const g of this.grupos.values()) g.dispose();
    this.raiz.dispose(false, false);
  }
}
