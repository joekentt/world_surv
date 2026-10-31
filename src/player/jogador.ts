import {
  CharacterSupportedState, PhysicsCharacterController, PhysicsShapeCapsule, Vector3, type Scene,
} from "@babylonjs/core";
import { CFG } from "../config";
import type { Entrada } from "../core/entrada";
import type { Personagem } from "../core/personagem";

export interface Escada {
  x: number;
  y0: number;
  y1: number;
  tipo: "escada" | "corda";
}

export type EstadoJogador = "chao" | "ar" | "escada" | "travado" | "morto";

const M = CFG.movimento;
const BAIXO = new Vector3(0, -1, 0);

/**
 * Controle 2,5D do subidor: anda no eixo X, pula, corre, agacha e sobe escadas e cordas.
 * A colisão usa o PhysicsCharacterController do Havok; Z fica travado em 0.
 * Nada aqui impede incluir combate depois: ações novas entram como estados extras.
 */
export class Jogador {
  readonly controlador: PhysicsCharacterController;
  estado: EstadoJogador = "chao";
  agachado = false;
  correndo = false;
  private vel = new Vector3();
  private gravidade = new Vector3(0, M.gravidade, 0);
  private tempoNoAr = 0;
  private bufferPulo = 0;
  private escadaAtual: Escada | null = null;
  private altura = M.alturaCapsula;
  private menorVy = 0;
  escadas: Escada[] = [];
  /** Empurrão externo (vento da tempestade), em m/s no eixo X. */
  empurrao = 0;
  /** Multiplicador de velocidade (mochila pesada etc.). */
  fatorVelocidade = 1;
  /** Disparado ao tocar o chão depois de uma queda forte, com a velocidade de impacto. */
  aoCairForte: ((vy: number) => void) | null = null;
  aoPular: (() => void) | null = null;
  aoPisar: (() => void) | null = null;
  private faseDoPasso = 0;

  constructor(private cena: Scene, readonly personagem: Personagem, private entrada: Entrada, x: number, y: number) {
    this.controlador = new PhysicsCharacterController(
      new Vector3(x, y + this.altura / 2, 0),
      { capsuleHeight: this.altura, capsuleRadius: M.raioCapsula },
      cena,
    );
    this.controlador.maxSlopeCosine = Math.cos((50 * Math.PI) / 180);
    this.controlador.maxStepHeight = 0.32;
    this.posicionarModelo();
  }

  /** Posição dos pés. */
  get pes(): Vector3 {
    const p = this.controlador.getPosition();
    return new Vector3(p.x, p.y - this.altura / 2, 0);
  }

  get velocidade(): Vector3 {
    return this.vel;
  }

  teleportar(x: number, y: number): void {
    this.controlador.setPosition(new Vector3(x, y + this.altura / 2, 0));
    this.controlador.setVelocity(Vector3.Zero());
    this.vel.setAll(0);
    this.estado = "chao";
    this.escadaAtual = null;
    this.personagem.anguloForcado = null;
    this.posicionarModelo();
  }

  travar(travar: boolean): void {
    if (travar) {
      this.estado = "travado";
      this.vel.x = 0;
    } else if (this.estado === "travado") {
      this.estado = "ar";
    }
  }

  private definirAltura(nova: number): boolean {
    if (Math.abs(nova - this.altura) < 0.01) return true;
    const r = M.raioCapsula;
    // Ao levantar, confere se há espaço acima (teto baixo mantém agachado).
    if (nova > this.altura) {
      const p = this.controlador.getPosition();
      if (this.tetoAcima(p.x, p.y - this.altura / 2 + nova)) return false;
    }
    const p = this.controlador.getPosition();
    const pesY = p.y - this.altura / 2;
    this.controlador.shape = new PhysicsShapeCapsule(
      new Vector3(0, -nova / 2 + r, 0), new Vector3(0, nova / 2 - r, 0), r, this.cena,
    );
    this.altura = nova;
    this.controlador.setPosition(new Vector3(p.x, pesY + nova / 2, 0));
    return true;
  }

  /** Verificação simples de teto usando os sólidos registrados pelo construtor de áreas. */
  tetoAcima: (x: number, y: number) => boolean = () => false;

