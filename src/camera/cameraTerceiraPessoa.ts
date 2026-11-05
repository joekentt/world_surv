import {
  Camera, FreeCamera, PhysicsShapeSphere, Quaternion, ShapeCastResult, Vector3,
  type HavokPlugin, type PhysicsBody, type Scene,
} from "@babylonjs/core";
import { CAMADA_SEM_CAMERA } from "../world/construtor";
import { CFG } from "../config";
import { carregarOpcoes, salvarOpcoes, type OpcoesCamera } from "./opcoes";

const C = CFG.camera;
const RAD = Math.PI / 180;

/** Diferença angular em (-π, π]. */
export function diferencaAngulo(a: number, b: number): number {
  let d = a - b;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d <= -Math.PI) d += Math.PI * 2;
  return d;
}

export interface ZonaCamera {
  tipo: keyof typeof C.zonas;
  min: [number, number, number];
  max: [number, number, number];
}

/** Algo que pode ficar translúcido quando está entre a câmera e o personagem (NPCs, objetos pequenos). */
export interface Obstrutor {
  posicao(): Vector3;
  raio: number;
  definirTransparencia(alfa: number): void;
}

/** Estado do personagem que a câmera precisa a cada quadro. */
export interface AlvoCamera {
  posicao: Vector3; // pés
  yaw: number; // para onde o personagem olha
  velocidade: Vector3;
  correndo: boolean;
}

/**
 * Câmera em terceira pessoa com órbita livre (seção 3 da revisão 2).
 *
 * O mouse e o analógico direito têm prioridade: qualquer entrada cancela a recentralização.
 * Com o personagem andando e sem entrada por `atrasoRecentralizar`, a câmera gira até as costas
 * dele, mais rápido quanto mais rápido ele anda e desacelerando perto do alvo. Se o personagem
 * anda em direção à câmera (mais de 135°), ela só recua junto e espera 1,5 s antes de girar.
 * A colisão lança uma esfera do foco até a posição desejada; a câmera aproxima na hora e volta
 * devagar (0,3 s). Zonas de câmera mudam distância e campo de visão.
 */
export class CameraTerceiraPessoa {
  readonly camera: FreeCamera;
  opcoes: OpcoesCamera = carregarOpcoes();
  /** Ângulo horizontal: a câmera olha na direção (sin yaw, 0, cos yaw). */
  yaw = 0;
  /** Inclinação vertical em radianos (positivo olha para baixo). */
  pitch = C.inclinacaoNeutraGraus * RAD;
  /** Distância escolhida com a roda do mouse. */
  distanciaZoom: number = C.distancia;
  /** Distância efetiva depois da colisão. */
  distanciaAtual: number = C.distancia;
  /** Ajustes de roteiro e diálogo. */
  distanciaExtra = 0;
  alturaExtra = 0;
  tremor = 0;
  /** Gancho para mira/travamento de alvo no futuro (seção 12): com alvo, o yaw aponta para ele. */
  alvoTravado: Vector3 | null = null;
  zonas: ZonaCamera[] = [];
  zonaPadrao: keyof typeof C.zonas = "vila";
  obstrutores: () => Obstrutor[] = () => [];
  /** Corpo do próprio personagem, ignorado pela colisão da câmera. */
  corpoIgnorado: PhysicsBody | null = null;
  aoTransparenciaPersonagem: ((alfa: number) => void) | null = null;

  // estado interno
  private foco = new Vector3();
  private velFoco = new Vector3();
  private dxMouse = 0;
  private dyMouse = 0;
  private tempoSemMouse = 0;
  private tempoAndando = 0;
  private tempoCostas = 0;
  private pesoRecentralizar = 0;
  private distanciaZona: number = C.zonas.vila.distancia;
  private fovZona = 0;
  private fovAtual: number = C.fovGraus;
  private esfera: PhysicsShapeSphere | null = null;
  private resultadoEntrada = new ShapeCastResult();
  private resultadoAcerto = new ShapeCastResult();
  /** Registro de diagnóstico (testes): se esteve recentralizando no último quadro. */
  recentralizando = false;

