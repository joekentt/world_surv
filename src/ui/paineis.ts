import type { Jogo } from "../core/jogo";
import { CFG } from "../config";
import { descricaoItem, nomeItem, pesoItem, precoItem } from "../economy/itens";
import { UI } from "./textos";

type Painel = "inventario" | "diario" | "menu" | "loja" | null;

const UPGRADES: Record<string, { nome: string; descricao: string; requer?: (j: Jogo) => boolean; tem: (j: Jogo) => boolean; aplicar: (j: Jogo) => void }> = {
  filtro2: {
    nome: "Filtro nível 2", descricao: `Ar para ${CFG.epi.filtroNivel2} s na superfície. Chega ao Marco.`,
    tem: (j) => j.estado.d.upgrades.filtro >= 2, aplicar: (j) => { j.estado.d.upgrades.filtro = 2; },
  },
  filtro3: {
    nome: "Filtro nível 3", descricao: `Ar para ${CFG.epi.filtroNivel3} s. Chega à Antena.`,
    requer: (j) => j.estado.d.upgrades.filtro >= 2, tem: (j) => j.estado.d.upgrades.filtro >= 3, aplicar: (j) => { j.estado.d.upgrades.filtro = 3; },
  },
  roupa_reforcada: {
    nome: "Roupa reforçada", descricao: `Integridade ${CFG.epi.roupaReforcada} e menos desgaste por poeira e queda.`,
    tem: (j) => j.estado.d.upgrades.roupaReforcada, aplicar: (j) => { j.estado.d.upgrades.roupaReforcada = true; },
  },
  cilindro_extra: {
    nome: "Cilindro extra", descricao: `+${CFG.epi.cilindroExtra} s de ar em qualquer filtro.`,
    tem: (j) => j.estado.d.upgrades.cilindroExtra, aplicar: (j) => { j.estado.d.upgrades.cilindroExtra = true; },
  },
};

const LOJAS: Record<string, { titulo: string; compra?: boolean; venda: string[]; upgrades: string[]; filtro?: number; faccao: string }> = {
  bento: { titulo: "Tio Bento · mercado da praça", compra: true, venda: ["filtro_reposicao"], upgrades: [], filtro: 1, faccao: "conselho" },
  samira: { titulo: "Caravana de Qarar", venda: [], upgrades: ["filtro2", "filtro3", "roupa_reforcada", "cilindro_extra"], faccao: "caravana" },
  nita: { titulo: "Banca das Galerias · filtros recondicionados", compra: true, venda: ["filtro_reposicao"], upgrades: [], filtro: 0.7, faccao: "galerias" },
};

/** Inventário, diário, menu de pausa e lojas. Um painel aberto por vez; o jogo fica parado. */
export class Paineis {
  aberto: Painel = null;
  private el: HTMLElement;
  private lojaAtual = "";

  constructor(private jogo: Jogo, raiz: HTMLElement) {
    this.el = document.createElement("div");
    this.el.className = "painel interativo";
    raiz.appendChild(this.el);
    this.el.addEventListener("click", (ev) => this.clicar(ev));
  }

  /** Multiplicador de preço conforme a escolha da missão 3. */
  fatorPreco(faccao: string): number {
    const e = this.jogo.estado;
    const vig = e.flag("m3_ajudou_vigilia");
    if (vig === undefined) return 1;
    const aliado = (faccao === "galerias" && vig === true) || (faccao === "conselho" && vig === false);
    const hostil = (faccao === "conselho" && vig === true) || (faccao === "galerias" && vig === false);
    return aliado ? 1 - CFG.economia.descontoAliado : hostil ? 1 + CFG.economia.acrescimoHostil : 1;
  }

  precoFiltro(loja: string): number {
    const l = LOJAS[loja];
    return Math.max(1, Math.round(CFG.economia.precoFiltroReposicao * (l.filtro ?? 1) * this.fatorPreco(l.faccao)));
  }

