import { UI } from "./textos";

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, pai: HTMLElement): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  e.className = cls;
  pai.appendChild(e);
  return e;
}

/** Camada de interface em HTML sobre o canvas: avisos, nome da área e escurecimento. */
export class Hud {
  readonly raiz: HTMLElement;
  private aviso: HTMLElement;
  private nomeArea: HTMLElement;
  private cortina: HTMLElement;
  private mensagem: HTMLElement;
  private tempoNome = 0;
  private tempoMsg = 0;

  constructor() {
    this.raiz = document.getElementById("ui")!;
    this.aviso = el("div", "aviso-interacao", this.raiz);
    this.nomeArea = el("div", "nome-area", this.raiz);
    this.mensagem = el("div", "mensagem", this.raiz);
    this.cortina = el("div", "cortina", this.raiz);
  }

  el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, pai: HTMLElement = this.raiz): HTMLElementTagNameMap[K] {
    return el(tag, cls, pai);
  }

  mostrarAviso(rotulo: string | null, gamepad: boolean): void {
    if (!rotulo) {
      this.aviso.classList.remove("visivel");
      return;
    }
    const tecla = gamepad ? UI.botaoInteragir : UI.teclaInteragir;
    this.aviso.innerHTML = `<kbd>${tecla}</kbd> ${rotulo}`;
    this.aviso.classList.add("visivel");
  }

  anunciarArea(nome: string): void {
    this.nomeArea.textContent = nome;
    this.nomeArea.classList.add("visivel");
    this.tempoNome = 3.5;
  }

  mensagemCurta(texto: string, segundos = 3): void {
    this.mensagem.textContent = texto;
    this.mensagem.classList.add("visivel");
    this.tempoMsg = segundos;
  }

  async escurecer(sim: boolean, ms = 450): Promise<void> {
    this.cortina.style.transitionDuration = `${ms}ms`;
    this.cortina.classList.toggle("ativa", sim);
    await new Promise((r) => setTimeout(r, ms));
  }

  atualizar(dt: number): void {
    if (this.tempoNome > 0 && (this.tempoNome -= dt) <= 0) this.nomeArea.classList.remove("visivel");
    if (this.tempoMsg > 0 && (this.tempoMsg -= dt) <= 0) this.mensagem.classList.remove("visivel");
  }
}
