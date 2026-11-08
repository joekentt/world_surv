import { Matrix, Vector3 } from "@babylonjs/core";
import * as RecastCore from "@recast-navigation/core";
import { NavMeshQuery, type NavMesh, type OffMeshConnectionParams } from "@recast-navigation/core";
import { generateTiledNavMesh } from "@recast-navigation/generators";
import { CFG } from "../config";
import { Jogador } from "../player/jogador";
import type { AreaDef, Solido, Terreno } from "../world/tipos";

type V3 = [number, number, number];

/** Rota mais curta pelo navmesh entre dois pontos de um mundo. */
export interface RotaNav {
  ok: boolean;
  motivo?: string;
  /** Comprimento em 3D (m), somando os trechos retos da rota (inclui as escadas, na vertical). */
  comprimento: number;
  /** Comprimento no plano XZ (m): é o que vale para o tempo correndo, que é medido na horizontal. */
  horizontal: number;
  /** Pontos da rota (cantos do caminho reto), do início projetado no navmesh ao fim projetado. */
  pontos: V3[];
  /** Escadas e cordas usadas (ligações fora da malha). */
  escadas: number;
  /** Início e fim projetados no navmesh. */
  inicio?: V3;
  fim?: V3;
}

export interface InfoNavmesh { mundo: string; ms: number; triangulos: number; tiles: number; poligonos: number; ligacoes: number; ligacoesNaMalha: number; cs: number }

/**
 * Resolução da grade de voxels por mundo. A cápsula (raio 0,3, altura 1,7, degrau 0,35, rampa 45°)
 * vira raio, altura e degrau em células; `ch` de 5 cm guarda o degrau de 0,35 m inteiro.
 */
const RESOLUCAO: Record<string, { cs: number; tileSize: number }> = {
  subsolo: { cs: 0.15, tileSize: 96 },
  superficie_aberta: { cs: 0.3, tileSize: 128 },
};
const CH = 0.05;
/** Espaço entre as fatias internas das caixas (menor que a altura da cápsula, mesmo inclinado). */
const FATIA = 1.0;
const PEDACO = 16;

/** Faces da caixa unitária: quatro cantos (índices de ±x, ±y, ±z) por face. */
const CANTOS: V3[] = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]];
const FACES = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]];

/** Junta triângulos garantindo a normal (pela regra do Recast, cross(v1-v0, v2-v0)) no sentido de `fora`. */
function triangulo(pos: number[], ind: number[], a: V3, b: V3, c: V3, fora: V3): void {
  const e0 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e1 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const n = [e0[1] * e1[2] - e0[2] * e1[1], e0[2] * e1[0] - e0[0] * e1[2], e0[0] * e1[1] - e0[1] * e1[0]];
  const base = pos.length / 3;
  const [p, q] = n[0] * fora[0] + n[1] * fora[1] + n[2] * fora[2] >= 0 ? [b, c] : [c, b];
  pos.push(...a, ...p, ...q);
  ind.push(base, base + 1, base + 2);
}

/** Caixa de colisão de um sólido com a mesma rotação do construtor (yaw, pitch, roll do Babylon). */
function caixa(pos: number[], ind: number[], s: Solido, oco: [number, number] | null): void {
  const d = s.d ?? CFG.movimento.profundidadeFaixaAntiga;
  const rot = Matrix.RotationYawPitchRoll(((s.ry ?? 0) * Math.PI) / 180, ((s.rx ?? 0) * Math.PI) / 180, ((s.rz ?? 0) * Math.PI) / 180);
  const centro = new Vector3(s.x, s.y, s.z ?? 0);
  const v = CANTOS.map(([i, j, k]) => {
    const p = Vector3.TransformCoordinates(new Vector3((i * s.w) / 2, (j * s.h) / 2, (k * d) / 2), rot).addInPlace(centro);
    return [p.x, p.y, p.z] as V3;
  });
  for (const f of FACES) {
    const m = [0, 1, 2].map((e) => f.reduce((acc, i) => acc + v[i][e], 0) / 4);
    const fora: V3 = [m[0] - centro.x, m[1] - centro.y, m[2] - centro.z];
    triangulo(pos, ind, v[f[0]], v[f[1]], v[f[2]], fora);
    triangulo(pos, ind, v[f[0]], v[f[2]], v[f[3]], fora);
  }
  // O Recast só rasteriza superfícies: o oco de uma caixa alta (ou o chão dentro dela) viraria uma ilha
  // andável. Fatias horizontais internas a cada FATIA m deixam o oco baixo demais para a cápsula.
  // Caixas mais baixas que a cápsula não têm oco andável. Fatias longas são partidas em pedaços de até
  // PEDACO m: triângulos compridos incham os blocos de busca do gerador e multiplicam o tempo de geração.
  if (!oco) return;
  const c = Vector3.TransformNormal(Vector3.Up(), rot);
  const cima: V3 = [c.x, c.y, c.z];
  const nx = Math.ceil(s.w / PEDACO), nz = Math.ceil(d / PEDACO);
  const canto = (u: number, y: number, w: number): V3 => {
    const p = Vector3.TransformCoordinates(new Vector3(-s.w / 2 + (u * s.w) / nx, y, -d / 2 + (w * d) / nz), rot).addInPlace(centro);
    return [p.x, p.y, p.z];
  };
  for (let y = oco[0] + FATIA; y < oco[1] - 0.05; y += FATIA) {
    for (let i = 0; i < nx; i++) {
      for (let k = 0; k < nz; k++) {
        const q = [canto(i, y, k), canto(i + 1, y, k), canto(i + 1, y, k + 1), canto(i, y, k + 1)];
        triangulo(pos, ind, q[0], q[1], q[2], cima);
        triangulo(pos, ind, q[0], q[2], q[3], cima);
      }
    }
  }
}

