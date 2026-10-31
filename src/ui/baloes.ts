import { Matrix, Vector3, type Scene } from "@babylonjs/core";

interface Balao { el: HTMLElement; pos: () => Vector3; ate: number; }

/** Balões de fala presos à cabeça dos personagens (HTML projetado da cena). */
export class Baloes {
  private lista: Balao[] = [];
  constructor(private cena: Scene, private raiz: HTMLElement) {}

  mostrar(pos: () => Vector3, texto: string, segundos: number, tipo: "fundo" | "reacao" | "sermao" = "fundo"): void {
    const el = document.createElement("div");
    el.className = `balao balao-${tipo}`;
    el.textContent = texto;
    this.raiz.appendChild(el);
    this.lista.push({ el, pos, ate: performance.now() + segundos * 1000 });
  }

  limpar(): void {
    for (const b of this.lista) b.el.remove();
    this.lista = [];
  }

  atualizar(): void {
    const cam = this.cena.activeCamera;
    if (!cam) return;
    const eng = this.cena.getEngine();
    const vp = cam.viewport.toGlobal(eng.getRenderWidth(), eng.getRenderHeight());
    const escala = eng.getRenderWidth() / (eng.getRenderingCanvas()?.clientWidth || eng.getRenderWidth());
    const agora = performance.now();
    this.lista = this.lista.filter((b) => {
      if (agora > b.ate) {
        b.el.remove();
        return false;
      }
      const p = Vector3.Project(b.pos(), Matrix.Identity(), this.cena.getTransformMatrix(), vp);
      const visivel = p.z > 0 && p.z < 1;
      b.el.style.display = visivel ? "block" : "none";
      b.el.style.left = `${p.x / escala}px`;
      b.el.style.top = `${p.y / escala}px`;
      b.el.style.opacity = agora > b.ate - 400 ? "0" : "1";
      return true;
    });
  }
}