  precoUpgrade(id: string): number {
    return Math.round((CFG.economia.upgrades as Record<string, number>)[id] * this.fatorPreco("caravana"));
  }

  alternar(p: Exclude<Painel, null>): void {
    if (this.aberto === p) this.fechar();
    else this.abrir(p);
  }

  abrir(p: Exclude<Painel, null>, loja = ""): void {
    this.aberto = p;
    if (loja) this.lojaAtual = loja;
    this.jogo.pausado = p !== "loja";
    this.jogo.travarParaDialogo(true);
    this.render();
    this.el.classList.add("visivel");
  }

  abrirLoja(id: string): void {
    this.abrir("loja", id);
  }

  fechar(): void {
    this.aberto = null;
    this.el.classList.remove("visivel");
    this.jogo.pausado = false;
    this.jogo.travarParaDialogo(false);
    this.jogo.estado.avisar("painelFechado");
  }

  render(): void {
    const e = this.jogo.estado;
    let html = "";
    if (this.aberto === "inventario") {
      const itens = Object.entries(e.d.itens);
      html = `<h2>Mochila <small>${e.pesoTotal().toFixed(1)} / ${e.pesoMaximo()} kg · ${e.d.cotas} cotas</small></h2>
        <ul class="itens">${itens.length ? itens.map(([k, n]) => `<li><b>${nomeItem(k, n)}</b> × ${n} <small>${(pesoItem(k) * n).toFixed(1)} kg</small><p>${descricaoItem(k)}</p></li>`).join("") : "<li>Vazia.</li>"}</ul>
        <h3>Equipamento</h3><ul class="itens">
          <li><b>Filtro nível ${e.d.upgrades.filtro}</b> <small>${e.capacidadeFiltro()} s de ar</small></li>
          <li><b>${e.d.upgrades.roupaReforcada ? "Roupa reforçada" : "Roupa remendada de Darci"}</b> <small>integridade ${e.capacidadeRoupa()}</small></li>
        </ul>`;
    } else if (this.aberto === "diario") {
      const linhas = this.jogo.missoes.diario();
      html = `<h2>Diário <small>dia ${e.d.dia}</small></h2><ul class="diario">${linhas.map((l) =>
        `<li class="${l.estado}"><b>${l.titulo}</b>${l.tipo === "opcional" ? " <small>tarefa</small>" : ""}<p>${l.texto}</p></li>`).join("") || "<li>Nada anotado ainda.</li>"}</ul>`;
    } else if (this.aberto === "menu") {
      html = `<h2>${UI.pausado}</h2>
        <button data-acao="voltar">${UI.voltar}</button>
        <label class="volume">${UI.volume} <input type="range" min="0" max="1" step="0.05" value="${this.jogo.audio.volumeGeral}" data-acao="volume"></label>
        <button data-acao="carregar">${UI.reiniciarDia}</button>
        <p class="controles">${UI.controles}<br>${UI.controlesGamepad}</p>`;
    } else if (this.aberto === "loja") {
      const l = LOJAS[this.lojaAtual];
      const fator = this.fatorPreco(l.faccao);
      const aviso = fator < 1 ? "<p class='preco-bom'>Preço de amigo.</p>" : fator > 1 ? "<p class='preco-ruim'>Preço salgado para você.</p>" : "";
      html = `<h2>${l.titulo} <small>${e.d.cotas} cotas · ${e.pesoTotal().toFixed(1)} / ${e.pesoMaximo()} kg</small></h2>${aviso}`;
      if (l.compra) {
        const vendaveis = ["sucata", "componente", "vidro"].filter((k) => e.qtd(k) > 0);
        html += `<h3>Vender</h3><ul class="loja">${vendaveis.map((k) => `<li>${nomeItem(k, e.qtd(k))} × ${e.qtd(k)} <span>${precoItem(k)} cota(s) cada</span>
          <button data-acao="vender" data-item="${k}">Vender 1</button><button data-acao="venderTudo" data-item="${k}">Vender tudo</button></li>`).join("") || "<li>Nada para vender.</li>"}</ul>`;
      }
      if (l.venda.length) {
        const preco = this.precoFiltro(this.lojaAtual);
        html += `<h3>Comprar</h3><ul class="loja"><li>${nomeItem("filtro_reposicao")} (você tem ${e.qtd("filtro_reposicao")}) <span>${preco} cotas</span>
          <button data-acao="comprarFiltro" ${e.d.cotas < preco ? "disabled" : ""}>Comprar</button></li></ul>`;
      }
      if (l.upgrades.length) {
        html += `<h3>Equipamento de Qarar</h3><ul class="loja">${l.upgrades.map((id) => {
          const u = UPGRADES[id];
          const preco = this.precoUpgrade(id);
          const tem = u.tem(this.jogo);
          const bloqueado = u.requer && !u.requer(this.jogo);
          return `<li><b>${u.nome}</b> <span>${tem ? "comprado" : `${preco} cotas`}</span><p>${u.descricao}${bloqueado ? " Exige o nível anterior." : ""}</p>
            ${tem ? "" : `<button data-acao="upgrade" data-item="${id}" ${e.d.cotas < preco || bloqueado ? "disabled" : ""}>Comprar</button>`}</li>`;
        }).join("")}</ul>`;
      }
      html += `<button data-acao="voltar">Sair</button>`;
    }
    this.el.innerHTML = html;
  }

