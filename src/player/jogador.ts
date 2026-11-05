import {
  CharacterSupportedState, PhysicsCharacterController, PhysicsShapeCapsule, Vector3, type Scene,
} from "@babylonjs/core";
import { diferencaAngulo } from "../camera/cameraTerceiraPessoa";
import { CFG } from "../config";
import type { Entrada } from "../core/entrada";
import type { Personagem } from "../core/personagem";

export interface Escada {
  x: number;
  z?: number;
  y0: number;
  y1: number;
  tipo: "escada" | "corda";
  /** Direção para onde o jogador olha ao subir, em graus (0 = +Z, 90 = +X). */
  yaw?: number;
}

export type EstadoJogador = "chao" | "ar" | "escada" | "travado" | "morto";

const M = CFG.movimento;
const RAD = Math.PI / 180;
const BAIXO = new Vector3(0, -1, 0);
const V_PULO = Math.sqrt(2 * Math.abs(M.gravidade) * M.alturaPulo);
const V_PULO_MIN = Math.sqrt(2 * Math.abs(M.gravidade) * M.alturaPuloMinima);

interface EntradaQuadro {
  direcao: Vector3; // no chão, magnitude 0..1
  correr: boolean;
  agachar: boolean;
  pulou: boolean;
  soltouPulo: boolean;
  subir: number; // escada: -1, 0, 1
}

/**
 * Controle em terceira pessoa (seção 3.3 da revisão 2) sobre o PhysicsCharacterController do Havok.
 * A entrada é lida no início do quadro; a física roda em passo fixo (1/60 s) e o modelo é
 * interpolado entre os dois últimos passos, para não tremer em telas de taxa variável.
 * Ações novas (combate no futuro) entram como estados extras, sem mexer na câmera.
 */
export class Jogador {
  readonly controlador: PhysicsCharacterController;
  estado: EstadoJogador = "chao";
  agachado = false;
  correndo = false;
  /** Para onde o personagem olha (radianos; 0 = +Z). */
  yaw = 0;
  private yawAnterior = 0;
  private inclinacao = 0;
  private vel = new Vector3();
  private gravidade = new Vector3(0, M.gravidade, 0);
  private tempoNoAr = 0;
  private bufferPulo = 0;
  private escadaAtual: Escada | null = null;
  private altura: number = M.alturaCapsula;
  private menorVy = 0;
  /** Pés no último chão firme pisado: destino quando o personagem cai para fora do mapa. */
  private readonly ultimoChaoSeguro = new Vector3();
  private apice = 0;
  private acumulado = 0;
  private posAnterior = new Vector3();
  private posAtual = new Vector3();
  private acaoUnica: { nome: string; ate: number } | null = null;
  private relogio = 0;
  private faseDoPasso = 0;
  escadas: Escada[] = [];
  /** Eixos da câmera no chão (definidos pelo jogo a cada quadro). */
  eixos: () => { frente: Vector3; direita: Vector3 } = () => ({ frente: new Vector3(0, 0, 1), direita: new Vector3(1, 0, 0) });
  /** Testes: direção de movimento fixa no mundo, ignorando a câmera. */
  direcaoForcada: Vector3 | null = null;
  /** Empurrão externo (vento da tempestade), em m/s no eixo X. */
  empurrao = 0;
  fatorVelocidade = 1;
  aoCairForte: ((vy: number) => void) | null = null;
  aoPular: (() => void) | null = null;
  aoPisar: (() => void) | null = null;
  /** Quadro (contador) em que o personagem começou a se mover, para o teste de resposta. */
  quadro = 0;

  constructor(private cena: Scene, readonly personagem: Personagem, private entrada: Entrada, x: number, y: number, z = 0) {
    this.controlador = new PhysicsCharacterController(
      new Vector3(x, y + this.altura / 2, z),
      { capsuleHeight: this.altura, capsuleRadius: M.raioCapsula },
      cena,
    );
    this.controlador.maxSlopeCosine = Math.cos(M.rampaMaximaGraus * RAD);
    // A subida de degrau embutida no controlador (maxStepHeight) só funciona quando o avanço de um
    // passo de física passa de uns 0,13 m (cerca de 8 m/s a 60 Hz): a cápsula pousa na quina e a
    // normal sai inclinada demais. Por isso ela fica desligada e o degrau é tratado em subirDegrau().
    this.controlador.maxStepHeight = 0;
    personagem.controleExterno = true;
    this.posAtual.copyFrom(this.controlador.getPosition());
    this.posAnterior.copyFrom(this.posAtual);
    this.posicionarModelo(1);
  }

