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
  /** O controlador do jogador define o giro diretamente (yaw e inclinação nas curvas). */
  controleExterno = false;
  private pesosLocomocao = { parado: 1, andar: 0, correr: 0 };
  /** Velocidade pedida e velocidade suavizada que comanda a mistura (a física não muda). */
  private loc = { alvo: 0, suave: 0, refAndar: 1, refCorrer: 1, vAndar: 1 };
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

  /**
   * Mistura de locomoção (seção 3.3): parado, andar e correr tocam juntos com pesos pela velocidade,
   * e a velocidade de reprodução acompanha a velocidade real para o pé não deslizar. Os pesos seguem
   * uma velocidade suavizada (partida, parada e troca andar/correr sem estalo) e andar e correr ficam
   * na mesma fase do passo, para os pés não se cruzarem durante a mistura.
   */
  locomover(velocidade: number, refAndar: number, refCorrer: number, vAndar: number, transicao = 0.18): void {
    const L = this.loc;
    L.alvo = Math.max(0, velocidade);
    L.refAndar = refAndar;
    L.refCorrer = refCorrer;
    L.vAndar = vAndar;
    if (this.atual === "locomocao") return;
    L.suave = L.alvo;
    this.empurrarParaSaida();
    this.atual = "locomocao";
    this.duracaoTransicao = transicao;
    this.entrada = 0;
    const ga = this.grupos.get("andar"), gc = this.grupos.get("correr"), gp = this.grupos.get("parado");
    for (const g of [gp, ga, gc]) {
      if (!g) continue;
      this.saindo = this.saindo.filter((s) => s.g !== g);
      g.weight = 0;
    }
    // andar e correr recomeçam juntos, no toque do pé esquerdo, para ficarem em fase
    for (const g of [ga, gc]) if (g?.isStarted) g.stop();
    this.atualizarLocomocao(0);
    for (const g of [gp, ga, gc]) if (g && !g.isPlaying) g.start(true, g.speedRatio);
    // correr segue a fase normalizada de andar (ciclos de durações diferentes, mesmo passo)
    const raiz = ga?.animatables[0];
    if (gc && raiz) gc.syncAllAnimationsWith(raiz);
  }

  /** Fase do passo (0 a 1, toque do pé esquerdo em 0 e do direito em 0,5); correr segue a fase de andar. */
  fasePasso(): number | null {
    if (this.atual !== "locomocao") return null;
    const { andar, correr } = this.pesosLocomocao;
    const g = this.grupos.get("andar");
    if (andar + correr < 0.3 || !g?.isPlaying) return null;
    const n = g.to - g.from;
    return n > 0 ? (((g.getCurrentFrame() - g.from) / n) % 1 + 1) % 1 : null;
  }

  private atualizarLocomocao(dt: number): void {
    const L = this.loc;
    // acelerar responde um pouco mais rápido que frear
    const tau = L.alvo > L.suave ? 0.08 : 0.11;
    L.suave += (L.alvo - L.suave) * (dt > 0 ? 1 - Math.exp(-dt / tau) : 1);
    const v = L.suave;
    let pp = 0, pa = 0, pc = 0;
    if (v <= L.vAndar) {
      const u = v / L.vAndar;
      pa = u * u * (3 - 2 * u);
      pp = 1 - pa;
    } else {
      const u = Math.min(1, (v - L.vAndar) / Math.max(0.01, L.refCorrer - L.vAndar));
      pc = u * u * (3 - 2 * u);
      pa = 1 - pc;
    }
    this.pesosLocomocao = { parado: pp, andar: pa, correr: pc };
    const ga = this.grupos.get("andar"), gc = this.grupos.get("correr");
    const ra = Math.min(1.8, Math.max(0.55, v / L.refAndar));
    const rc = Math.min(1.6, Math.max(0.6, v / L.refCorrer));
    if (!ga || !gc) {
      if (ga) ga.speedRatio = ra;
      if (gc) gc.speedRatio = rc;
      return;
    }
    // mesma frequência de passo para os dois ciclos, ponderada pelos pesos: andar dita o relógio e
    // correr acompanha a fase de andar (syncAllAnimationsWith em locomover)
    const ta = Math.max(1e-3, ga.to - ga.from), tc = Math.max(1e-3, gc.to - gc.from);
    const soma = Math.max(1e-3, pa + pc);
    const freq = (pa * (ra / ta) + pc * (rc / tc)) / soma || ra / ta;
    ga.speedRatio = freq * ta;
    gc.speedRatio = freq * tc;
  }

  private empurrarParaSaida(): void {
    if (!this.atual) return;
    const lista = this.atual === "locomocao" ? ["parado", "andar", "correr"] : [this.atual];
    for (const nome of lista) {
      const g = this.grupos.get(nome);
      if (!g) continue;
      this.saindo = this.saindo.filter((s) => s.g !== g);
      const w = g.weight < 0 ? 1 : g.weight;
      if (w > 0.001) this.saindo.push({ g, w });
      else g.stop();
    }
  }

  /** Alfa das malhas (câmera muito perto ou personagem entre a câmera e o jogador). */
  definirTransparencia(alfa: number): void {
    for (const m of this.malhas) if (Math.abs(m.visibility - alfa) > 0.01) m.visibility = alfa;
  }

  /** Giro e inclinação lateral definidos pelo controlador (radianos). */
  definirGiro(yaw: number, inclinacao = 0): void {
    this.raiz.rotation.y = yaw;
    this.raiz.rotation.z = inclinacao;
  }

  tocar(acao: string, op: OpcoesTocar = {}): void {
    const g = this.grupos.get(acao);
    if (!g) return;
    const vinhaDaLocomocao = this.atual === "locomocao";
    if (vinhaDaLocomocao) {
      this.empurrarParaSaida();
      this.atual = null;
    }
    const velocidade = op.velocidade ?? 1;
    if (this.atual === acao) {
      g.speedRatio = velocidade;
      return;
    }
    const anterior = this.atual ? this.grupos.get(this.atual) ?? null : null;
    if (anterior) {
      this.saindo = this.saindo.filter((s) => s.g !== anterior && s.g !== g);
      this.saindo.push({ g: anterior, w: anterior.weight < 0 ? 1 : anterior.weight });
    }
    this.saindo = this.saindo.filter((s) => s.g !== g);
    this.atual = acao;
    this.duracaoTransicao = op.transicao ?? 0.2;
    this.entrada = this.duracaoTransicao > 0 && (anterior || vinhaDaLocomocao) ? 0 : 1;
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
    if (this.atual === "locomocao") {
      this.atualizarLocomocao(dt);
      this.entrada = Math.min(1, this.entrada + passo);
      for (const nome of ["parado", "andar", "correr"] as const) {
        const g = this.grupos.get(nome);
        // peso zero pausa o grupo no Babylon: andar e correr ficam com um mínimo invisível para
        // continuarem correndo em fase e entrarem na mistura sem salto
        if (g) g.weight = Math.max(nome === "parado" ? 0 : 1e-3, this.pesosLocomocao[nome] * this.entrada);
      }
    } else if (this.atual && this.entrada < 1) {
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
    if (this.controleExterno) return;
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
