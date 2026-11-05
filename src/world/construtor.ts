import {
  Color3, Matrix, Mesh, MeshBuilder, PhysicsAggregate, PhysicsShapeType, PointLight, SpotLight, StandardMaterial,
  TransformNode, Vector3, type AbstractMesh, type AssetContainer, type Light, type Scene,
} from "@babylonjs/core";
import type { Carregador } from "../core/carregador";
import { CFG } from "../config";
import type { AreaDef, Peca, Solido } from "./tipos";

/** Camada de colisão de sólidos que barram o personagem mas não a câmera (paredes invisíveis). */
export const CAMADA_SEM_CAMERA = 1 << 4;

/**
 * Áreas da revisão 1 são faixas lineares sem profundidade definida (nenhum sólido tem z).
 * Com o movimento livre, recebem paredes invisíveis nas laterais até serem refeitas na fase 2.
 */
function bordasFaixaAntiga(def: AreaDef): Solido[] {
  if (def.solidos.length === 0 || def.solidos.some((s) => s.z !== undefined)) return [];
  const meia = CFG.movimento.profundidadeFaixaAntiga / 2;
  const base = Math.min(...def.solidos.map((s) => s.y - s.h / 2)) - 2;
  const topo = Math.max(...def.solidos.map((s) => s.y + s.h / 2)) + 30;
  const largura = def.fim - def.inicio;
  const comum = { x: (def.inicio + def.fim) / 2, y: (base + topo) / 2, w: largura, h: topo - base, d: 1, invisivel: true, semCamera: true };
  return [{ ...comum, z: meia + 0.5 }, { ...comum, z: -meia - 0.5 }];
}

export interface AreaCarregada {
  def: AreaDef;
  raiz: TransformNode;
  corpos: PhysicsAggregate[];
  luzes: Light[];
  malhas: AbstractMesh[];
  dispose(): void;
}

const CORES_BLOQUEIO: Record<string, [number, number, number]> = {
  chao: [0.32, 0.3, 0.27], parede: [0.42, 0.4, 0.36], plataforma: [0.5, 0.36, 0.2], caixa: [0.55, 0.45, 0.3],
};

function materialBloqueio(cena: Scene, nome: string): StandardMaterial {
  const id = `bloqueio_${nome}`;
  const existente = cena.getMaterialByName(id) as StandardMaterial | null;
  if (existente) return existente;
  const m = new StandardMaterial(id, cena);
  const c = CORES_BLOQUEIO[nome] ?? [0.45, 0.45, 0.45];
  m.diffuseColor = new Color3(...c);
  m.specularColor = new Color3(0.05, 0.05, 0.05);
  return m;
}

/** Módulos de kit já carregados: nome do módulo -> malha-fonte (oculta) para instanciar. */
export async function fontesDoKit(carregador: Carregador, kit: string): Promise<Map<string, Mesh[]>> {
  const c: AssetContainer = await carregador.carregar(`kits/${kit}.glb`);
  const mapa = (c as unknown as { _fontes?: Map<string, Mesh[]> })._fontes;
  if (mapa) return mapa;
  const fontes = new Map<string, Mesh[]>();
  c.addAllToScene();
  for (const no of c.rootNodes[0]?.getChildren() ?? []) {
    const malhas: Mesh[] = [];
    const coletar = (n: TransformNode) => {
      if (n instanceof Mesh && n.getTotalVertices() > 0) malhas.push(n);
      for (const f of n.getChildren()) coletar(f as TransformNode);
    };
    coletar(no as TransformNode);
    for (const m of malhas) {
      // Assa a conversão do glTF (raiz com escala -1 em Z) e gira 180° em Y, para que o eixo
      // X do Blender vire o X do jogo e o Y do Blender (profundidade) vire o Z do jogo.
      const mundo = m.computeWorldMatrix(true).multiply(Matrix.RotationY(Math.PI));
      m.parent = null;
      m.position.setAll(0);
      m.rotationQuaternion = null;
      m.rotation.setAll(0);
      m.scaling.setAll(1);
      m.bakeTransformIntoVertices(mundo);
      m.setEnabled(true);
      m.isVisible = false;
      m.isPickable = false;
      m.freezeNormals();
    }
    fontes.set(no.name, malhas);
  }
  (c as unknown as { _fontes?: Map<string, Mesh[]> })._fontes = fontes;
  return fontes;
}

function escala(e: Peca["e"]): Vector3 {
  if (e === undefined) return Vector3.One();
  if (typeof e === "number") return new Vector3(e, e, e);
  return new Vector3(e[0], e[1], e[2]);
}

export interface OpcoesConstrucao {
  qualidade: "alta" | "media";
  sombras?: (m: AbstractMesh) => void;
}

