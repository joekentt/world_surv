import type { Entrada } from "../core/entrada";
import type { Hud } from "../ui/hud";

export interface Interacao {
  id: string;
  x: number;
  y: number;
  raio?: number;
  rotulo: string | (() => string);
  acao: () => void;
  ativo?: () => boolean;
  /** Prioridade quando duas interações se sobrepõem (maior vence). */
  prioridade?: number;
}

/** Mostra o aviso da interação mais próxima do jogador e executa a ação ao apertar o botão. */
export class SistemaInteracao {
  private lista = new Map<string, Interacao>();
  atual: Interacao | null = null;
  bloqueado = false;

  constructor(private entrada: Entrada, private hud: Hud, private posicao: () => { x: number; y: number }) {}

  adicionar(i: Interacao): void {
    this.lista.set(i.id, i);
  }

  remover(id: string): void {
    this.lista.delete(id);
  }

  removerPrefixo(prefixo: string): void {
    for (const k of [...this.lista.keys()]) if (k.startsWith(prefixo)) this.lista.delete(k);
  }

  atualizar(): void {
    if (this.bloqueado) {
      this.hud.mostrarAviso(null, false);
      this.atual = null;
      return;
    }
    const p = this.posicao();
    let melhor: Interacao | null = null;
    let melhorNota = Infinity;
    for (const i of this.lista.values()) {
      if (i.ativo && !i.ativo()) continue;
      const dx = Math.abs(i.x - p.x);
      const dy = Math.abs(i.y - p.y);
      if (dx > (i.raio ?? 1.3) || dy > 1.6) continue;
      const nota = dx - (i.prioridade ?? 0) * 10;
      if (nota < melhorNota) {
        melhor = i;
        melhorNota = nota;
      }
    }
    this.atual = melhor;
    this.hud.mostrarAviso(melhor ? (typeof melhor.rotulo === "function" ? melhor.rotulo() : melhor.rotulo) : null, this.entrada.usandoGamepad);
    if (melhor && this.entrada.apertou("interagir")) melhor.acao();
  }
}