type Caixa3 = { min: V3; max: V3 };

/** Caixa alinhada aos eixos que envolve o sólido (com a rotação). */
function envoltoria(s: Solido): Caixa3 {
  const d = s.d ?? CFG.movimento.profundidadeFaixaAntiga;
  const rot = Matrix.RotationYawPitchRoll(((s.ry ?? 0) * Math.PI) / 180, ((s.rx ?? 0) * Math.PI) / 180, ((s.rz ?? 0) * Math.PI) / 180);
  const min: V3 = [Infinity, Infinity, Infinity], max: V3 = [-Infinity, -Infinity, -Infinity];
  for (const [i, j, k] of CANTOS) {
    const p = Vector3.TransformCoordinates(new Vector3((i * s.w) / 2, (j * s.h) / 2, (k * d) / 2), rot);
    const v = [p.x + s.x, p.y + s.y, p.z + (s.z ?? 0)];
    for (let e = 0; e < 3; e++) { min[e] = Math.min(min[e], v[e]); max[e] = Math.max(max[e], v[e]); }
  }
  return { min, max };
}

/**
 * Faixa de altura (no referencial da caixa) em que o oco precisa de fatias: das superfícies de outras
 * peças dentro da caixa (topos de sólidos e o terreno) até a altura da cápsula acima delas. Nulo quando
 * nada fica dentro do oco ou a caixa é mais baixa que a cápsula. Caixas giradas recebem a altura toda.
 */
function faixasDoOco(solidos: Solido[], terrenos: Terreno[]): (Caixa3 & { oco: [number, number] | null })[] {
  const caixas = solidos.map(envoltoria);
  const H = CFG.movimento.alturaCapsula;
  return solidos.map((s, n) => {
    const b = caixas[n];
    if (s.h <= H) return { ...b, oco: null };
    if (s.rx || s.ry || s.rz) return { ...b, oco: [-s.h / 2, s.h / 2] };
    let lo = Infinity, hi = -Infinity;
    const dentro = (y: number) => { if (y > b.min[1] - 0.01 && y < b.max[1]) { lo = Math.min(lo, y); hi = Math.max(hi, y); } };
    for (let m = 0; m < caixas.length; m++) {
      const o = caixas[m];
      if (m === n || o.max[0] <= b.min[0] || o.min[0] >= b.max[0] || o.max[2] <= b.min[2] || o.min[2] >= b.max[2]) continue;
      dentro(o.max[1]);
    }
    for (const t of terrenos) {
      const i0 = Math.max(0, Math.floor((b.min[0] - t.x0) / t.passo)), i1 = Math.min(t.nx - 1, Math.ceil((b.max[0] - t.x0) / t.passo));
      const j0 = Math.max(0, Math.floor((b.min[2] - t.z0) / t.passo)), j1 = Math.min(t.nz - 1, Math.ceil((b.max[2] - t.z0) / t.passo));
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) dentro(t.alturas[j * t.nx + i]);
    }
    if (lo === Infinity) return { ...b, oco: null };
    return { ...b, oco: [Math.max(lo, b.min[1]) - s.y, Math.min(hi + H + FATIA, b.max[1]) - s.y] };
  });
}