  /** Posição dos pés (interpolada, a mesma do modelo). */
  get pes(): Vector3 {
    return this.personagem.raiz.position.add(new Vector3(0, 0.01, 0));
  }

  get velocidade(): Vector3 {
    return this.vel;
  }

  teleportar(x: number, y: number, z = 0, yaw?: number): void {
    this.moverPara(new Vector3(x, y + this.altura / 2, z));
    this.controlador.setVelocity(Vector3.Zero());
    this.vel.setAll(0);
    this.estado = "chao";
    this.escadaAtual = null;
    if (yaw !== undefined) this.yaw = this.yawAnterior = yaw;
    this.posAtual.copyFrom(this.controlador.getPosition());
    this.posAnterior.copyFrom(this.posAtual);
    this.acumulado = 0;
    this.menorVy = 0;
    this.ultimoChaoSeguro.set(x, y, z);
    this.posicionarModelo(1);
  }

  /** Volta ao último ponto de chão firme (queda para fora do mapa). */
  voltarAoChaoSeguro(): void {
    const c = this.ultimoChaoSeguro;
    this.teleportar(c.x, c.y + 0.05, c.z);
  }

  travar(travar: boolean): void {
    if (travar) {
      this.estado = "travado";
      this.vel.x = this.vel.z = 0;
    } else if (this.estado === "travado") {
      this.estado = "ar";
    }
  }

  /**
   * Reposiciona o controlador e recalcula os contatos. O setPosition do Babylon só troca a posição;
   * os contatos antigos continuariam valendo e podem sustentar o personagem no ar. A subida de
   * degrau interna do controlador faz o mesmo refresh depois de mover (método interno, conferido
   * na versão 9.33.1).
   */
  private moverPara(pos: Vector3): void {
    this.controlador.setPosition(pos);
    const c = this.controlador as unknown as { _refreshManifoldAtPosition?: (p: Vector3) => void };
    c._refreshManifoldAtPosition?.call(this.controlador, pos);
  }

  /** Teto baixo (definido pelo jogo a partir dos sólidos da área). */
  tetoAcima: (x: number, y: number, z: number) => boolean = () => false;

  // ------------------------------------------------------------------ entrada

  private lerEntrada(): EntradaQuadro {
    const e = this.entrada;
    let direcao: Vector3;
    if (this.direcaoForcada) direcao = this.direcaoForcada.clone();
    else {
      const { frente, direita } = this.eixos();
      direcao = frente.scale(e.eixoY).add(direita.scale(e.eixoX));
      if (direcao.length() > 1) direcao.normalize();
    }
    const mag = direcao.length();
    return {
      direcao,
      correr: e.segurando("correr") || (e.usandoGamepad && mag > 0.95),
      agachar: e.segurando("agachar"),
      pulou: e.apertou("pular"),
      soltouPulo: e.soltou("pular"),
      subir: e.segurando("cima") ? 1 : e.segurando("baixo") ? -1 : 0,
    };
  }

  // ------------------------------------------------------------------ quadro

  atualizar(dt: number): void {
    if (dt <= 0) return;
    this.quadro++;
    this.relogio += dt;
    const ent = this.lerEntrada();
    if (ent.pulou) this.bufferPulo = M.bufferPulo;
    this.acumulado += Math.min(dt, M.passoFisica * M.maxPassosPorQuadro);
    let primeiro = true;
    let passos = 0;
    while (this.acumulado >= M.passoFisica - 1e-6 && passos < M.maxPassosPorQuadro) {
      this.posAnterior.copyFrom(this.posAtual);
      this.yawAnterior = this.yaw;
      this.passoFixo(M.passoFisica, ent, primeiro);
      this.posAtual.copyFrom(this.controlador.getPosition());
      this.acumulado -= M.passoFisica;
      const chao = this.estado === "chao" ? this.chaoAbaixo() : null;
      const alvoFolga = chao === null ? 0 : Math.max(0, Math.min(0.2, this.posAtual.y - this.altura / 2 - chao));
      this.folgaChao += (alvoFolga - this.folgaChao) * 0.5;
      primeiro = false;
      passos++;
    }
    this.posicionarModelo(this.acumulado / M.passoFisica);
    this.animar(dt);
  }

