import { CFG } from "../config";
import type { Estado } from "../core/estado";

export type Turno = "primeiro_turno" | "segundo_turno" | "vigilia" | "descanso";

/** Ciclo artificial de luz da vila. As lâmpadas baixam no turno de descanso. */
export class TurnosDeLuz {
  aoMudar: ((t: Turno) => void) | null = null;
  fatorLuz = 1;
  /** Multiplicador de velocidade do relógio (testes). */
  acelerar = 1;

  constructor(private estado: Estado) {}

  get turno(): Turno {
    return CFG.turnos.ordem[this.estado.d.turno % CFG.turnos.ordem.length] as Turno;
  }

  /** Fração do turno atual (0 a 1). */
  get fracao(): number {
    return this.estado.d.relogioTurno / CFG.turnos.duracaoTurno;
  }

  avancar(): void {
    this.estado.d.turno = (this.estado.d.turno + 1) % CFG.turnos.ordem.length;
    if (this.estado.d.turno === 0) this.estado.d.dia += 1;
    this.estado.d.relogioTurno = 0;
    this.aoMudar?.(this.turno);
    this.estado.avisar("turno");
  }

  atualizar(dt: number): void {
    this.estado.d.relogioTurno += dt * this.acelerar;
    if (this.estado.d.relogioTurno >= CFG.turnos.duracaoTurno) this.avancar();
    const alvo = this.turno === "descanso" ? CFG.turnos.luzDescanso : 1;
    this.fatorLuz += (alvo - this.fatorLuz) * Math.min(1, dt * 0.6);
  }
}