/** Terreno em grade com as mesmas diagonais do construtor, todos os triângulos virados para cima. */
function terreno(pos: number[], ind: number[], t: Terreno): void {
  const p = (i: number, j: number): V3 => [t.x0 + i * t.passo, t.alturas[j * t.nx + i], t.z0 + j * t.passo];
  const cima: V3 = [0, 1, 0];
  for (let j = 0; j < t.nz - 1; j++) {
    for (let i = 0; i < t.nx - 1; i++) {
      const a = p(i, j), b = p(i + 1, j), c = p(i, j + 1), d = p(i + 1, j + 1);
      triangulo(pos, ind, b, d, c, cima);
      triangulo(pos, ind, a, b, c, cima);
    }
  }
}

/** Escadas de mão e cordas viram ligações fora da malha entre o ponto de encaixe embaixo e a saída no topo. */
function ligacoes(areas: AreaDef[]): OffMeshConnectionParams[] {
  return areas.flatMap((a) => (a.escadas ?? []).map((e) => {
    const { base, topo } = Jogador.pontosEscada(e);
    return { startPosition: { x: base.x, y: base.y, z: base.z }, endPosition: { x: topo.x, y: topo.y, z: topo.z }, radius: 0.6, bidirectional: true };
  }));
}

let recastPronto: Promise<void> | null = null;

/**
 * Navmesh em vários níveis dos mundos da revisão 2 (subsolo e superfície), gerado com o Recast
 * (@recast-navigation, o mesmo WASM do plugin do Babylon) a partir da geometria de colisão das
 * áreas: sólidos sem `semColisao` e o terreno em grade. Gerado sob demanda, um por mundo, com
 * todas as áreas do mundo (não só as carregadas). A navegação em faixa da revisão 1 (mundo "vila")
 * continua em `Navegacao`.
 */
export class NavegacaoNiveis {
  private malhas = new Map<string, { navMesh: NavMesh; query: NavMeshQuery; info: InfoNavmesh }>();

  constructor(private areasDoMundo: (mundo: string) => AreaDef[]) {}

  async construir(mundo: string): Promise<InfoNavmesh> {
    const existente = this.malhas.get(mundo);
    if (existente) return existente.info;
    recastPronto ??= (RecastCore as unknown as { init: () => Promise<void> }).init();
    await recastPronto;
    const areas = this.areasDoMundo(mundo).filter((a) => a.limites);
    if (!areas.length) throw new Error(`mundo sem áreas 3D: ${mundo}`);
    const t0 = performance.now();
    const pos: number[] = [], ind: number[] = [];
    const terrenos = areas.flatMap((a) => (a.terreno ? [a.terreno] : []));
    for (const t of terrenos) terreno(pos, ind, t);
    const solidos = areas.flatMap((a) => a.solidos.filter((s) => !s.semColisao));
    const ocos = faixasDoOco(solidos, terrenos);
    solidos.forEach((s, i) => caixa(pos, ind, s, ocos[i].oco));
    // limites do navmesh: a união das caixas das áreas (o terreno passa dela e é cortado)
    const min: V3 = [Infinity, Infinity, Infinity], max: V3 = [-Infinity, -Infinity, -Infinity];
    for (const a of areas) for (let e = 0; e < 3; e++) { min[e] = Math.min(min[e], a.limites!.min[e]); max[e] = Math.max(max[e], a.limites!.max[e]); }
    const { cs, tileSize } = RESOLUCAO[mundo] ?? { cs: 0.2, tileSize: 96 };
    const M = CFG.movimento;
    const offMesh = ligacoes(areas);
    const r = generateTiledNavMesh(pos, ind, {
      bounds: [min, max], cs, ch: CH, tileSize,
      walkableSlopeAngle: M.rampaMaximaGraus,
      walkableHeight: Math.ceil(M.alturaCapsula / CH),
      walkableClimb: Math.floor(M.degrauMaximo / CH + 1e-6),
      walkableRadius: Math.ceil(M.raioCapsula / cs - 1e-6),
      maxEdgeLen: Math.round(12 / cs), maxSimplificationError: 1.3, minRegionArea: 8, mergeRegionArea: 20, maxVertsPerPoly: 6,
      detailSampleDist: 6, detailSampleMaxError: 1, offMeshConnections: offMesh,
    });
    if (!r.success) throw new Error(`navmesh de ${mundo}: ${r.error}`);
    let tiles = 0, poligonos = 0, ligacoesNaMalha = 0;
    for (let i = 0; i < r.navMesh.getMaxTiles(); i++) {
      const h = r.navMesh.getTile(i).header();
      if (!h) continue;
      tiles++;
      poligonos += h.polyCount();
      ligacoesNaMalha += h.offMeshConCount();
    }
    const query = new NavMeshQuery(r.navMesh, { maxNodes: 65535 });
    const info: InfoNavmesh = { mundo, ms: Math.round(performance.now() - t0), triangulos: ind.length / 3, tiles, poligonos, ligacoes: offMesh.length, ligacoesNaMalha, cs };
    this.malhas.set(mundo, { navMesh: r.navMesh, query, info });
    return info;
  }