  constructor(private cena: Scene) {
    this.camera = new FreeCamera("camera", new Vector3(0, 2, -5), cena);
    this.camera.fovMode = Camera.FOVMODE_HORIZONTAL_FIXED;
    this.camera.fov = C.fovGraus * RAD;
    this.camera.minZ = 0.1;
    this.camera.maxZ = 2500;
    this.camera.inputs.clear();
  }

  // ------------------------------------------------------------------ entrada

  /** Movimento do mouse (pixels) ou do analógico direito já convertido para pixels equivalentes. */
  girar(dx: number, dy: number): void {
    this.dxMouse += dx;
    this.dyMouse += dy;
  }

  zoom(passos: number): void {
    this.distanciaZoom = Math.min(C.distanciaMaxima, Math.max(C.distanciaMinima, this.distanciaZoom + passos * C.passoZoom));
  }

  definirOpcoes(o: Partial<OpcoesCamera>): void {
    this.opcoes = { ...this.opcoes, ...o };
    salvarOpcoes(this.opcoes);
  }

  /** Posiciona a câmera atrás do personagem, sem suavização (teleporte, troca de área). */
  posicionar(alvo: AlvoCamera, yaw = alvo.yaw): void {
    this.yaw = yaw;
    this.pitch = C.inclinacaoNeutraGraus * RAD;
    this.foco.set(alvo.posicao.x, alvo.posicao.y + C.alturaFoco, alvo.posicao.z);
    this.velFoco.setAll(0);
    this.distanciaAtual = this.distanciaDesejada();
    this.aplicarPosicao(0);
  }

  // ------------------------------------------------------------------ atualização

  atualizar(dt: number, alvo: AlvoCamera): void {
    if (dt <= 0) return;
    this.atualizarZona(dt, alvo.posicao);
    this.atualizarOrbita(dt, alvo);
    this.atualizarFoco(dt, alvo.posicao);
    this.atualizarFov(dt, alvo.correndo && alvo.velocidade.length() > CFG.movimento.andar + 0.5);
    this.atualizarColisao(dt);
    this.aplicarPosicao(dt);
    this.atualizarTransparencias();
  }

  private atualizarOrbita(dt: number, alvo: AlvoCamera): void {
    const sens = C.sensibilidade * this.opcoes.sensibilidade;
    const temEntrada = Math.abs(this.dxMouse) + Math.abs(this.dyMouse) > 0.01;
    if (temEntrada) {
      this.yaw += this.dxMouse * sens;
      this.pitch += this.dyMouse * sens * (this.opcoes.inverterY ? -1 : 1);
      this.tempoSemMouse = 0;
      this.pesoRecentralizar = 0;
      this.tempoCostas = 0;
    } else {
      this.tempoSemMouse += dt;
    }
    this.dxMouse = 0;
    this.dyMouse = 0;
    this.pitch = Math.min(C.inclinacaoMaxGraus * RAD, Math.max(C.inclinacaoMinGraus * RAD, this.pitch));

    if (this.alvoTravado) {
      const d = this.alvoTravado.subtract(alvo.posicao);
      this.yaw += diferencaAngulo(Math.atan2(d.x, d.z), this.yaw) * Math.min(1, dt * 8);
      this.recentralizando = false;
      return;
    }

    const vh = Math.hypot(alvo.velocidade.x, alvo.velocidade.z);
    this.tempoAndando = vh < 0.3 ? 0 : this.tempoAndando + dt;
    this.recentralizando = false;
    // o atraso conta a partir do mais recente entre a última entrada do mouse e o início da caminhada
    const parado = Math.min(this.tempoSemMouse, this.tempoAndando);
    if (temEntrada || !this.opcoes.recentralizar || vh < 0.3 || parado < this.opcoes.atrasoRecentralizar) {
      this.pesoRecentralizar = 0;
      if (vh < 0.3) this.tempoCostas = 0;
      return;
    }
    const direcaoMovimento = Math.atan2(alvo.velocidade.x, alvo.velocidade.z);
    const contraCamera = Math.abs(diferencaAngulo(direcaoMovimento, this.yaw)) > C.anguloCostasGraus * RAD;
    if (contraCamera) {
      this.tempoCostas += dt;
      if (this.tempoCostas < C.tempoCostas) {
        this.pesoRecentralizar = 0;
        return; // só recua acompanhando o personagem
      }
    } else {
      this.tempoCostas = 0;
    }
    // entrada suave: o giro cresce em 0,3 s, sem tranco no início
    this.pesoRecentralizar = Math.min(1, this.pesoRecentralizar + dt / 0.3);
    const erro = diferencaAngulo(alvo.yaw, this.yaw);
    const omega = (C.velocidadeRecentralizarBase + C.velocidadeRecentralizarPorMetro * vh) * this.pesoRecentralizar;
    // aproximação exponencial: rápida longe do alvo, desacelera perto dele
    this.yaw += erro * (1 - Math.exp(-omega * dt * 2));
    const neutra = C.inclinacaoNeutraGraus * RAD;
    this.pitch += (neutra - this.pitch) * (1 - Math.exp(-C.velocidadeInclinacao * dt * this.pesoRecentralizar));
    this.recentralizando = true;
  }

