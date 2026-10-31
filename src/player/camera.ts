import { FreeCamera, Vector3, type Scene } from "@babylonjs/core";
import { CFG } from "../config";

const C = CFG.camera;

/** Câmera lateral em 2,5D com suavização, antecipação na direção do movimento e limites por área. */
export class CameraLateral {
  readonly camera: FreeCamera;
  private alvo = new Vector3();
  private antecipacaoAtual = 0;
  limiteMin = -Infinity;
  limiteMax = Infinity;
  tremor = 0;
  /** Deslocamento extra (cutscenes, zoom no diálogo). */
  distanciaExtra = 0;
  alturaExtra = 0;

  constructor(cena: Scene) {
    this.camera = new FreeCamera("camera", new Vector3(0, C.altura, -C.distancia), cena);
    this.camera.fov = C.fov;
    this.camera.minZ = 0.3;
    this.camera.maxZ = 900;
    this.camera.inputs.clear();
  }

  seguir(x: number, y: number, lado: number, dt: number, imediato = false): void {
    const alvoAnt = lado * C.antecipacao;
    this.antecipacaoAtual += (alvoAnt - this.antecipacaoAtual) * Math.min(1, dt * 1.6);
    const meiaLargura = this.meiaLarguraVisivel();
    let ax = x + this.antecipacaoAtual;
    const min = this.limiteMin + meiaLargura;
    const max = this.limiteMax - meiaLargura;
    ax = min > max ? (this.limiteMin + this.limiteMax) / 2 : Math.min(max, Math.max(min, ax));
    const desejado = new Vector3(ax, y + C.alvoAltura + this.alturaExtra, 0);
    if (imediato) this.alvo.copyFrom(desejado);
    else Vector3.LerpToRef(this.alvo, desejado, Math.min(1, dt * C.suavizacao), this.alvo);
    const t = this.tremor > 0 ? this.tremor : 0;
    this.tremor = Math.max(0, this.tremor - dt);
    const tx = t ? (Math.random() - 0.5) * t * 0.3 : 0;
    const ty = t ? (Math.random() - 0.5) * t * 0.3 : 0;
    const dist = C.distancia + this.distanciaExtra;
    this.camera.position.set(this.alvo.x + tx, this.alvo.y + (C.altura - C.alvoAltura) + ty, -dist);
    this.camera.setTarget(new Vector3(this.alvo.x + tx, this.alvo.y + ty, 0));
  }

  private meiaLarguraVisivel(): number {
    const eng = this.camera.getScene().getEngine();
    const aspecto = eng.getRenderWidth() / Math.max(1, eng.getRenderHeight());
    const dist = C.distancia + this.distanciaExtra;
    return Math.tan(C.fov / 2) * dist * aspecto;
  }
}