  private passoFixo(h: number, ent: EntradaQuadro, primeiro: boolean): void {
    if (this.estado === "morto" || this.estado === "travado") {
      this.vel.x = this.vel.z = 0;
      this.integrar(h, this.controlador.checkSupport(h, BAIXO), true);
      return;
    }
    if (this.estado === "escada") {
      this.passoEscada(h, ent, primeiro);
      return;
    }
    const suporte = this.controlador.checkSupport(h, BAIXO);
    const noChao = suporte.supportedState === CharacterSupportedState.SUPPORTED;
    if (noChao) this.tempoNoAr = 0;
    else this.tempoNoAr += h;

    // agachar
    if (ent.agachar !== this.agachado && this.definirAltura(ent.agachar ? M.alturaAgachado : M.alturaCapsula)) {
      this.agachado = ent.agachar;
    }

    // velocidade horizontal desejada
    const mag = ent.direcao.length();
    this.correndo = ent.correr && !this.agachado && mag > 0.1;
    const vmax = (this.agachado ? M.agachado : this.correndo ? M.correr : M.andar * Math.min(1, mag / 0.7)) * this.fatorVelocidade;
    const dirN = mag > 0.01 ? ent.direcao.scale(1 / mag) : Vector3.Zero();
    const pesado = this.acaoUnica?.nome === "aterrissar_pesado" && this.relogio < this.acaoUnica.ate;
    const alvo = dirN.scale(mag > 0.01 && !pesado ? vmax : 0);
    alvo.x += this.empurrao;
    const atual = new Vector3(this.vel.x, 0, this.vel.z);
    const dif = alvo.subtract(atual);
    const acelerando = alvo.length() >= atual.length();
    let taxa = acelerando ? M.correr / M.tempoAteMaxima : M.correr / M.tempoAteParar;
    if (!noChao && this.tempoNoAr > M.tempoCoiote) taxa *= M.controleNoAr;
    const passoV = taxa * h;
    const novo = dif.length() <= passoV ? alvo : atual.add(dif.normalize().scale(passoV));
    this.vel.x = novo.x;
    this.vel.z = novo.z;

    // giro do personagem até a direção do movimento
    if (mag > 0.1) {
      const desejado = Math.atan2(dirN.x, dirN.z);
      const erro = diferencaAngulo(desejado, this.yaw);
      const velH = Math.hypot(this.vel.x, this.vel.z);
      if (Math.abs(erro) > M.giroRapidoGraus * RAD && velH > 1.5 && noChao) {
        this.iniciarAcao("giro_rapido", 0.3);
        this.vel.x *= 0.35;
        this.vel.z *= 0.35;
      }
      const maxPasso = M.giroMaximoGrausPorSegundo * RAD * h * (this.acaoUnica?.nome === "giro_rapido" ? 2 : 1);
      const suave = erro * (1 - Math.exp(-M.suavizacaoGiro * h));
      this.yaw += Math.sign(suave) * Math.min(Math.abs(suave), maxPasso);
    }

    // pulo com tolerância de borda e buffer
    if (primeiro) this.bufferPulo = Math.max(0, this.bufferPulo - h);
    const podePular = (noChao || this.tempoNoAr < M.tempoCoiote) && this.estado !== "ar";
    if (this.bufferPulo > 0 && podePular && !this.agachado) {
      this.vel.y = V_PULO;
      this.bufferPulo = 0;
      this.estado = "ar";
      this.tempoNoAr = M.tempoCoiote;
      this.apice = this.posAtual.y;
      this.aoPular?.();
    } else if (noChao && this.vel.y <= 0.01) {
      if (this.estado === "ar") this.aterrissar();
      this.estado = "chao";
      if (suporte.averageSurfaceNormal.y > 0.9) {
        this.ultimoChaoSeguro.set(this.posAtual.x, this.posAtual.y - this.altura / 2, this.posAtual.z);
      }
      this.menorVy = 0;
      // O apoio é detectado até ~0,1 m acima da superfície; uma velocidade para baixo leva a cápsula
      // até a folga de contato (sem pairar) e a mantém colada em rampas e na descida de degraus.
      this.vel.y = -M.colarNoChao;
    } else {
      if (this.estado === "chao" && !noChao && this.tempoNoAr > M.tempoCoiote) {
        this.estado = "ar";
        this.apice = this.posAtual.y;
      }
      this.vel.y = Math.max(-M.velocidadeMaxQueda, this.vel.y + M.gravidade * h);
      if (primeiro && ent.soltouPulo && this.vel.y > V_PULO_MIN) this.vel.y = V_PULO_MIN;
      this.menorVy = Math.min(this.menorVy, this.vel.y);
      this.apice = Math.max(this.apice, this.posAtual.y);
    }
    this.integrar(h, suporte, false, noChao && this.estado === "chao" ? suporte.averageSurfaceNormal : null);
  }