  private atualizarFoco(dt: number, pes: Vector3): void {
    const alvo = new Vector3(pes.x, pes.y + C.alturaFoco + this.alturaExtra, pes.z);
    // mola criticamente amortecida, rígida na horizontal e mais macia na vertical
    const passo = (k: number, x: number, v: number, alvoX: number): [number, number] => {
      const w = k;
      const f = 1 + 2 * dt * w;
      const oo = w * w;
      const hoo = dt * oo;
      const hhoo = dt * hoo;
      const det = 1 / (f + hhoo);
      const novoX = (f * x + dt * v + hhoo * alvoX) * det;
      const novoV = (v + hoo * (alvoX - x)) * det;
      return [novoX, novoV];
    };
    [this.foco.x, this.velFoco.x] = passo(C.molaHorizontal, this.foco.x, this.velFoco.x, alvo.x);
    [this.foco.z, this.velFoco.z] = passo(C.molaHorizontal, this.foco.z, this.velFoco.z, alvo.z);
    [this.foco.y, this.velFoco.y] = passo(C.molaVertical, this.foco.y, this.velFoco.y, alvo.y);
  }

  private atualizarZona(dt: number, p: Vector3): void {
    let tipo = this.zonaPadrao;
    for (const z of this.zonas) {
      if (p.x >= z.min[0] && p.x <= z.max[0] && p.y >= z.min[1] && p.y <= z.max[1] && p.z >= z.min[2] && p.z <= z.max[2]) {
        tipo = z.tipo;
        break;
      }
    }
    const cfg = C.zonas[tipo];
    const k = Math.min(1, dt / C.transicaoZona * 3);
    this.distanciaZona += (cfg.distancia - this.distanciaZona) * k;
    this.fovZona += (cfg.fovExtra - this.fovZona) * k;
  }

  private atualizarFov(dt: number, correndo: boolean): void {
    const alvo = C.fovGraus + this.fovZona + (correndo ? C.acrescimoFovCorrida : 0);
    this.fovAtual += (alvo - this.fovAtual) * Math.min(1, dt * C.suavizacaoFov);
    this.camera.fov = this.fovAtual * RAD;
  }

  /** Distância sem colisão: zoom do jogador escalado pela zona (a zona da vila é a referência). */
  private distanciaDesejada(): number {
    const escala = this.distanciaZona / C.zonas.vila.distancia;
    return Math.max(1.2, this.distanciaZoom * escala + this.distanciaExtra);
  }