  private clicar(ev: Event): void {
    const b = (ev.target as HTMLElement).closest("[data-acao]") as HTMLElement | null;
    if (!b) return;
    this.executar(b.dataset.acao!, b.dataset.item);
  }

  executar(acao: string, item?: string): void {
    const j = this.jogo;
    const e = j.estado;
    j.audio.tocar("clique", 0.5);
    if (acao === "voltar") return this.fechar();
    if (acao === "carregar") { this.fechar(); void j.carregarSave(); return; }
    if (acao === "vender" && item) { e.dar(item, -1); e.mudarCotas(precoItem(item)); j.audio.tocar("moedas", 0.5); e.avisar(`vendeu:${item}`); }
    if (acao === "venderTudo" && item) { const n = e.qtd(item); e.dar(item, -n); e.mudarCotas(precoItem(item) * n); j.audio.tocar("moedas", 0.6); e.avisar(`vendeu:${item}`); }
    if (acao === "comprarFiltro") {
      const p = this.precoFiltro(this.lojaAtual);
      if (e.d.cotas >= p) { e.mudarCotas(-p); e.dar("filtro_reposicao", 1); j.audio.tocar("moedas", 0.5); }
    }
    if (acao === "upgrade" && item) {
      const u = UPGRADES[item];
      const p = this.precoUpgrade(item);
      if (e.d.cotas >= p && !u.tem(j) && (!u.requer || u.requer(j))) {
        e.mudarCotas(-p);
        u.aplicar(j);
        e.avisar("upgrade");
        e.avisar(`upgrade:${item}`);
        j.audio.tocar("moedas", 0.7);
      }
    }
    this.render();
  }

  atualizarInput(): void {
    const ent = this.jogo.entrada;
    if (ent.apertouUI("menu")) {
      if (this.aberto) this.fechar();
      else this.abrir("menu");
      return;
    }
    if (this.aberto === "loja") return;
    if (ent.apertouUI("inventario")) this.alternar("inventario");
    if (ent.apertouUI("diario")) this.alternar("diario");
  }

  /** Volume (input range) */
  ligarVolume(): void {
    this.el.addEventListener("input", (ev) => {
      const t = ev.target as HTMLInputElement;
      if (t.dataset.acao === "volume") this.jogo.audio.definirVolumeGeral(Number(t.value));
    });
  }
}
