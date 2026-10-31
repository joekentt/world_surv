import type { SistemaEPI } from "../epi/epi";
import type { Estado } from "../core/estado";
import { textos } from "./textos";

/**
 * Medidores do EPI e da mochila. Pensados para serem lidos sem tutorial: ícone, número grande
 * de segundos de ar, barra que muda de cor e pulsa quando falta pouco.
 */
export class Medidores {
  private painel: HTMLElement;
  private filtroArco: SVGCircleElement;
  private filtroNum: HTMLElement;
  private roupaBarra: HTMLElement;
  private saudeBarra: HTMLElement;
  private saudeLinha: HTMLElement;
  private mochila: HTMLElement;
  private cotas: HTMLElement;
  private vinheta: HTMLElement;
  private tempestade: HTMLElement;
  private dano = 0;

  constructor(raiz: HTMLElement, private estado: Estado) {
    this.vinheta = document.createElement("div");
    this.vinheta.className = "vinheta-dano";
    raiz.appendChild(this.vinheta);
    this.painel = document.createElement("div");
    this.painel.className = "medidores";
    this.painel.innerHTML = `
      <div class="filtro" title="${textos("epi.filtro")}">
        <svg viewBox="0 0 64 64"><circle class="fundo" cx="32" cy="32" r="27"/><circle class="arco" cx="32" cy="32" r="27"/></svg>
        <div class="icone-mascara">⬡</div><div class="num">90</div>
      </div>
      <div class="barras">
        <div class="linha roupa"><span class="rot">${textos("epi.roupa")}</span><div class="barra"><i></i></div></div>
        <div class="linha saude"><span class="rot">${textos("epi.saude")}</span><div class="barra"><i></i></div></div>
      </div>`;
    raiz.appendChild(this.painel);
    this.filtroArco = this.painel.querySelector(".arco")!;
    this.filtroNum = this.painel.querySelector(".num")!;
    this.roupaBarra = this.painel.querySelector(".roupa i")!;
    this.saudeBarra = this.painel.querySelector(".saude i")!;
    this.saudeLinha = this.painel.querySelector(".linha.saude")!;
    const rodape = document.createElement("div");
    rodape.className = "mochila-cotas";
    rodape.innerHTML = `<span class="mochila"></span><span class="cotas"></span>`;
    raiz.appendChild(rodape);
    this.mochila = rodape.querySelector(".mochila")!;
    this.cotas = rodape.querySelector(".cotas")!;
    this.tempestade = document.createElement("div");
    this.tempestade.className = "alerta-tempestade";
    this.tempestade.textContent = "⚠";
    raiz.appendChild(this.tempestade);
    estado.ouvir(() => this.atualizarMochila());
    this.atualizarMochila();
  }

  atualizarMochila(): void {
    const p = this.estado.pesoTotal();
    const max = this.estado.pesoMaximo();
    this.mochila.textContent = `🎒 ${p.toFixed(1)} / ${max} kg`;
    this.mochila.classList.toggle("cheia", p >= max * 0.95);
    this.cotas.textContent = `◉ ${this.estado.d.cotas} ${textos("epi.cotas").toLowerCase()}`;
  }

  atualizarEPI(epi: SistemaEPI, visivel: boolean): void {
    this.painel.classList.toggle("visivel", visivel);
    const f = Math.max(0, Math.min(1, epi.fracaoFiltro));
    const circ = 2 * Math.PI * 27;
    this.filtroArco.style.strokeDasharray = `${circ}`;
    this.filtroArco.style.strokeDashoffset = `${circ * (1 - f)}`;
    this.filtroNum.textContent = `${Math.ceil(epi.filtro)}`;
    const estadoFiltro = f <= 0 ? "zerado" : f < 0.12 ? "critico" : f < 0.3 ? "baixo" : "ok";
    this.painel.dataset.filtro = estadoFiltro;
    const r = Math.max(0, Math.min(1, epi.fracaoRoupa));
    this.roupaBarra.style.width = `${r * 100}%`;
    this.painel.dataset.roupa = r <= 0 ? "zerado" : r < 0.25 ? "critico" : "ok";
    this.saudeBarra.style.width = `${epi.saude}%`;
    this.saudeLinha.classList.toggle("oculta", epi.saude >= 99.5 && visivel);
    this.dano = Math.max(0, this.dano - 0.04);
    this.vinheta.style.opacity = `${Math.min(0.85, this.dano + (100 - epi.saude) / 160)}`;
  }

  piscarDano(): void {
    this.dano = Math.min(1, this.dano + 0.25);
  }

  alertaTempestade(sim: boolean): void {
    this.tempestade.classList.toggle("visivel", sim);
  }
}