  private direcao(): Vector3 {
    const cp = Math.cos(this.pitch);
    return new Vector3(Math.sin(this.yaw) * cp, -Math.sin(this.pitch), Math.cos(this.yaw) * cp);
  }

  /** Lança uma esfera do foco até a câmera; devolve a distância livre. */
  private distanciaLivre(desejada: number): number {
    const plugin = this.cena.getPhysicsEngine()?.getPhysicsPlugin() as HavokPlugin | undefined;
    if (!plugin || typeof plugin.shapeCast !== "function") return desejada;
    if (!this.esfera) {
      this.esfera = new PhysicsShapeSphere(Vector3.Zero(), C.raioColisao, this.cena);
      this.esfera.filterCollideMask = ~CAMADA_SEM_CAMERA;
    }
    const inicio = this.foco.clone();
    const fim = inicio.subtract(this.direcao().scale(desejada));
    this.resultadoEntrada.reset();
    this.resultadoAcerto.reset();
    plugin.shapeCast({
      shape: this.esfera, rotation: Quaternion.Identity(), startPosition: inicio, endPosition: fim,
      shouldHitTriggers: false, ignoreBody: this.corpoIgnorado ?? undefined,
    }, this.resultadoEntrada, this.resultadoAcerto);
    if (!this.resultadoAcerto.hasHit) return desejada;
    return Math.max(0.3, desejada * this.resultadoAcerto.hitFraction - 0.05);
  }

  private atualizarColisao(dt: number): void {
    const desejada = this.distanciaDesejada();
    const livre = this.distanciaLivre(desejada);
    if (livre < this.distanciaAtual) {
      this.distanciaAtual = livre; // aproxima na hora
    } else {
      const velocidade = desejada / C.tempoVoltarDistancia;
      this.distanciaAtual = Math.min(livre, this.distanciaAtual + velocidade * dt);
    }
  }

  private aplicarPosicao(dt: number): void {
    const dir = this.direcao();
    const lateral = new Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw)).scale(C.deslocamentoLateral);
    const foco = this.foco.add(lateral);
    let tx = 0, ty = 0;
    if (this.tremor > 0) {
      tx = (Math.random() - 0.5) * this.tremor * 0.15;
      ty = (Math.random() - 0.5) * this.tremor * 0.15;
      this.tremor = Math.max(0, this.tremor - dt);
    }
    this.camera.position.copyFrom(foco.subtract(dir.scale(this.distanciaAtual)));
    this.camera.position.x += tx;
    this.camera.position.y += ty;
    this.camera.setTarget(foco.add(new Vector3(tx, ty, 0)));
  }

  private atualizarTransparencias(): void {
    const cam = this.camera.position;
    const foco = this.foco;
    const seg = foco.subtract(cam);
    const comp = seg.length();
    for (const o of this.obstrutores()) {
      const p = o.posicao();
      const t = Math.max(0, Math.min(1, Vector3.Dot(p.subtract(cam), seg) / (comp * comp)));
      const maisPerto = cam.add(seg.scale(t));
      const dist = Vector3.Distance(new Vector3(p.x, maisPerto.y, p.z), maisPerto);
      o.definirTransparencia(dist < o.raio && t < 0.95 ? 0.3 : 1);
    }
    const perto = this.distanciaAtual < C.distanciaTranslucidoPersonagem;
    this.aoTransparenciaPersonagem?.(perto ? 0.25 : 1);
  }

  /** Vetores de frente e direita no plano do chão, para o movimento relativo à câmera. */
  eixosNoChao(): { frente: Vector3; direita: Vector3 } {
    return {
      frente: new Vector3(Math.sin(this.yaw), 0, Math.cos(this.yaw)),
      direita: new Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw)),
    };
  }

  get focoAtual(): Vector3 {
    return this.foco.clone();
  }
}
