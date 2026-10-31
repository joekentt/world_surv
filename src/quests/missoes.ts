import type { EstadoMissao } from "../core/estado";
import type { Jogo } from "../core/jogo";
import { avaliar, type Condicao } from "./condicoes";
import { aplicarEfeitos, type Efeito } from "./efeitos";

export interface Gatilho { evento: string; se?: Condicao; efeitos: Efeito[]; }
export interface MissaoDef {
  id: string;
  titulo: string;
  tipo: "principal" | "opcional";
  ordem: number;
  resumo: string;
  etapas: { texto: string; local?: string }[];
  conclusao: string;
  gatilhos?: Gatilho[];
}

const arquivos = import.meta.glob("../../content/missoes/*.json", { eager: true, import: "default" }) as Record<string, MissaoDef>;
export const MISSOES: MissaoDef[] = Object.values(arquivos).sort((a, b) => a.ordem - b.ordem);

/** Missões: textos do diário, avisos na tela e gatilhos por evento (coleta, volta da superfície, área). */
export class Missoes {
  constructor(private jogo: Jogo) {
    jogo.estado.ouvir((chave) => this.evento(chave));
  }

  def(id: string): MissaoDef | undefined {
    return MISSOES.find((m) => m.id === id);
  }

  evento(nome: string): void {
    for (const m of MISSOES) {
      for (const g of m.gatilhos ?? []) {
        if (g.evento === nome && avaliar(g.se, this.jogo.estado)) aplicarEfeitos(this.jogo, g.efeitos);
      }
    }
  }

  anunciar(id: string, estado: EstadoMissao, etapa: number): void {
    const m = this.def(id);
    if (!m) return;
    const j = this.jogo;
    if (estado === "concluida") {
      j.hud.aviso("Missão concluída", m.titulo, m.conclusao);
      j.audio.tocar("coleta", 0.5, 0.7);
    } else if (estado === "ativa") {
      j.hud.aviso(etapa === 0 ? (m.tipo === "principal" ? "Nova missão" : "Nova tarefa") : m.titulo, etapa === 0 ? m.titulo : "", m.etapas[etapa]?.texto ?? "");
    }
  }

  /** Linhas do diário: missões ativas primeiro, depois as concluídas. */
  diario(): { titulo: string; texto: string; tipo: string; estado: EstadoMissao }[] {
    const e = this.jogo.estado;
    const lista = MISSOES.map((m) => ({ m, s: e.missao(m.id) })).filter((x) => x.s.estado !== "inativa");
    return lista
      .sort((a, b) => (a.s.estado === b.s.estado ? a.m.ordem - b.m.ordem : a.s.estado === "ativa" ? -1 : 1))
      .map(({ m, s }) => ({
        titulo: m.titulo,
        texto: s.estado === "concluida" ? m.conclusao : m.etapas[s.etapa]?.texto ?? m.resumo,
        tipo: m.tipo,
        estado: s.estado,
      }));
  }
}
