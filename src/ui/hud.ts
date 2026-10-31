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
  private avisoInteracao: HTMLElement;
  private nomeArea: HTMLElement;
  private cortina: HTMLElement;
  private mensagem: HTMLElement;
  private morte: HTMLElement;
  private avisoMissao: HTMLElement;
  private tempoAviso = 0;
  private tempoNome = 0;
  private tempoMsg = 0;

  constructor() {
    this.raiz = document.getElementById("ui")!;
    this.avisoInteracao = el("div", "aviso-interacao", this.raiz);
    this.nomeArea = el("div", "nome-area", this.raiz);
    this.mensagem = el("div", "mensagem", this.raiz);
    this.cortina = el("div", "cortina", this.raiz);
    this.morte = el("div", "tela-morte", this.raiz);
    this.avisoMissao = el("div", "aviso-missao", this.raiz);
  }

  telaFim(titulo: string, texto: string, rodape: string): void {
    const fim = el("div", "tela-fim interativo", this.raiz);
    fim.innerHTML = `<h1>${titulo}</h1><p>${texto}</p><small>${rodape}</small><button>Continuar explorando</button>`;
    fim.querySelector("button")!.addEventListener("click", () => fim.remove());
    requestAnimationFrame(() => fim.classList.add("visivel"));
  }

  aviso(rotulo: string, titulo: string, texto: string): void {
    this.avisoMissao.innerHTML = `<div class="rot">${rotulo}</div>${titulo ? `<b>${titulo}</b>` : ""}<p>${texto}</p>`;
    this.avisoMissao.classList.add("visivel");
    this.tempoAviso = 6;
  }

  telaMorte(titulo: string | null, texto: string | null): void {
    if (!titulo) {
      this.morte.classList.remove("visivel");
      return;
    }
    this.morte.innerHTML = `<h2>${titulo}</h2><p>${texto ?? ""}</p>`;
    this.morte.classList.add("visivel");
  }

  el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, pai: HTMLElement = this.raiz): HTMLElementTagNameMap[K] {
    return el(tag, cls, pai);
  }

  mostrarAviso(rotulo: string | null, gamepad: boolean): void {
    if (!rotulo) {
      this.avisoInteracao.classList.remove("visivel");
      return;
    }
    const tecla = gamepad ? UI.botaoInteragir : UI.teclaInteragir;
    this.avisoInteracao.innerHTML = `<kbd>${tecla}</kbd> ${rotulo}`;
    this.avisoInteracao.classList.add("visivel");
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
    if (this.tempoAviso > 0 && (this.tempoAviso -= dt) <= 0) this.avisoMissao.classList.remove("visivel");
  }
}
