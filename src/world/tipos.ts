/** Formato das áreas em content/areas/<id>.json. Coordenadas em metros; x e y são o centro das caixas. */
export interface Solido { x: number; y: number; w: number; h: number; d?: number; z?: number; mat?: string; invisivel?: boolean; }
export interface Peca { m: string; x: number; y: number; z?: number; r?: number; e?: number | [number, number, number]; }
export interface EscadaDef { x: number; y0: number; y1: number; tipo: "escada" | "corda"; }
export interface Saida { x: number; y: number; destino: string; entrada: string; rotulo: string; tipo?: "porta" | "eclusa"; }
export interface Luz { x: number; y: number; z?: number; cor: [number, number, number]; i: number; alcance?: number; tipo?: "ponto" | "foco"; piscar?: boolean; }
export interface Coletavel { id: string; item: string; x: number; y: number; qtd?: number; }
export interface Interativo { id: string; tipo: string; x: number; y: number; z?: number; rotulo?: string; npc?: string; [k: string]: unknown; }
export interface ZonaPerigo { x0: number; x1: number; tipo: "poeira" | "radiacao"; intensidade: number; }

export interface AreaDef {
  id: string;
  nome: string;
  mundo: string;
  estetica: string;
  kit?: string;
  inicio: number;
  fim: number;
  superficie?: boolean;
  solidos: Solido[];
  escadas?: EscadaDef[];
  pecas?: Peca[];
  fundo?: Peca[];
  saidas?: Saida[];
  entradas?: Record<string, { x: number; y: number }>;
  luzes?: Luz[];
  coletaveis?: Coletavel[];
  interativos?: Interativo[];
  zonas?: ZonaPerigo[];
  marcos?: { id: string; x: number; rotulo: string }[];
}
