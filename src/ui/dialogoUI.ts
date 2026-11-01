import type { Entrada } from "../core/entrada";
import { textos } from "./textos";

/** Caixa de diálogo com texto digitado e opções navegáveis por teclado, gamepad ou mouse. */
export class DialogoUI {
  private caixa: HTMLElement;
  private nome: HTMLElement;
  private texto: HTMLElement;
  private opcoes: HTMLElement;
  private dica: HTMLElement;
  private esperando: ((i: number) => void) | null = null;
  private selecionada = 0;
  private qtd = 0;
  private avancar: (() => void) | null = null;
  private digitando = false;

  constructor(raiz: HTMLElement, private entrada: Entrada, private clique: () => void) {
    this.caixa = document.createElement("div");
    this.caixa.className = "dialogo interativo";
    this.caixa.innerHTML = `<div class="nome"></div><div class="texto"></div><ol class="opcoes"></ol><div class="dica">▶ <small>${textos("dicaAvancar")}</small></div>`;
    raiz.appendChild(this.caixa);
    this.nome = this.caixa.querySelector(".nome")!;
    this.texto = this.caixa.querySelector(".texto")!;
    this.opcoes = this.caixa.querySelector(".opcoes")!;
    this.dica = this.caixa.querySelector(".dica")!;
    this.caixa.addEventListener("click", (ev) => {
      const li = (ev.target as HTMLElement).closest("li");
      if (li && this.esperando) this.confirmar(Number(li.dataset.i));
      else this.avancar?.();
    });
  }

  get aberto(): boolean {
    return this.caixa.classList.contains("visivel");
  }

  fala(quem: string, texto: string, jogador: boolean): Promise<void> {
    this.caixa.classList.add("visivel");
    this.caixa.classList.toggle("do-jogador", jogador);
    this.nome.textContent = quem;
    this.opcoes.innerHTML = "";
    this.dica.style.visibility = "hidden";
    return new Promise((ok) => {
      let i = 0;
      this.digitando = true;
      this.texto.textContent = "";
      const passo = () => {
        if (!this.digitando) return;
        i += 2;
        this.texto.textContent = texto.slice(0, i);
        if (i < texto.length) setTimeout(passo, 16);
        else {
          this.digitando = false;
          this.dica.style.visibility = "visible";
        }
      };
      passo();
      this.avancar = () => {
        if (this.digitando) {
          this.digitando = false;
          this.texto.textContent = texto;
          this.dica.style.visibility = "visible";
          return;
        }
        this.avancar = null;
        ok();
      };
    });
  }

  escolher(opcoes: string[]): Promise<number> {
    this.dica.style.visibility = "hidden";
    this.opcoes.innerHTML = opcoes.map((o, i) => `<li data-i="${i}">${o}</li>`).join("");
    this.qtd = opcoes.length;
    this.selecionada = 0;
    this.marcar();
    return new Promise((ok) => { this.esperando = ok; });
  }

  private marcar(): void {
    this.opcoes.querySelectorAll("li").forEach((li, i) => li.classList.toggle("sel", i === this.selecionada));
  }

  private confirmar(i: number): void {
    const f = this.esperando;
    this.esperando = null;
    this.opcoes.innerHTML = "";
    this.clique();
    f?.(i);
  }

  fechar(): void {
    this.caixa.classList.remove("visivel");
    this.esperando = null;
    this.avancar = null;
  }

  /** Lido a cada quadro enquanto o diálogo está aberto. */
  atualizar(): void {
    if (!this.aberto) return;
    const e = this.entrada;
    if (this.esperando) {
      if (e.apertouUI("baixo")) { this.selecionada = (this.selecionada + 1) % this.qtd; this.marcar(); this.clique(); }
      if (e.apertouUI("cima")) { this.selecionada = (this.selecionada + this.qtd - 1) % this.qtd; this.marcar(); this.clique(); }
      if (e.apertouUI("interagir") || e.apertouUI("confirmar")) this.confirmar(this.selecionada);
    } else if (this.avancar && (e.apertouUI("interagir") || e.apertouUI("confirmar"))) {
      this.avancar();
    }
  }

  /** Atalho para testes: escolhe a opção cujo texto contém o trecho. */
  escolherPorTexto(trecho: string): boolean {
    const lis = [...this.opcoes.querySelectorAll("li")];
    const i = lis.findIndex((li) => li.textContent?.includes(trecho));
    if (i < 0 || !this.esperando) return false;
    this.confirmar(i);
    return true;
  }

  avancarTexto(): void {
    this.avancar?.();
    this.avancar?.();
  }
}