  atualizar(dt: number): void {
    if (dt <= 0) return;
    dt = Math.min(dt, 1 / 20);
    const e = this.entrada;
    const p = this.controlador.getPosition();
    if (this.estado === "morto" || this.estado === "travado") {
      this.vel.x = 0;
      this.integrarFisica(dt, true);
      this.animar(dt);
      return;
    }

    if (this.estado === "escada") {
      this.atualizarEscada(dt);
      this.animar(dt);
      return;
    }

    const suporte = this.controlador.checkSupport(dt, BAIXO);
    const noChao = suporte.supportedState === CharacterSupportedState.SUPPORTED;
    if (noChao) this.tempoNoAr = 0;
    else this.tempoNoAr += dt;

    // agachar (segurar)
    const querAgachar = e.segurando("agachar") || (noChao && e.segurando("baixo") && !this.escadaPerto(p, -1));
    if (querAgachar !== this.agachado) {
      if (this.definirAltura(querAgachar ? M.alturaAgachado : M.alturaCapsula)) this.agachado = querAgachar;
    }

    // horizontal
    const eixo = Math.abs(e.eixoX) > 0.2 ? e.eixoX : 0;
    this.correndo = e.segurando("correr") && !this.agachado && eixo !== 0;
    const vmax = (this.agachado ? M.agachado : this.correndo ? M.correr : M.andar) * this.fatorVelocidade;
    const alvo = eixo * vmax + this.empurrao;
    const acel = noChao ? (eixo === 0 ? M.frenagemChao : M.aceleracaoChao) : M.aceleracaoAr;
    const dif = alvo - this.vel.x;
    this.vel.x += Math.sign(dif) * Math.min(Math.abs(dif), acel * dt);
    if (eixo !== 0) this.personagem.virar(eixo);

    // pulo com tempo de coiote e buffer
    if (e.apertou("pular")) this.bufferPulo = M.bufferPulo;
    else this.bufferPulo = Math.max(0, this.bufferPulo - dt);
    const podePular = (noChao || this.tempoNoAr < M.tempoCoiote) && this.estado !== "ar";
    if (this.bufferPulo > 0 && podePular && !this.agachado) {
      this.vel.y = M.velocidadePulo;
      this.bufferPulo = 0;
      this.estado = "ar";
      this.tempoNoAr = M.tempoCoiote;
      this.aoPular?.();
    } else if (noChao && this.vel.y <= 0.01) {
      if (this.estado === "ar" && this.menorVy < -M.velocidadeQuedaDano) this.aoCairForte?.(-this.menorVy);
      if (this.estado === "ar") this.aoPisar?.();
      this.estado = "chao";
      this.menorVy = 0;
      this.vel.y = 0;
    } else {
      if (this.estado === "chao" && !noChao && this.tempoNoAr > M.tempoCoiote) this.estado = "ar";
      this.vel.y = Math.max(-M.velocidadeMaxQueda, this.vel.y + M.gravidade * dt);
      if (e.soltou("pular") && this.vel.y > 0) this.vel.y *= M.corteDoPulo;
      this.menorVy = Math.min(this.menorVy, this.vel.y);
    }

    // entrar em escada ou corda
    if (e.segurando("cima") || (e.segurando("baixo") && noChao)) {
      const esc = this.escadaPerto(p, e.segurando("cima") ? 1 : -1);
      if (esc) {
        this.entrarEscada(esc);
        this.animar(dt);
        return;
      }
    }

    this.integrarFisica(dt, false, suporte);
    this.animar(dt);
  }

  private integrarFisica(dt: number, soGravidade: boolean, suporte = this.controlador.checkSupport(dt, BAIXO)): void {
    if (soGravidade) {
      const noChao = suporte.supportedState === CharacterSupportedState.SUPPORTED;
      this.vel.y = noChao ? 0 : Math.max(-M.velocidadeMaxQueda, this.vel.y + M.gravidade * dt);
    }
    this.controlador.setVelocity(new Vector3(this.vel.x, this.vel.y, 0));
    this.controlador.integrate(dt, suporte, this.gravidade);
    const v = this.controlador.getVelocity();
    // bateu a cabeça ou parede: a física corrige a velocidade
    if (this.vel.y > 0 && v.y < this.vel.y * 0.5) this.vel.y = Math.min(this.vel.y, Math.max(0, v.y));
    if (Math.abs(v.x) < Math.abs(this.vel.x) * 0.3) this.vel.x = v.x;
    const p = this.controlador.getPosition();
    if (Math.abs(p.z) > 0.001) this.controlador.setPosition(new Vector3(p.x, p.y, 0));
    this.posicionarModelo();
  }

