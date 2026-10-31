import { MeshBuilder, Vector3, type Mesh, type Scene } from "@babylonjs/core";
import { CreateNavigationPluginAsync, type RecastNavigationJSPluginV2 } from "@babylonjs/addons/navigation";
import * as RecastCore from "@recast-navigation/core";
import * as RecastGeradores from "@recast-navigation/generators";
import type { AreaDef } from "../world/tipos";

/** Pegada (largura em X, profundidade em Z, deslocamento em Z) dos módulos que bloqueiam a passagem. */
const PEGADAS: Record<string, [number, number, number]> = {
  barraca_lona: [3.0, 1.6, 0.9], barraca_caravana: [3.3, 1.0, 0.6], sede_conselho: [8.2, 0.7, -0.2], bomba: [2.6, 1.8, 0.8],
  banco: [1.6, 0.45, 0.25], banco_madeira: [2.4, 0.5, 0.25], altar: [2.8, 1.1, 0.5], mesa: [1.4, 0.8, 0.5], cozinha: [0.8, 0.8, 0.4],
  caixote: [1.0, 1.0, 0.5], barril: [0.7, 0.7, 0.35], oficina: [2.2, 0.9, 0.5], banca_filtros: [1.6, 0.7, 0.4], coluna: [1.2, 1.2, 0],
  casa_fundo: [3.8, 2.8, 1.3], barraco_a: [3.0, 2.6, 1.3], barraco_b: [2.6, 2.6, 1.3], barraco_c: [3.4, 2.6, 1.3],
  maquina_velha: [3.4, 1.8, 1.2], muro_subidores: [6.0, 0.5, 0.2], armario_epi: [1.8, 0.6, 0.3], chuveiro: [0.4, 0.4, 0.2],
  painel_controle: [1.0, 0.4, 0.2],
};

/**
 * Malha de navegação dos NPCs, gerada pelo plugin Recast do Babylon (@babylonjs/addons) a partir
 * dos dados das áreas (piso e pegadas dos objetos), uma vez por mundo. O Recast é injetado pelo
 * npm em vez de baixado de CDN.
 */
export class Navegacao {
  private plugin: RecastNavigationJSPluginV2 | null = null;
  private mundo = "";

  constructor(private cena: Scene) {}

  async iniciar(): Promise<void> {
    // Com instância injetada o addon não chama init(): o WASM do Recast é iniciado aqui.
    await (RecastCore as unknown as { init: () => Promise<void> }).init();
    this.plugin = await CreateNavigationPluginAsync({ instance: { ...RecastCore, ...RecastGeradores } });
  }

  get pronta(): boolean {
    return !!this.plugin && this.mundo !== "";
  }

  construir(mundo: string, areas: AreaDef[]): void {
    if (!this.plugin || this.mundo === mundo) return;
    const temporarias: Mesh[] = [];
    for (const a of areas) {
      const chao = MeshBuilder.CreateBox("nav_chao", { width: a.fim - a.inicio, height: 0.2, depth: 9 }, this.cena);
      chao.position.set((a.inicio + a.fim) / 2, -0.1, 2.5);
      temporarias.push(chao);
      for (const p of a.pecas ?? []) {
        const pg = PEGADAS[p.m];
        if (!pg || (p.y ?? 0) > 0.5) continue;
        const caixa = MeshBuilder.CreateBox("nav_obst", { width: pg[0], height: 1.5, depth: pg[1] }, this.cena);
        caixa.position.set(p.x, 0.75, (p.z ?? 0) + pg[2]);
        temporarias.push(caixa);
      }
    }
    this.plugin.createNavMesh(temporarias, {
      cs: 0.15, ch: 0.1, walkableSlopeAngle: 35, walkableHeight: 16, walkableClimb: 3, walkableRadius: 2,
      maxEdgeLen: 12, maxSimplificationError: 1.3, minRegionArea: 8, mergeRegionArea: 20, maxVertsPerPoly: 6,
      detailSampleDist: 6, detailSampleMaxError: 1,
    } as never);
    for (const m of temporarias) m.dispose();
    this.mundo = mundo;
  }

  /** Caminho de (x, z) até (x, z) no plano do chão. Sem malha, devolve a linha reta. */
  caminho(x0: number, z0: number, x1: number, z1: number): Vector3[] {
    if (!this.plugin || !this.mundo) return [new Vector3(x1, 0, z1)];
    try {
      const ini = this.plugin.getClosestPoint(new Vector3(x0, 0, z0));
      const fim = this.plugin.getClosestPoint(new Vector3(x1, 0, z1));
      const pts = this.plugin.computePath(ini, fim);
      if (!pts.length) return [new Vector3(x1, 0, z1)];
      return [...pts.map((p) => new Vector3(p.x, 0, p.z)), new Vector3(x1, 0, z1)];
    } catch {
      return [new Vector3(x1, 0, z1)];
    }
  }
}