  private aterrissar(): void {
    const queda = this.apice - this.posAtual.y;
    if (this.menorVy < -M.velocidadeQuedaDano) this.aoCairForte?.(-this.menorVy);
    if (queda > M.quedaPesada) this.iniciarAcao("aterrissar_pesado", 0.55);
    else if (queda > 0.6) this.iniciarAcao("aterrissar_leve", 0.25);
    this.aoPisar?.();
  }

  private iniciarAcao(nome: string, duracao: number): void {
    this.acaoUnica = { nome, ate: this.relogio + duracao };
    this.personagem.tocar(nome, { loop: false, transicao: 0.08 });
  }

  /** Deslocamento visual que some aos poucos depois de subir um degrau (evita o tranco). */
  private degrauVisual = 0;
  /** Diferença entre a base da cápsula e o chão real (o controlador mantém uma folga das superfícies). */
  private folgaChao = 0;

  /** Altura do chão logo abaixo do personagem (raycast), ou null se não houver chão perto. */
  private chaoAbaixo(): number | null {
    const motor = this.cena.getPhysicsEngine();
    if (!motor) return null;
    const p = this.controlador.getPosition();
    const base = p.y - this.altura / 2;
    const r = motor.raycast(new Vector3(p.x, base + 0.3, p.z), new Vector3(p.x, base - 0.4, p.z));
    return r.hasHit ? r.hitPointWorld.y : null;
  }

  /**
   * Subida de degrau: com o personagem no chão e barrado na horizontal, um raio vertical logo à
   * frente procura um topo plano até `degrauMaximo`; se houver espaço para a cápsula, sobe.
   */
  private subirDegrau(pedidaX: number, pedidaZ: number): void {
    const pedida = Math.hypot(pedidaX, pedidaZ);
    if (pedida < 0.3 || this.estado !== "chao") return;
    const v = this.controlador.getVelocity();
    if (Math.hypot(v.x, v.z) > pedida * 0.6) return;
    const motor = this.cena.getPhysicsEngine();
    if (!motor) return;
    const dir = new Vector3(pedidaX / pedida, 0, pedidaZ / pedida);
    const p = this.controlador.getPosition();
    const pe = this.chaoAbaixo() ?? p.y - this.altura / 2;
    for (const alcance of [M.raioCapsula + 0.1, M.raioCapsula + 0.22]) {
      const topo = new Vector3(p.x + dir.x * alcance, pe + M.degrauMaximo + 0.05, p.z + dir.z * alcance);
      const r = motor.raycast(topo, new Vector3(topo.x, pe - 0.02, topo.z));
      if (!r.hasHit) continue;
      const altura = r.hitPointWorld.y - pe;
      // degrau tem topo plano; rampas (normal inclinada) ficam com o controlador
      if (altura < 0.03 || altura > M.degrauMaximo || r.hitNormalWorld.y < 0.97) return;
      // espaço livre para o corpo acima do degrau
      const cabeca = new Vector3(p.x, pe + altura + this.altura - 0.05, p.z);
      const livre = motor.raycast(new Vector3(p.x, p.y, p.z), cabeca);
      const frente = motor.raycast(new Vector3(p.x, pe + altura + 0.3, p.z), new Vector3(topo.x + dir.x * 0.1, pe + altura + 0.3, topo.z + dir.z * 0.1));
      if (livre.hasHit || frente.hasHit) return;
      this.moverPara(new Vector3(p.x + dir.x * 0.08, pe + altura + this.altura / 2 + 0.06, p.z + dir.z * 0.08));
      this.degrauVisual -= altura;
      return;
    }
  }

