import type { Jogo } from "../core/jogo";
import { avaliar, type Condicao } from "./condicoes";
import { aplicarEfeitos, type Efeito } from "./efeitos";

export interface Opcao { texto: string; se?: Condicao; efeitos?: Efeito[]; ir?: string | null; }
export interface No { falas: (string | { quem: "jogador" | "npc"; texto: string })[]; opcoes?: Opcao[]; efeitos?: Efeito[]; ir?: string; }
export interface DialogoDef { npc: string; entradas: { se?: Condicao; no: string }[]; nos: Record<string, No>; }

const arquivos = import.meta.glob("../../content/dialogos/*.json", { eager: true, import: "default" }) as Record<string, DialogoDef>;
const DIALOGOS: Record<string, DialogoDef> = {};
for (const d of Object.values(arquivos)) if ((d as DialogoDef).npc) DIALOGOS[d.npc] = d;

export function temDialogo(npc: string): boolean {
  return !!DIALOGOS[npc];
}

/** Percorre a árvore de diálogo: escolhe a entrada pela condição, mostra falas e opções, aplica efeitos. */
export class Dialogo {
  ativo = false;
  private def: DialogoDef | null = null;
  constructor(private jogo: Jogo) {}

  async iniciar(npc: string, nome: string): Promise<void> {
    const def = DIALOGOS[npc];
    if (!def || this.ativo) return;
    this.def = def;
    const entrada = def.entradas.find((e) => avaliar(e.se, this.jogo.estado));
    if (!entrada) return;
    this.ativo = true;
    this.jogo.travarParaDialogo(true);
    let noId: string | null | undefined = entrada.no;
    while (noId) noId = await this.executar(noId, nome);
    this.ativo = false;
    this.jogo.ui.dialogo.fechar();
    this.jogo.travarParaDialogo(false);
    const depois = this.jogo.depoisDoDialogo;
    this.jogo.depoisDoDialogo = null;
    depois?.();
  }

  private async executar(id: string, nome: string): Promise<string | null | undefined> {
    const no = this.def!.nos[id];
    if (!no) return null;
    for (const f of no.falas) {
      const quem = typeof f === "string" ? "npc" : f.quem;
      const texto = typeof f === "string" ? f : f.texto;
      await this.jogo.ui.dialogo.fala(quem === "npc" ? nome : "Você", texto, quem === "jogador");
    }
    aplicarEfeitos(this.jogo, no.efeitos);
    const opcoes = (no.opcoes ?? []).filter((o) => avaliar(o.se, this.jogo.estado));
    if (!opcoes.length) return no.ir ?? null;
    const i = await this.jogo.ui.dialogo.escolher(opcoes.map((o) => o.texto));
    const o = opcoes[i];
    aplicarEfeitos(this.jogo, o.efeitos);
    return o.ir === undefined ? null : o.ir;
  }
}
