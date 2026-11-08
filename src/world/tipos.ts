/** Formato das áreas em content/areas/<id>.json. Coordenadas em metros; x e y são o centro das caixas. */
/**
 * Caixa de colisão: centro (x, y, z), tamanhos w (X), h (Y), d (Z) e rotação opcional em graus (rampas).
 * `semColisao`: só visual (lonas, lâmpadas, facho de luz, vigas altas); não entra na física nem no piso mínimo.
 */
export interface Solido { x: number; y: number; w: number; h: number; d?: number; z?: number; mat?: string; invisivel?: boolean; semCamera?: boolean; semColisao?: boolean; rx?: number; ry?: number; rz?: number; }
/** Peça de kit: módulo `m` na posição (x, y, z), guinada `r` e, opcionais, arfagem `rx` e rolagem `rz` (graus, Euler como as caixas). */
export interface Peca { m: string; x: number; y: number; z?: number; r?: number; rx?: number; rz?: number; e?: number | [number, number, number]; }
/** Escada de mão ou corda: base em (x, z), de y0 a y1; yaw é para onde o jogador olha ao subir (graus no JSON). */
export interface EscadaDef { x: number; z?: number; y0: number; y1: number; tipo: "escada" | "corda"; yaw?: number; }
/** Saída para outra área ou mundo; `z` posiciona a interação nas áreas 3D (revisão 2). */
export interface Saida { x: number; y: number; z?: number; destino: string; entrada: string; rotulo: string; tipo?: "porta" | "eclusa"; }
export interface Luz { x: number; y: number; z?: number; cor: [number, number, number]; i: number; alcance?: number; tipo?: "ponto" | "foco"; piscar?: boolean; }
export interface Coletavel { id: string; item: string; x: number; y: number; qtd?: number; }
export interface Interativo { id: string; tipo: string; x: number; y: number; z?: number; rotulo?: string; npc?: string; [k: string]: unknown; }
export interface ZonaPerigo { x0: number; x1: number; tipo: "poeira" | "radiacao"; intensidade: number; }

export type Vec3 = [number, number, number];
export interface Ponto3 { x: number; y: number; z: number }

/**
 * Terreno com relevo (superfície, revisão 2): grade regular de alturas a partir de (x0, z0), com `passo` m
 * entre amostras; `alturas` em linhas de z crescente, nx amostras por linha. Vira malha com colisão de malha.
 */
export interface Terreno { x0: number; z0: number; passo: number; nx: number; nz: number; alturas: number[] }

export interface AreaDef {
  id: string;
  nome: string;
  mundo: string;
  estetica: string;
  kit?: string;
  /**
   * Kits de decoração da revisão 2 (`public/assets/kits/<nome>.glb`): as `pecas` vêm deles e os blocos continuam
   * visíveis (os que uma peça substitui vêm marcados `invisivel` pelo gerador, com a colisão mantida).
   */
  kits?: string[];
  /** Extensão em X. Nas áreas 3D é derivada de `limites` pelo gerador. */
  inicio: number;
  fim: number;
  /**
   * Caixa da área em 3D (revisão 2). Define a área atual do jogador e a distância de carregamento.
   * Áreas sem limites são as faixas lineares da revisão 1.
   */
  limites?: { min: Vec3; max: Vec3 };
  superficie?: boolean;
  solidos: Solido[];
  escadas?: EscadaDef[];
  pecas?: Peca[];
  fundo?: Peca[];
  saidas?: Saida[];
  entradas?: Record<string, { x: number; y: number; z?: number; yaw?: number }>;
  zonasCamera?: { tipo: "tunel" | "vila" | "superficie"; min: [number, number, number]; max: [number, number, number] }[];
  zonaPadrao?: "tunel" | "vila" | "superficie";
  luzes?: Luz[];
  coletaveis?: Coletavel[];
  interativos?: Interativo[];
  zonas?: ZonaPerigo[];
  marcos?: { id: string; x: number; rotulo: string }[];
  terreno?: Terreno;
  /**
   * Limite jogável da superfície (revisão 2): a área que o tem monta o horizonte (cidade, montanhas, céu) e a
   * parede de tempestade em volta dele enquanto estiver carregada.
   */
  limiteJogavel?: { x0: number; x1: number; z0: number; z1: number };
  /** Interiores que servem de abrigo na superfície (dreno do filtro reduzido, fase 3). */
  abrigos?: { id: string; min: Vec3; max: Vec3 }[];
}
