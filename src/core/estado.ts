import { CFG } from "../config";

export type EstadoMissao = "inativa" | "ativa" | "concluida";

export interface DadosJogo {
  versao: 1;
  dia: number;
  cotas: number;
  itens: Record<string, number>;
  upgrades: { filtro: 1 | 2 | 3; roupaReforcada: boolean; cilindroExtra: boolean };
  flags: Record<string, boolean | number | string>;
  missoes: Record<string, { estado: EstadoMissao; etapa: number }>;
  coletados: string[];
  local: { area: string; entrada: string };
  tempoJogo: number;
  subidas: number;
  turno: number;
  relogioTurno: number;
}

export function dadosIniciais(): DadosJogo {
  return {
    versao: 1,
    dia: 1,
    cotas: CFG.economia.cotasIniciais,
    itens: { filtro_reposicao: CFG.economia.filtrosIniciais },
    upgrades: { filtro: 1, roupaReforcada: false, cilindroExtra: false },
    flags: {},
    missoes: {},
    coletados: [],
    local: { area: "praca", entrada: "inicio" },
    tempoJogo: 0,
    subidas: 0,
    turno: 0,
    relogioTurno: 0,
  };
}

type Ouvinte = (chave: string) => void;

/** Estado serializável do jogo: tudo o que o save guarda passa por aqui. */
export class Estado {
  d: DadosJogo = dadosIniciais();
  private ouvintes: Ouvinte[] = [];

  ouvir(f: Ouvinte): void {
    this.ouvintes.push(f);
  }

  avisar(chave: string): void {
    for (const f of this.ouvintes) f(chave);
  }

  flag(nome: string): boolean | number | string | undefined {
    return this.d.flags[nome];
  }

  definirFlag(nome: string, valor: boolean | number | string): void {
    this.d.flags[nome] = valor;
    this.avisar(`flag:${nome}`);
  }

  qtd(item: string): number {
    return this.d.itens[item] ?? 0;
  }

  dar(item: string, n = 1): void {
    this.d.itens[item] = Math.max(0, this.qtd(item) + n);
    if (this.d.itens[item] === 0) delete this.d.itens[item];
    this.avisar(`item:${item}`);
  }

  pesoTotal(): number {
    const itens = CFG.inventario.itens as Record<string, { peso: number }>;
    return Object.entries(this.d.itens).reduce((s, [k, n]) => s + (itens[k]?.peso ?? 0) * n, 0);
  }

  pesoMaximo(): number {
    return CFG.inventario.pesoMaximo;
  }

  cabe(item: string, n = 1): boolean {
    const itens = CFG.inventario.itens as Record<string, { peso: number }>;
    return this.pesoTotal() + (itens[item]?.peso ?? 0) * n <= this.pesoMaximo() + 1e-6;
  }

  mudarCotas(n: number): void {
    this.d.cotas = Math.max(0, this.d.cotas + n);
    this.avisar("cotas");
  }

  missao(id: string): { estado: EstadoMissao; etapa: number } {
    return this.d.missoes[id] ?? { estado: "inativa", etapa: 0 };
  }

  definirMissao(id: string, estado: EstadoMissao, etapa = 0): void {
    this.d.missoes[id] = { estado, etapa };
    this.avisar(`missao:${id}`);
  }

  /** Capacidade do filtro instalado, em segundos. */
  capacidadeFiltro(): number {
    const e = CFG.epi;
    const base = [0, e.filtroBasico, e.filtroNivel2, e.filtroNivel3][this.d.upgrades.filtro];
    return base + (this.d.upgrades.cilindroExtra ? e.cilindroExtra : 0);
  }

  capacidadeRoupa(): number {
    return this.d.upgrades.roupaReforcada ? CFG.epi.roupaReforcada : CFG.epi.roupaMaxima;
  }

  carregar(d: DadosJogo): void {
    this.d = { ...dadosIniciais(), ...d };
    this.avisar("carregado");
  }
}