  /** Ponto do navmesh mais próximo, dentro da caixa de busca (meias medidas em X, Y e Z). */
  projetar(mundo: string, p: V3, ext: V3 = [1.5, 1, 1.5]): V3 | null {
    const m = this.malhas.get(mundo);
    if (!m) return null;
    const r = m.query.findClosestPoint({ x: p[0], y: p[1], z: p[2] }, { halfExtents: { x: ext[0], y: ext[1], z: ext[2] } });
    return r.success && r.polyRef ? [r.point.x, r.point.y, r.point.z] : null;
  }

  /**
   * Rota mais curta de `a` a `b` (cada um projetado no navmesh dentro de `ext`). Falha se algum ponto
   * não estiver no navmesh ou se o caminho achado parar antes do destino (ilhas desligadas).
   * O A* do Detour mede pelos centros dos polígonos e não garante o caminho mais curto: a busca é feita
   * nos dois sentidos e fica a mais curta (a de volta, invertida).
   */
  rota(mundo: string, a: V3, b: V3, ext: V3 = [1.5, 1, 1.5]): RotaNav {
    const vazia = (motivo: string): RotaNav => ({ ok: false, motivo, comprimento: 0, horizontal: 0, pontos: [], escadas: 0 });
    const m = this.malhas.get(mundo);
    if (!m) return vazia(`navmesh de ${mundo} não construído`);
    const pa = this.projetar(mundo, a, ext), pb = this.projetar(mundo, b, ext);
    if (!pa) return vazia(`início (${a.join(", ")}) fora do navmesh`);
    if (!pb) return vazia(`destino (${b.join(", ")}) fora do navmesh`);
    const ida = this.caminho(m.query, pa, pb);
    const volta = this.caminho(m.query, pb, pa);
    volta.pontos.reverse();
    const r = !volta.ok || (ida.ok && ida.comprimento <= volta.comprimento) ? ida : volta;
    return { ...r, inicio: pa, fim: pb };
  }

  private caminho(query: NavMeshQuery, pa: V3, pb: V3): RotaNav {
    const v = (p: V3) => ({ x: p[0], y: p[1], z: p[2] });
    const r = query.computePath(v(pa), v(pb), { halfExtents: { x: 0.2, y: 0.5, z: 0.2 }, maxPathPolys: 16384, maxStraightPathPoints: 4096 });
    if (!r.success || !r.path.length) return { ok: false, motivo: `sem caminho: ${r.error?.name ?? "?"}`, comprimento: 0, horizontal: 0, pontos: [], escadas: 0 };
    const pontos = r.path.map((p) => [p.x, p.y, p.z] as V3);
    let comprimento = 0, horizontal = 0, escadas = 0;
    for (let i = 1; i < pontos.length; i++) {
      const [x0, y0, z0] = pontos[i - 1], [x1, y1, z1] = pontos[i];
      const h = Math.hypot(x1 - x0, z1 - z0);
      comprimento += Math.hypot(h, y1 - y0);
      // trecho de escada: quase vertical (ligação fora da malha)
      if (Math.abs(y1 - y0) > 1.5 && h < 2) escadas++;
      else horizontal += h;
    }
    const ultimo = pontos[pontos.length - 1];
    const falta = Math.hypot(ultimo[0] - pb[0], ultimo[1] - pb[1], ultimo[2] - pb[2]);
    if (falta > 0.5) return { ok: false, motivo: `caminho parcial: parou a ${falta.toFixed(1)} m do destino`, comprimento, horizontal, pontos, escadas };
    return { ok: true, comprimento, horizontal, pontos, escadas };
  }
}
