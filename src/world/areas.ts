import type { Scene } from "@babylonjs/core";
import type { Carregador } from "../core/carregador";
import { construirArea, type AreaCarregada, type OpcoesConstrucao } from "./construtor";
import { CFG } from "../config";
import type { AreaDef, Ponto3, Solido, Vec3 } from "./tipos";

const arquivos = import.meta.glob("../../content/areas/*.json", { eager: true, import: "default" }) as Record<string, AreaDef>;
export const AREAS: Record<string, AreaDef> = {};
for (const def of Object.values(arquivos)) AREAS[def.id] = def;

/** Distância (m) a partir da borda de uma área em que ela começa a carregar. */
const MARGEM_CARGA = 45;
const MARGEM_DESCARGA = 70;

/** Caixa da área: `limites` nas áreas 3D; nas faixas da revisão 1, de inicio a fim em X. */
export function caixaDaArea(def: AreaDef): { min: Vec3; max: Vec3 } {
  if (def.limites) return def.limites;
  const meia = CFG.movimento.profundidadeFaixaAntiga / 2 + 1;
  return { min: [def.inicio, -1e4, -meia], max: [def.fim, 1e4, meia] };
}

/** Distância de um ponto à caixa da área (zero dentro dela). */
export function distanciaArea(def: AreaDef, p: Ponto3): number {
  const { min, max } = caixaDaArea(def);
  const d = (v: number, a: number, b: number) => (v < a ? a - v : v > b ? v - b : 0);
  return Math.hypot(d(p.x, min[0], max[0]), d(p.y, min[1], max[1]), d(p.z, min[2], max[2]));
}

function volume(def: AreaDef): number {
  const { min, max } = caixaDaArea(def);
  return (max[0] - min[0]) * (max[1] - min[1]) * (max[2] - min[2]);
}

/**
 * Áreas do mesmo "mundo" carregam sob demanda pela distância do jogador à caixa de cada uma
 * (streaming em 3D). Caixas podem se sobrepor, como níveis empilhados: vale a menor que contém
 * o jogador. Mundos diferentes (subsolo e superfície) se ligam por saídas com transição.
 */
export class GerenciadorAreas {
  mundo = "";
  carregadas = new Map<string, AreaCarregada>();
  private carregando = new Map<string, Promise<AreaCarregada>>();
  aoCarregar: ((a: AreaCarregada) => void) | null = null;
  aoDescarregar: ((a: AreaCarregada) => void) | null = null;

  constructor(private cena: Scene, private carregador: Carregador, private opcoes: OpcoesConstrucao) {}

  areasDoMundo(mundo: string): AreaDef[] {
    return Object.values(AREAS).filter((a) => a.mundo === mundo).sort((a, b) => caixaDaArea(a).min[0] - caixaDaArea(b).min[0]);
  }

  /** Área que contém x no mundo atual. */
  /** Altura da base do sólido mais baixo entre as áreas do mundo atual. */
  pisoMinimo(): number {
    const lista = this.areasDoMundo(this.mundo);
    if (this.pisoCache?.mundo !== this.mundo) {
      const bases = lista.flatMap((a) => a.solidos.map((s) => s.y - s.h / 2));
      this.pisoCache = { mundo: this.mundo, y: bases.length ? Math.min(...bases) : 0 };
    }
    return this.pisoCache.y;
  }
  private pisoCache: { mundo: string; y: number } | null = null;

  /** Área que contém o ponto no mundo atual; com caixas sobrepostas, a de menor volume. */
  areaEm(p: Ponto3): AreaDef | null {
    let melhor: AreaDef | null = null;
    for (const a of this.areasDoMundo(this.mundo)) {
      if (distanciaArea(a, p) > 0) continue;
      if (!melhor || volume(a) < volume(melhor)) melhor = a;
    }
    return melhor;
  }

  limites(): [number, number] {
    const lista = this.areasDoMundo(this.mundo);
    return [Math.min(...lista.map((a) => a.inicio)), Math.max(...lista.map((a) => a.fim))];
  }

  /** Troca de mundo: descarrega tudo e carrega as áreas próximas do ponto. */
  async entrarMundo(mundo: string, p: Ponto3): Promise<void> {
    for (const a of this.carregadas.values()) {
      this.aoDescarregar?.(a);
      a.dispose();
    }
    this.carregadas.clear();
    this.mundo = mundo;
    await this.atualizar(p, true);
  }

  /** Chamado todo quadro (barato): inicia cargas e descargas conforme a posição. */
  async atualizar(p: Ponto3, esperar = false): Promise<void> {
    const promessas: Promise<unknown>[] = [];
    for (const def of this.areasDoMundo(this.mundo)) {
      const dist = distanciaArea(def, p);
      if (dist <= MARGEM_CARGA && !this.carregadas.has(def.id) && !this.carregando.has(def.id)) {
        const p = construirArea(this.cena, this.carregador, def, this.opcoes).then((a) => {
          this.carregando.delete(def.id);
          if (def.mundo !== this.mundo) {
            a.dispose();
            return a;
          }
          this.carregadas.set(def.id, a);
          this.aoCarregar?.(a);
          return a;
        });
        this.carregando.set(def.id, p);
        promessas.push(p);
      } else if (dist > MARGEM_DESCARGA && this.carregadas.has(def.id)) {
        const a = this.carregadas.get(def.id)!;
        this.carregadas.delete(def.id);
        this.aoDescarregar?.(a);
        a.dispose();
      }
    }
    if (esperar) await Promise.all(promessas);
  }

  /** Sólidos de todas as áreas carregadas (para checagem de teto e posicionamento). */
  solidos(): Solido[] {
    const s: Solido[] = [];
    for (const a of this.carregadas.values()) s.push(...a.def.solidos);
    return s;
  }
}