  private escadaPerto(p: Vector3, direcao: number): Escada | null {
    const pesY = p.y - this.altura / 2;
    for (const esc of this.escadas) {
      if (Math.abs(p.x - esc.x) > 0.55) continue;
      if (direcao > 0 && pesY >= esc.y0 - 0.3 && pesY < esc.y1 - 0.15) return esc;
      if (direcao < 0 && pesY > esc.y0 + 0.2 && pesY <= esc.y1 + 0.3) return esc;
    }
    return null;
  }

  private entrarEscada(esc: Escada): void {
    if (this.agachado) {
      this.definirAltura(M.alturaCapsula);
      this.agachado = false;
    }
    this.estado = "escada";
    this.escadaAtual = esc;
    this.vel.setAll(0);
    this.personagem.anguloForcado = 0; // de costas para a câmera
  }

  private atualizarEscada(dt: number): void {
    const esc = this.escadaAtual!;
    const e = this.entrada;
    const p = this.controlador.getPosition();
    let pesY = p.y - this.altura / 2;
    const sobe = e.segurando("cima") ? 1 : e.segurando("baixo") ? -1 : 0;
    this.vel.y = sobe * M.velocidadeEscada;
    pesY += this.vel.y * dt;
    const x = p.x + (esc.x - p.x) * Math.min(1, dt * 14);
    if (e.apertou("pular")) {
      this.sairEscada();
      const dir = Math.abs(e.eixoX) > 0.2 ? Math.sign(e.eixoX) : 0;
      this.vel.set(dir * M.andar, M.velocidadePulo * 0.75, 0);
      this.estado = "ar";
    } else if (pesY >= esc.y1 && sobe > 0) {
      pesY = esc.y1 + 0.02;
      this.sairEscada();
      this.estado = "chao";
    } else if (pesY <= esc.y0 && sobe < 0) {
      pesY = esc.y0;
      this.sairEscada();
      this.estado = "chao";
    }
    this.controlador.setPosition(new Vector3(x, pesY + this.altura / 2, 0));
    this.controlador.setVelocity(Vector3.Zero());
    this.posicionarModelo();
  }

  private sairEscada(): void {
    this.escadaAtual = null;
    this.personagem.anguloForcado = null;
    this.estado = "chao";
  }

  private posicionarModelo(): void {
    const p = this.controlador.getPosition();
    this.personagem.raiz.position.set(p.x, p.y - this.altura / 2 - 0.01, 0);
  }

  private animar(dt: number): void {
    const per = this.personagem;
    per.atualizar(dt);
    if (this.estado === "morto") return;
    if (this.estado === "escada") {
      per.tocar("escada", { velocidade: this.vel.y === 0 ? 0.0001 : Math.sign(this.vel.y), transicao: 0.15 });
      return;
    }
    if (this.estado === "ar") {
      per.tocar("pular", { transicao: 0.12 });
      return;
    }
    const v = Math.abs(this.vel.x);
    if (this.agachado) {
      per.tocar(v > 0.2 ? "agachar_andar" : "agachar", { velocidade: v > 0.2 ? v / M.agachado : 1, transicao: 0.18 });
    } else if (v > M.andar + 0.4) {
      per.tocar("correr", { velocidade: v / M.correr, transicao: 0.18 });
      this.contarPassos(dt, v, 0.36);
    } else if (v > 0.25) {
      per.tocar("andar", { velocidade: Math.max(0.5, v / M.andar), transicao: 0.2 });
      this.contarPassos(dt, v, 0.75);
    } else {
      per.tocar("parado", { transicao: 0.25 });
    }
  }

  private contarPassos(dt: number, v: number, passada: number): void {
    this.faseDoPasso += (v * dt) / passada;
    if (this.faseDoPasso >= 1) {
      this.faseDoPasso -= 1;
      this.aoPisar?.();
    }
  }
}