/** Monta uma área: colisão (caixas Havok), peças do kit instanciadas, escadas, fundo e luzes. */
export async function construirArea(cena: Scene, carregador: Carregador, def: AreaDef, op: OpcoesConstrucao): Promise<AreaCarregada> {
  const raiz = new TransformNode(`area_${def.id}`, cena);
  const corpos: PhysicsAggregate[] = [];
  const malhas: AbstractMesh[] = [];
  const luzes: Light[] = [];
  const temKit = !!def.kit;

  for (const [i, s] of [...def.solidos, ...bordasFaixaAntiga(def)].entries()) {
    const caixa = MeshBuilder.CreateBox(`${def.id}_solido_${i}`, { width: s.w, height: s.h, depth: s.d ?? CFG.movimento.profundidadeFaixaAntiga }, cena);
    caixa.position.set(s.x, s.y, s.z ?? 0);
    if (s.rx || s.ry || s.rz) caixa.rotation.set(((s.rx ?? 0) * Math.PI) / 180, ((s.ry ?? 0) * Math.PI) / 180, ((s.rz ?? 0) * Math.PI) / 180);
    caixa.parent = raiz;
    caixa.isPickable = false;
    if (temKit || s.invisivel) caixa.isVisible = false;
    else {
      caixa.material = materialBloqueio(cena, s.mat ?? "parede");
      caixa.receiveShadows = true;
      malhas.push(caixa);
    }
    const corpo = new PhysicsAggregate(caixa, PhysicsShapeType.BOX, { mass: 0, friction: 0.6 }, cena);
    if (s.semCamera) corpo.shape.filterMembershipMask = CAMADA_SEM_CAMERA;
    corpos.push(corpo);
  }

  if (def.kit) {
    const fontes = await fontesDoKit(carregador, def.kit);
    const comuns = await fontesDoKit(carregador, "comum");
    const colocar = (p: Peca, camada: string) => {
      const lista = fontes.get(p.m) ?? comuns.get(p.m);
      if (!lista) {
        console.warn(`[area ${def.id}] módulo desconhecido: ${p.m}`);
        return;
      }
      for (const fonte of lista) {
        const inst = fonte.createInstance(`${def.id}_${camada}_${p.m}`);
        inst.parent = raiz;
        inst.position.set(p.x, p.y, p.z ?? 0);
        inst.rotation.y = ((p.r ?? 0) * Math.PI) / 180;
        inst.scaling = escala(p.e);
        inst.isPickable = false;
        inst.alwaysSelectAsActiveMesh = false;
        malhas.push(inst);
        if (camada === "frente" && op.sombras) op.sombras(inst);
      }
    };
    for (const p of def.pecas ?? []) colocar(p, "frente");
    for (const p of def.fundo ?? []) colocar(p, "fundo");
  }

  for (const [i, esc] of (def.escadas ?? []).entries()) {
    const alt = esc.y1 - esc.y0;
    const yaw = ((esc.yaw ?? 0) * Math.PI) / 180;
    const grupo = new TransformNode(`${def.id}_escada_${i}`, cena);
    grupo.parent = raiz;
    grupo.position.set(esc.x, esc.y0, esc.z ?? 0);
    grupo.rotation.y = yaw;
    if (esc.tipo === "corda") {
      const corda = MeshBuilder.CreateCylinder(`${def.id}_corda_${i}`, { height: alt + 1.2, diameter: 0.06, tessellation: 6 }, cena);
      corda.position.set(0, (alt + 1.2) / 2, 0);
      corda.material = materialBloqueio(cena, "plataforma");
      corda.parent = grupo;
      malhas.push(corda);
    } else if (!temKit) {
      for (const lado of [-0.28, 0.28]) {
        const trilho = MeshBuilder.CreateBox("trilho", { width: 0.06, height: alt + 0.9, depth: 0.06 }, cena);
        trilho.position.set(lado, (alt + 0.9) / 2, -0.05);
        trilho.material = materialBloqueio(cena, "caixa");
        trilho.parent = grupo;
        malhas.push(trilho);
      }
      for (let y = 0.3; y < alt + 0.6; y += 0.35) {
        const degrau = MeshBuilder.CreateBox("degrau", { width: 0.56, height: 0.04, depth: 0.05 }, cena);
        degrau.position.set(0, y, -0.05);
        degrau.material = materialBloqueio(cena, "caixa");
        degrau.parent = grupo;
        malhas.push(degrau);
      }
    }
  }

  const maxLuzes = op.qualidade === "alta" ? 8 : 4;
  for (const [i, l] of (def.luzes ?? []).entries()) {
    const pos = new Vector3(l.x, l.y, l.z ?? -1);
    const luz = l.tipo === "foco"
      ? new SpotLight(`${def.id}_luz_${i}`, pos, new Vector3(0, -1, 0.15), Math.PI / 3, 2, cena)
      : new PointLight(`${def.id}_luz_${i}`, pos, cena);
    luz.diffuse = new Color3(...l.cor);
    luz.specular = luz.diffuse.scale(0.3);
    luz.intensity = l.i;
    luz.range = l.alcance ?? 14;
    luz.parent = raiz;
    (luz as unknown as { _base: number })._base = l.i;
    (luz as unknown as { _piscar: boolean })._piscar = !!l.piscar;
    luzes.push(luz);
  }
  void maxLuzes;

  return {
    def, raiz, corpos, luzes, malhas,
    dispose() {
      for (const c of corpos) c.dispose();
      for (const l of luzes) l.dispose();
      raiz.dispose(false, false);
    },
  };
}