  private integrar(h: number, suporte: ReturnType<PhysicsCharacterController["checkSupport"]>, soGravidade: boolean,
    normalChao: Vector3 | null = null): void {
    if (soGravidade) {
      const noChao = suporte.supportedState === CharacterSupportedState.SUPPORTED;
      this.vel.y = noChao ? -M.colarNoChao : Math.max(-M.velocidadeMaxQueda, this.vel.y + M.gravidade * h);
    }
    let pedida = this.vel.clone();
    if (normalChao && normalChao.y > 0.3) {
      // No chão: o movimento segue o plano da superfície (mesma velocidade horizontal em rampas)
      // e a força que mantém o contato vai contra a normal, sem frear a subida.
      const n = normalChao.normalizeToNew();
      const horiz = new Vector3(this.vel.x, 0, this.vel.z);
      const tang = horiz.subtract(n.scale(Vector3.Dot(horiz, n)));
      const th = Math.hypot(tang.x, tang.z);
      if (th > 1e-4) tang.scaleInPlace(horiz.length() / th);
      pedida = tang.subtract(n.scale(M.colarNoChao * 0.3));
    }
    this.controlador.setVelocity(pedida);
    this.controlador.integrate(h, suporte, this.gravidade);
    if (!soGravidade) this.subirDegrau(this.vel.x, this.vel.z);
    const v = this.controlador.getVelocity();
    // Bateu a cabeça: corta a subida. Na horizontal a velocidade pedida é mantida; o controlador
    // desliza na parede e precisa dela para a rotina de subir degraus funcionar.
    if (this.vel.y > 0 && v.y < this.vel.y * 0.5) this.vel.y = Math.max(0, v.y);
  }

  private definirAltura(nova: number): boolean {
    if (Math.abs(nova - this.altura) < 0.01) return true;
    const p = this.controlador.getPosition();
    if (nova > this.altura && this.tetoAcima(p.x, p.y - this.altura / 2 + nova, p.z)) return false;
    const r = M.raioCapsula;
    const pesY = p.y - this.altura / 2;
    this.controlador.shape = new PhysicsShapeCapsule(new Vector3(0, -nova / 2 + r, 0), new Vector3(0, nova / 2 - r, 0), r, this.cena);
    this.altura = nova;
    this.moverPara(new Vector3(p.x, pesY + nova / 2, p.z));
    return true;
  }

  // ------------------------------------------------------------------ escadas e cordas

  /** Pontos de encaixe de uma escada: embaixo e em cima. */
  static pontosEscada(esc: Escada): { base: Vector3; topo: Vector3; frente: Vector3 } {
    const yaw = ((esc.yaw ?? 0) * Math.PI) / 180;
    const frente = new Vector3(Math.sin(yaw), 0, Math.cos(yaw));
    const centro = new Vector3(esc.x, 0, esc.z ?? 0);
    const recuo = esc.tipo === "corda" ? 0.32 : 0.38;
    const base = centro.subtract(frente.scale(recuo));
    base.y = esc.y0;
    const topo = centro.add(frente.scale(esc.tipo === "corda" ? 0.9 : 0.55));
    topo.y = esc.y1;
    return { base, topo, frente };
  }

  /** Encaixa na escada ou corda (chamado ao apertar interagir perto dela). */
  entrarEscada(esc: Escada, deCima = false): void {
    if (this.estado === "escada" || this.estado === "morto" || this.estado === "travado") return;
    if (this.agachado && this.definirAltura(M.alturaCapsula)) this.agachado = false;
    const { base, frente } = Jogador.pontosEscada(esc);
    this.estado = "escada";
    this.escadaAtual = esc;
    this.vel.setAll(0);
    this.yaw = Math.atan2(frente.x, frente.z);
    const y = deCima ? esc.y1 - 1.2 : Math.max(esc.y0, Math.min(esc.y1 - 0.5, this.pes.y));
    this.moverPara(new Vector3(base.x, y + this.altura / 2, base.z));
  }

