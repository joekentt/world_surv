import type { Scene } from "@babylonjs/core";
import type { Carregador } from "../core/carregador";
import { construirArea, type AreaCarregada, type OpcoesConstrucao } from "./construtor";
import type { AreaDef, Solido } from "./tipos";

const arquivos = import.meta.glob("../../content/areas/*.json", { eager: true, import: "default" }) as Record<string, AreaDef>;
export const AREAS: Record<string, AreaDef> = {};
for (const def of Object.values(arquivos)) AREAS[def.id] = def;

/** Distância (m) a partir da borda de uma área em que ela começa a carregar. */
const MARGEM_CARGA = 45;
const MARGEM_DESCARGA = 70;

/**
 * Áreas do mesmo "mundo" são contíguas no eixo X e carregam sob demanda conforme o jogador
 * se aproxima (streaming). Mundos diferentes se ligam por saídas (portas, eclusa) com transição.
 */
export class GerenciadorAreas {
  mundo = "";
  carregadas = new Map<string, AreaCarregada>();
  private carregando = new Map<string, Promise<AreaCarregada>>();
  aoCarregar: ((a: AreaCarregada) => void) | null = null;
  aoDescarregar: ((a: AreaCarregada) => void) | null = null;

  constructor(private cena: Scene, private carregador: Carregador, private opcoes: OpcoesConstrucao) {}

  areasDoMundo(mundo: string): AreaDef[] {
    return Object.values(AREAS).filter((a) => a.mundo === mundo).sort((a, b) => a.inicio - b.inicio);
  }

  /** Área que contém x no mundo atual. */
  areaEm(x: number): AreaDef | null {
    for (const a of this.areasDoMundo(this.mundo)) if (x >= a.inicio && x < a.fim) return a;
    return null;
  }

  limites(): [number, number] {
    const lista = this.areasDoMundo(this.mundo);
    return [Math.min(...lista.map((a) => a.inicio)), Math.max(...lista.map((a) => a.fim))];
  }

  /** Troca de mundo: descarrega tudo e carrega as áreas próximas de x. */
  async entrarMundo(mundo: string, x: number): Promise<void> {
    for (const a of this.carregadas.values()) {
      this.aoDescarregar?.(a);
      a.dispose();
    }
    this.carregadas.clear();
    this.mundo = mundo;
    await this.atualizar(x, true);
  }

  /** Chamado todo quadro (barato): inicia cargas e descargas conforme a posição. */
  async atualizar(x: number, esperar = false): Promise<void> {
    const promessas: Promise<unknown>[] = [];
    for (const def of this.areasDoMundo(this.mundo)) {
      const dist = x < def.inicio ? def.inicio - x : x > def.fim ? x - def.fim : 0;
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
