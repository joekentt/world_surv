import "@babylonjs/loaders/glTF";
import {
  Animation,
  AnimationGroup,
  LoadAssetContainerAsync,
  Quaternion,
  TransformNode,
  Vector3,
  type AssetContainer,
  type Scene,
} from "@babylonjs/core";

const BASE = import.meta.env.BASE_URL + "assets/";

/** Cache de contêineres GLB: cada arquivo é baixado uma vez por cena. */
export class Carregador {
  private conteineres = new Map<string, Promise<AssetContainer>>();
  constructor(private cena: Scene) {}

  carregar(caminho: string): Promise<AssetContainer> {
    let p = this.conteineres.get(caminho);
    if (!p) {
      p = LoadAssetContainerAsync(BASE + caminho, this.cena);
      this.conteineres.set(caminho, p);
    }
    return p;
  }

  descartar(caminho: string): void {
    const p = this.conteineres.get(caminho);
    if (!p) return;
    this.conteineres.delete(caminho);
    p.then((c) => c.dispose()).catch(() => undefined);
  }
}

interface Repouso {
  p: Vector3;
  q: Quaternion;
}

function repousoDosNos(nos: TransformNode[]): Map<string, Repouso> {
  const m = new Map<string, Repouso>();
  for (const n of nos) {
    m.set(n.name, { p: n.position.clone(), q: (n.rotationQuaternion ?? Quaternion.FromEulerVector(n.rotation)).clone() });
  }
  return m;
}

/**
 * Biblioteca de animações compartilhada (animacoes.glb). As ações foram geradas no rig de um
 * corpo neutro; para cada corpo diferente, as chaves são adaptadas ao repouso dos ossos de destino:
 *   rotação: q_destino = R_destino · R_origem⁻¹ · q_chave
 *   posição: p_destino = P_destino + (p_chave − P_origem) · escala
 */
export class BibliotecaAnimacoes {
  private grupos = new Map<string, AnimationGroup>();
  private repousoOrigem = new Map<string, Repouso>();
  private cachePorCorpo = new Map<string, Map<string, Animation[]>>();

  static async carregar(carregador: Carregador): Promise<BibliotecaAnimacoes> {
    const c = await carregador.carregar("personagens/animacoes.glb");
    const b = new BibliotecaAnimacoes();
    b.repousoOrigem = repousoDosNos(c.transformNodes);
    for (const g of c.animationGroups) b.grupos.set(g.name, g);
    return b;
  }

  get nomes(): string[] {
    return [...this.grupos.keys()];
  }

  /** Animações adaptadas para um corpo (chave = id do personagem), calculadas uma vez. */
  private animacoesPara(corpo: string, repousoDestino: Map<string, Repouso>): Map<string, Animation[]> {
    let porAcao = this.cachePorCorpo.get(corpo);
    if (porAcao) return porAcao;
    porAcao = new Map();
    const escalaPelvis = (() => {
      const o = this.repousoOrigem.get("pelvis");
      const d = repousoDestino.get("pelvis");
      return o && d && o.p.length() > 0 ? d.p.length() / o.p.length() : 1;
    })();
    for (const [nome, grupo] of this.grupos) {
      const lista: Animation[] = [];
      for (const ta of grupo.targetedAnimations) {
        const alvo = ta.target as TransformNode;
        const o = this.repousoOrigem.get(alvo.name);
        const d = repousoDestino.get(alvo.name);
        if (!o || !d) continue;
        const a = ta.animation;
        if (a.targetProperty === "scaling") continue;
        const nova = new Animation(`${nome}:${alvo.name}`, a.targetProperty, a.framePerSecond, a.dataType, Animation.ANIMATIONLOOPMODE_CYCLE);
        if (a.targetProperty === "rotationQuaternion") {
          const delta = d.q.multiply(Quaternion.Inverse(o.q));
          nova.setKeys(a.getKeys().map((k) => ({ frame: k.frame, value: delta.multiply(k.value as Quaternion) })));
        } else if (a.targetProperty === "position") {
          const esc = alvo.name === "pelvis" ? escalaPelvis : 1;
          nova.setKeys(
            a.getKeys().map((k) => ({ frame: k.frame, value: d.p.add((k.value as Vector3).subtract(o.p).scale(esc)) })),
          );
        } else continue;
        (nova as unknown as { _alvo: string })._alvo = alvo.name;
        lista.push(nova);
      }
      porAcao.set(nome, lista);
    }
    this.cachePorCorpo.set(corpo, porAcao);
    return porAcao;
  }

  /** Cria os grupos de animação para uma instância de personagem já colocada na cena. */
  criarGrupos(cena: Scene, corpo: string, raiz: TransformNode, repousoCorpo: Map<string, Repouso>): Map<string, AnimationGroup> {
    const porAcao = this.animacoesPara(corpo, repousoCorpo);
    const nos = new Map<string, TransformNode>();
    for (const n of raiz.getChildTransformNodes(false)) nos.set(n.name, n);
    const grupos = new Map<string, AnimationGroup>();
    for (const [nome, anims] of porAcao) {
      const g = new AnimationGroup(`${raiz.name}:${nome}`, cena);
      for (const a of anims) {
        const alvo = nos.get((a as unknown as { _alvo: string })._alvo);
        if (alvo) g.addTargetedAnimation(a, alvo);
      }
      grupos.set(nome, g);
    }
    return grupos;
  }

  static repouso(c: AssetContainer): Map<string, Repouso> {
    return repousoDosNos(c.transformNodes);
  }
}