  private passoEscada(h: number, ent: EntradaQuadro, primeiro: boolean): void {
    const esc = this.escadaAtual!;
    const { base, topo, frente } = Jogador.pontosEscada(esc);
    const p = this.controlador.getPosition();
    let pesY = p.y - this.altura / 2;
    const vel = esc.tipo === "corda" ? M.velocidadeCorda : M.velocidadeEscada;
    this.vel.set(0, ent.subir * vel, 0);
    pesY += this.vel.y * h;
    if (primeiro && this.bufferPulo > 0) {
      // solta para trás
      this.bufferPulo = 0;
      this.sairEscada();
      this.vel.copyFrom(frente.scale(-2.5));
      this.vel.y = V_PULO * 0.6;
      this.estado = "ar";
      this.apice = pesY;
      return;
    }
    if (pesY >= esc.y1 && ent.subir > 0) {
      this.sairEscada();
      this.moverPara(new Vector3(topo.x, esc.y1 + 0.05 + this.altura / 2, topo.z));
      this.controlador.setVelocity(Vector3.Zero());
      return;
    }
    if (pesY <= esc.y0 && ent.subir < 0) {
      this.sairEscada();
      pesY = esc.y0;
    }
    this.moverPara(new Vector3(base.x, pesY + this.altura / 2, base.z));
    this.controlador.setVelocity(Vector3.Zero());
  }

  private sairEscada(): void {
    this.escadaAtual = null;
    this.estado = "chao";
  }

  get naEscada(): Escada | null {
    return this.escadaAtual;
  }

  // ------------------------------------------------------------------ modelo e animação

  private posicionarModelo(t: number): void {
    const p = Vector3.Lerp(this.posAnterior, this.posAtual, Math.max(0, Math.min(1, t)));
    this.personagem.raiz.position.set(p.x, p.y - this.altura / 2 - 0.01 - this.folgaChao + this.degrauVisual, p.z);
    const yaw = this.yawAnterior + diferencaAngulo(this.yaw, this.yawAnterior) * t;
    this.personagem.definirGiro(yaw, this.inclinacao);
  }

  private animar(dt: number): void {
    const per = this.personagem;
    this.degrauVisual *= Math.exp(-dt * 18);
    const velH = Math.hypot(this.vel.x, this.vel.z);
    // inclinação nas curvas: proporcional à velocidade angular e à velocidade
    const giro = diferencaAngulo(this.yaw, this.yawAnterior) / M.passoFisica;
    const alvoInc = this.estado === "chao" ? Math.max(-1, Math.min(1, -giro * 0.12)) * M.inclinacaoCurvaGraus * RAD * Math.min(1, velH / M.correr) : 0;
    this.inclinacao += (alvoInc - this.inclinacao) * Math.min(1, dt * 8);
    per.atualizar(dt);
    if (this.estado === "morto") return;
    if (this.estado === "escada") {
      const nome = this.escadaAtual?.tipo === "corda" ? "corda" : "escada";
      per.tocar(nome, { velocidade: this.vel.y === 0 ? 0.0001 : Math.sign(this.vel.y), transicao: 0.15 });
      return;
    }
    if (this.acaoUnica && this.relogio < this.acaoUnica.ate) return;
    this.acaoUnica = null;
    if (this.estado === "ar") {
      per.tocar("pular", { transicao: 0.15 });
      return;
    }
    if (this.agachado) {
      per.tocar(velH > 0.2 ? "agachar_andar" : "agachar", { velocidade: velH > 0.2 ? velH / M.agachado : 1, transicao: 0.18 });
      return;
    }
    per.locomover(velH, M.velocidadeReferenciaAndar, M.velocidadeReferenciaCorrer, M.andar, 0.18);
    if (velH > 0.3) {
      const passada = velH > M.andar + 0.5 ? 1.15 : 0.7;
      this.faseDoPasso += (velH * dt) / passada;
      if (this.faseDoPasso >= 1) {
        this.faseDoPasso -= 1;
        this.aoPisar?.();
      }
    }
  }
}
