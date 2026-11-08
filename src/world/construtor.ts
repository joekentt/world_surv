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
  if (def.limites || def.solidos.length === 0 || def.solidos.some((s) => s.z !== undefined)) return [];
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
  rocha: [0.3, 0.27, 0.24], concreto: [0.46, 0.44, 0.4], metal: [0.33, 0.34, 0.36], ferrugem: [0.45, 0.26, 0.15],
  madeira: [0.42, 0.28, 0.16], chapa_azul: [0.28, 0.36, 0.42], chapa_verde: [0.3, 0.4, 0.32], chapa_clara: [0.58, 0.55, 0.48],
  lona_vermelha: [0.62, 0.18, 0.12], lona_azul: [0.15, 0.3, 0.55], lona_amarela: [0.75, 0.58, 0.18], lona_verde: [0.22, 0.45, 0.25],
  pano: [0.7, 0.66, 0.58], grade: [0.16, 0.16, 0.17], escuro: [0.07, 0.065, 0.06],
  // superfícies úmidas e escuras do Duto Norte (a lanterna do capacete bate de perto sem estourar)
  rocha_escura: [0.19, 0.17, 0.15], madeira_escura: [0.17, 0.11, 0.07], concreto_escuro: [0.21, 0.2, 0.18],
  // azulejos antigos da Estação Aurora
  azulejo_creme: [0.6, 0.57, 0.48], azulejo_verde: [0.22, 0.4, 0.36], azulejo_azul: [0.24, 0.34, 0.46],
};

/** Materiais que emitem luz própria (lâmpadas, vitrais, facho), sem depender das luzes da cena. */
const EMISSIVOS: Record<string, { cor: [number, number, number]; alfa?: number }> = {
  luz_ambar: { cor: [1.0, 0.62, 0.26] }, luz_fria: { cor: [0.62, 1.0, 0.92] }, luz_dourada: { cor: [1.0, 0.88, 0.58] },
  luz_fraca: { cor: [0.55, 0.32, 0.16] }, janela: { cor: [0.85, 0.5, 0.2] },
  vitral_azul: { cor: [0.2, 0.45, 1.0] }, vitral_vermelho: { cor: [1.0, 0.25, 0.15] }, vitral_verde: { cor: [0.3, 0.9, 0.4] },
  facho: { cor: [1.0, 0.86, 0.55], alfa: 0.16 },
  // Duto Norte e Caverna da Fenda: musgo luminoso e água escorrendo (brilho fraco no escuro)
  musgo: { cor: [0.1, 0.46, 0.3] }, musgo_fraco: { cor: [0.035, 0.17, 0.12] }, agua: { cor: [0.08, 0.15, 0.18] },
  // Boca do Poço: luz vermelha de alerta e névoa da descontaminação
  luz_alerta: { cor: [1.0, 0.08, 0.04] }, nevoa: { cor: [0.32, 0.13, 0.12], alfa: 0.045 },
};

function materialBloqueio(cena: Scene, nome: string): StandardMaterial {
  const id = `bloqueio_${nome}`;
  const existente = cena.getMaterialByName(id) as StandardMaterial | null;
  if (existente) return existente;
  const m = new StandardMaterial(id, cena);
  const em = EMISSIVOS[nome];
  if (em) {
    m.diffuseColor = Color3.Black();
    m.emissiveColor = new Color3(...em.cor);
    m.disableLighting = true;
    if (em.alfa !== undefined) {
      m.alpha = em.alfa;
      m.backFaceCulling = false;
    }
    return m;
  }
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
  const visiveis: Mesh[] = [];

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
      visiveis.push(caixa);
    }
    if (s.semColisao) {
      if (!caixa.isVisible) caixa.dispose();
      continue;
    }
    const corpo = new PhysicsAggregate(caixa, PhysicsShapeType.BOX, { mass: 0, friction: 0.6 }, cena);
    if (s.semCamera) corpo.shape.filterMembershipMask = CAMADA_SEM_CAMERA;
    corpos.push(corpo);
  }
  // Blocos visíveis de mesmo material viram uma malha só (centenas de caixas custariam uma chamada de
  // desenho cada). As caixas originais ficam ocultas, só com o corpo físico.
  const porMaterial = new Map<string, Mesh[]>();
  for (const c of visiveis) {
    const nome = c.material!.name;
    if (!porMaterial.has(nome)) porMaterial.set(nome, []);
    porMaterial.get(nome)!.push(c);
  }
  for (const [nome, lista] of porMaterial) {
    const unida = lista.length > 1 ? Mesh.MergeMeshes(lista, false, true) : null;
    if (!unida) {
      malhas.push(...lista);
      continue;
    }
    unida.name = `${def.id}_${nome}`;
    unida.parent = raiz;
    unida.isPickable = false;
    unida.receiveShadows = true;
    unida.freezeWorldMatrix();
    malhas.push(unida);
    for (const c of lista) {
      if (corpos.some((k) => k.transformNode === c)) c.isVisible = false;
      else c.dispose();
    }
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
    // nasce apagada: a Iluminacao acende só as mais próximas (acesas todas de uma vez, os shaders
    // recompilados estouram o limite de blocos de uniformes do WebGL2)
    luz.setEnabled(false);
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
