import { Color3, Constants, DynamicTexture, GlowLayer, Mesh, MeshBuilder, StandardMaterial, VertexData, type Scene, type Vector3 } from "@babylonjs/core";
import type { AreaDef } from "./tipos";

/**
 * Horizonte da superfície (seção 5.2): cidade em ruínas até cerca de 2 km em volta da área jogável, chão de
 * areia até lá, montanhas ao fundo e um céu em degradê; à noite, a luz piscando a nordeste.
 *
 * Tudo é gerado aqui por código com semente fixa (nada modelado à mão) e desenhado sem luz: cada pedaço tem
 * um material emissivo cuja cor é misturada, a cada quadro, com a cor do céu conforme a distância da câmera.
 * É a névoa do horizonte, mais rala que a da cena (que esconderia tudo além de ~1 km) e mais densa na
 * tempestade. A mesma técnica serve ao WebGPU e ao WebGL2.
 *
 * Custo: ~40 malhas estáticas (a maioria fora do campo de visão a cada quadro), ~25 mil triângulos.
 */

type Cor = [number, number, number];
type Ret = { x0: number; x1: number; z0: number; z1: number };

/** Névoa do horizonte: fração do céu na cor de um pedaço a `d` metros da câmera. */
const DENSIDADE_HORIZONTE = 0.00062;
/** Mínimo de névoa: a cidade é vista através da poeira da parede de tempestade. */
const NEVOA_MINIMA = 0.28;
/** Raio da cidade em volta do centro do mapa: com a câmera na borda oposta, fica abaixo do maxZ de 2500 m. */
const RAIO_CIDADE = 1900;
const FAIXAS = [900, 1400, RAIO_CIDADE];
const SETORES = 8;
/** Luz a nordeste: rumo de 45° (norte = +Z, leste = +X) a partir do centro do mapa. */
const DIST_LUZ_NE = 1550;

function aleatorio(semente: number): () => number {
  let s = semente >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Ruído suave 2D (valor) para agrupar a cidade em bairros e desenhar as cristas das montanhas. */
function ruido(x: number, z: number): number {
  const h = (i: number, j: number) => {
    const s = Math.sin(i * 127.1 + j * 311.7) * 43758.5453;
    return s - Math.floor(s);
  };
  const i = Math.floor(x), j = Math.floor(z);
  const fx = x - i, fz = z - j;
  const u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
  const a = h(i, j), b = h(i + 1, j), c = h(i, j + 1), d = h(i + 1, j + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

/** Acumula quadriláteros com cor por vértice e vira uma malha só. */
class Lote {
  pos: number[] = [];
  cor: number[] = [];
  ind: number[] = [];

  quad(a: Cor, b: Cor, c: Cor, d: Cor, ca: number, cb = ca, cc = ca, cd = ca): void {
    const n = this.pos.length / 3;
    this.pos.push(...a, ...b, ...c, ...d);
    for (const k of [ca, cb, cc, cd]) this.cor.push(k, k, k, 1);
    this.ind.push(n, n + 1, n + 2, n, n + 2, n + 3);
  }

  get vazio(): boolean {
    return this.ind.length === 0;
  }

  malha(nome: string, cena: Scene): Mesh {
    const vd = new VertexData();
    vd.positions = this.pos;
    vd.indices = this.ind;
    vd.colors = this.cor;
    const m = new Mesh(nome, cena);
    vd.applyToMesh(m);
    m.isPickable = false;
    return m;
  }
}

interface Pedaco {
  malhas: Mesh[];
  mat: StandardMaterial;
  cor: Cor;
  /** Centro (x, z) para a distância à câmera; ausente nos pedaços que seguem a câmera (montanhas, céu). */
  cx?: number;
  cz?: number;
  /** Névoa fixa (pedaços que seguem a câmera). */
  nevoa?: number;
}

export class Horizonte {
  private pedacos: Pedaco[] = [];
  private luzNE: { malha: Mesh; mat: StandardMaterial } | null = null;
  private ceu: { malha: Mesh; mat: StandardMaterial } | null = null;
  private readonly centro: { x: number; z: number };

  constructor(private cena: Scene, def: AreaDef, qualidade: "alta" | "media") {
    const lim = def.limiteJogavel!;
    this.centro = { x: (lim.x0 + lim.x1) / 2, z: (lim.z0 + lim.z1) / 2 };
    const t = def.terreno;
    const borda: Ret = t
      ? { x0: t.x0, x1: t.x0 + t.passo * (t.nx - 1), z0: t.z0, z1: t.z0 + t.passo * (t.nz - 1) }
      : { x0: lim.x0 - 60, x1: lim.x1 + 60, z0: lim.z0 - 60, z1: lim.z1 + 60 };
    const altura = (x: number, z: number) => {
      if (!t) return 0;
      const i = Math.min(t.nx - 1, Math.max(0, Math.round((x - t.x0) / t.passo)));
      const j = Math.min(t.nz - 1, Math.max(0, Math.round((z - t.z0) / t.passo)));
      return t.alturas[j * t.nx + i];
    };
    this.construirChao(borda, altura);
    this.construirCidade(borda, qualidade);
    this.construirMontanhas();
    this.construirCeu();
    this.construirLuzNordeste();
    for (const camada of cena.effectLayers) {
      if (!(camada instanceof GlowLayer)) continue;
      for (const p of this.pedacos) for (const m of p.malhas) camada.addExcludedMesh(m);
      if (this.ceu) camada.addExcludedMesh(this.ceu.malha);
    }
  }

  private material(nome: string): StandardMaterial {
    const m = new StandardMaterial(`horizonte_${nome}`, this.cena);
    m.disableLighting = true;
    m.diffuseColor = Color3.Black();
    m.specularColor = Color3.Black();
    m.backFaceCulling = false;
    m.fogEnabled = false;
    return m;
  }

  private adicionar(nome: string, lote: Lote, cor: Cor, extra: Partial<Pedaco> = {}): Pedaco | null {
    if (lote.vazio) return null;
    const mat = this.material(nome);
    const malha = lote.malha(`horizonte_${nome}`, this.cena);
    malha.material = mat;
    if (extra.nevoa === undefined) malha.freezeWorldMatrix();
    const p: Pedaco = { malhas: [malha], mat, cor, ...extra };
    this.pedacos.push(p);
    return p;
  }

  /** Raio, a partir do centro, em que um raio de ângulo `a` sai do retângulo `r`. */
  private saidaDoRet(r: Ret, a: number): number {
    const dx = Math.sin(a), dz = Math.cos(a);
    const tx = dx > 0 ? (r.x1 - this.centro.x) / dx : dx < 0 ? (r.x0 - this.centro.x) / dx : Infinity;
    const tz = dz > 0 ? (r.z1 - this.centro.z) / dz : dz < 0 ? (r.z0 - this.centro.z) / dz : Infinity;
    return Math.min(tx, tz);
  }

  /** Chão de areia da borda do terreno até além da cidade, em fatias por setor e faixa de distância. */
  private construirChao(borda: Ret, altura: (x: number, z: number) => number): void {
    const passosAng = 24;
    const raios = [0, ...FAIXAS.slice(0, -1), 2350];
    for (let s = 0; s < SETORES; s++) {
      for (let f = 0; f < raios.length - 1; f++) {
        const lote = new Lote();
        let somaX = 0, somaZ = 0, n = 0;
        for (let k = 0; k < passosAng; k++) {
          const a0 = ((s + k / passosAng) / SETORES) * Math.PI * 2;
          const a1 = ((s + (k + 1) / passosAng) / SETORES) * Math.PI * 2;
          const ponto = (a: number, r: number, y: number): Cor => [this.centro.x + Math.sin(a) * r, y, this.centro.z + Math.cos(a) * r];
          // a primeira faixa começa 2 m para dentro da borda do terreno, na altura dele (sem degrau)
          const rin0 = f === 0 ? this.saidaDoRet(borda, a0) - 2 : raios[f];
          const rin1 = f === 0 ? this.saidaDoRet(borda, a1) - 2 : raios[f];
          const yin = (a: number, r: number) => (f === 0 ? altura(this.centro.x + Math.sin(a) * r, this.centro.z + Math.cos(a) * r) - 0.4 : this.yChao(r));
          const p0 = ponto(a0, rin0, yin(a0, rin0)), p1 = ponto(a1, rin1, yin(a1, rin1));
          const p2 = ponto(a1, raios[f + 1], this.yChao(raios[f + 1])), p3 = ponto(a0, raios[f + 1], this.yChao(raios[f + 1]));
          const v = (a: number) => 0.92 + 0.08 * ruido(a * 9, f * 3.1);
          lote.quad(p0, p1, p2, p3, v(a0), v(a1), v(a1), v(a0));
          somaX += p0[0] + p2[0];
          somaZ += p0[2] + p2[2];
          n += 2;
        }
        this.adicionar(`chao_${s}_${f}`, lote, [0.6, 0.53, 0.41], { cx: somaX / n, cz: somaZ / n });
      }
    }
  }

  /** Altura do chão de fora: desce devagar dos morros da borda até o nível da planície. */
  private yChao(r: number): number {
    return -3 + 6 * Math.exp(-r / 900);
  }

  /** Prédios em ruínas: caixas com topo quebrado, agrupadas em bairros, maiores e mais raras ao longe. */
  private construirCidade(borda: Ret, qualidade: "alta" | "media"): void {
    const rnd = aleatorio(20261108);
    const lotes = new Map<string, { lote: Lote; sx: number; sz: number; n: number }>();
    const margem = 25;
    const total = qualidade === "alta" ? 2600 : 1700;
    for (let i = 0; i < total; i++) {
      const a = rnd() * Math.PI * 2;
      const r = Math.sqrt(rnd()) * RAIO_CIDADE;
      const x = this.centro.x + Math.sin(a) * r, z = this.centro.z + Math.cos(a) * r;
      if (x > borda.x0 - margem && x < borda.x1 + margem && z > borda.z0 - margem && z < borda.z1 + margem) continue;
      // bairros (ruído em escala de ~350 m) e uma avenida larga vazia ao longo do leito do rio, a leste e oeste
      const bairro = ruido(x / 350 + 11, z / 350 - 7);
      if (rnd() > bairro * bairro * 1.9) continue;
      if (Math.abs(z - 203) < 70 && rnd() < 0.85) continue;
      const fx = 1 + r / 1300;
      const largura = (10 + rnd() * 24) * fx, prof = (10 + rnd() * 24) * fx;
      let alt = (7 + Math.pow(rnd(), 2.2) * 60) * (0.8 + 0.5 * bairro) * Math.min(1.6, fx);
      if (rnd() < 0.04) alt *= 1.9;
      const f = FAIXAS.findIndex((v) => r < v);
      const s = Math.floor((((a / (Math.PI * 2)) % 1) + 1) % 1 * SETORES);
      const chave = `${s}_${f}`;
      if (!lotes.has(chave)) lotes.set(chave, { lote: new Lote(), sx: 0, sz: 0, n: 0 });
      const g = lotes.get(chave)!;
      g.sx += x;
      g.sz += z;
      g.n++;
      const y0 = this.yChao(r) - 2;
      this.predio(g.lote, x, z, largura, prof, y0, y0 + 2 + alt, rnd() * Math.PI, rnd, [0.3, 0.2, 0.12][f]);
    }
    for (const [chave, g] of lotes) {
      const f = Number(chave.split("_")[1]);
      this.adicionar(`cidade_${chave}`, g.lote, [0.36, 0.33, 0.29].map((v) => v * (1 - f * 0.06)) as Cor, { cx: g.sx / g.n, cz: g.sz / g.n });
    }
  }

  /** Um prédio: caixa girada, topo inclinado ou com um canto desabado; sombra pela cor dos vértices. */
  private predio(l: Lote, x: number, z: number, w: number, d: number, y0: number, y1: number, giro: number, rnd: () => number, amp: number): void {
    const c = Math.cos(giro), s = Math.sin(giro);
    const p = (u: number, v: number, y: number): Cor => [x + u * c - v * s, y, z + u * s + v * c];
    const hw = w / 2, hd = d / 2;
    // topo: cada canto numa altura (quebrado) ou reto
    const quebrado = rnd() < 0.55;
    const tops = [0, 1, 2, 3].map(() => (quebrado ? y1 - rnd() * Math.min(12, (y1 - y0) * 0.35) : y1));
    const cantos: [number, number][] = [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]];
    // luz do sol vindo de (0.4, 1, -0.5): faces para +x e -z mais claras
    const tom = 1 - amp * (0.15 + 0.2 * rnd());
    for (let k = 0; k < 4; k++) {
      const [u0, v0] = cantos[k], [u1, v1] = cantos[(k + 1) % 4];
      const nx = (v1 - v0), nz = -(u1 - u0);
      const len = Math.hypot(nx, nz) || 1;
      const wx = (nx * c - nz * s) / len, wz = (nx * s + nz * c) / len;
      const luz = 0.5 + 0.5 * Math.max(-1, Math.min(1, wx * 0.62 - wz * 0.78));
      const k1 = tom * (1 - amp * (1 - luz));
      l.quad(p(u0, v0, y0), p(u1, v1, y0), p(u1, v1, tops[(k + 1) % 4]), p(u0, v0, tops[k]), k1 * 0.97, k1 * 0.97, k1, k1);
    }
    l.quad(p(-hw, -hd, tops[0]), p(hw, -hd, tops[1]), p(hw, hd, tops[2]), p(-hw, hd, tops[3]), tom);
    // bloco menor em cima de parte dos prédios altos (caixa d'água, andar recuado ou resto de andar)
    if (y1 - y0 > 25 && rnd() < 0.45) {
      const ww = w * (0.3 + rnd() * 0.3), dd = d * (0.3 + rnd() * 0.3);
      const ou = (rnd() - 0.5) * (w - ww), ov = (rnd() - 0.5) * (d - dd);
      const yb = Math.min(...tops) - 0.5, yt = yb + 3 + rnd() * 9;
      const q: [number, number][] = [[ou - ww / 2, ov - dd / 2], [ou + ww / 2, ov - dd / 2], [ou + ww / 2, ov + dd / 2], [ou - ww / 2, ov + dd / 2]];
      for (let k = 0; k < 4; k++) {
        const [u0, v0] = q[k], [u1, v1] = q[(k + 1) % 4];
        l.quad(p(u0, v0, yb), p(u1, v1, yb), p(u1, v1, yt), p(u0, v0, yt), tom * (k % 2 ? 1 - amp * 0.6 : 1));
      }
    }
  }

  /** Duas cordilheiras em anel que acompanham a câmera: montanhas altas ao norte e a oeste, morros no resto. */
  private construirMontanhas(): void {
    const aneis: { r: number; base: number; alt: (a: number) => number; cor: Cor; nevoa: number; amp: number }[] = [
      {
        r: 2380, base: -90, cor: [0.42, 0.42, 0.44], nevoa: 0.66, amp: 0.12,
        alt: (a) => {
          // a = 0 é o norte, PI/2 o leste: mais altas entre noroeste e norte
          const peso = 0.35 + 0.65 * Math.max(0, Math.cos(a + 0.7));
          const crista = ruido(a * 5.1, 1.3) * 0.6 + ruido(a * 13.7, 4.2) * 0.3 + ruido(a * 41, 9.1) * 0.1;
          return 40 + peso * (90 + 230 * crista);
        },
      },
      {
        r: 2250, base: -80, cor: [0.5, 0.45, 0.38], nevoa: 0.56, amp: 0.1,
        alt: (a) => 18 + 55 * (ruido(a * 8.3, 7.7) * 0.7 + ruido(a * 29, 2.2) * 0.3) * (0.5 + 0.5 * Math.max(0, Math.cos(a - 2.4))),
      },
    ];
    const N = 240;
    for (const [i, an] of aneis.entries()) {
      const lote = new Lote();
      for (let k = 0; k < N; k++) {
        const a0 = (k / N) * Math.PI * 2, a1 = ((k + 1) / N) * Math.PI * 2;
        const h0 = an.alt(a0), h1 = an.alt(a1);
        const p = (a: number, y: number): Cor => [Math.sin(a) * an.r, y, Math.cos(a) * an.r];
        // encosta voltada para o sol (leste) mais clara
        const k0 = 1 - an.amp * (0.5 - 0.5 * Math.sin(a0)), k1 = 1 - an.amp * (0.5 - 0.5 * Math.sin(a1));
        lote.quad(p(a0, an.base), p(a1, an.base), p(a1, h1), p(a0, h0), k0, k1, k1 * 1.03, k0 * 1.03);
      }
      const ped = this.adicionar(`montanhas_${i}`, lote, an.cor, { nevoa: an.nevoa });
      if (ped) {
        ped.malhas[0].infiniteDistance = true;
        ped.malhas[0].alwaysSelectAsActiveMesh = true;
      }
    }
  }

  /** Céu em degradê (meia esfera que acompanha a câmera): a cor de fundo no horizonte, mais fria no alto. */
  private construirCeu(): void {
    const ceu = MeshBuilder.CreateSphere("horizonte_ceu", { diameter: 4900, segments: 12, slice: 0.6, sideOrientation: Mesh.DOUBLESIDE }, this.cena);
    const pos = ceu.getVerticesData("position")!;
    const cores: number[] = [];
    for (let i = 0; i < pos.length; i += 3) {
      const h = Math.max(0, pos[i + 1] / 2450);
      const k = Math.pow(h, 0.6);
      cores.push(1 - 0.1 * k, 1 - 0.06 * k, 1 + 0.06 * k, 1);
    }
    ceu.setVerticesData("color", cores);
    const mat = this.material("ceu");
    ceu.material = mat;
    ceu.infiniteDistance = true;
    ceu.alwaysSelectAsActiveMesh = true;
    ceu.isPickable = false;
    this.ceu = { malha: ceu, mat };
  }

  /** Luz piscando a nordeste, no alto de uma torre distante: só aparece quando a cena está escura. */
  private construirLuzNordeste(): void {
    const a = Math.PI / 4;
    const x = this.centro.x + Math.sin(a) * DIST_LUZ_NE, z = this.centro.z + Math.cos(a) * DIST_LUZ_NE;
    const torre = new Lote();
    const y0 = this.yChao(DIST_LUZ_NE) - 2;
    const rnd = aleatorio(45);
    this.predio(torre, x, z, 22, 18, y0, y0 + 95, 0.3, rnd, 0.2);
    this.adicionar("torre_ne", torre, [0.34, 0.31, 0.28], { cx: x, cz: z });
    // núcleo (o brilho da cena o espalha) e um halo aditivo virado para a câmera, legível a 1,5 km
    const malha = MeshBuilder.CreateSphere("horizonte_luz_ne", { diameter: 12, segments: 6 }, this.cena);
    malha.position.set(x, y0 + 102, z);
    const mat = new StandardMaterial("horizonte_luz_ne", this.cena);
    mat.disableLighting = true;
    mat.emissiveColor = new Color3(1, 0.86, 0.6);
    mat.fogEnabled = false;
    malha.material = mat;
    malha.isPickable = false;
    const halo = MeshBuilder.CreatePlane("horizonte_luz_ne_halo", { size: 90 }, this.cena);
    halo.parent = malha;
    halo.billboardMode = Mesh.BILLBOARDMODE_ALL;
    const tex = new DynamicTexture("horizonte_halo", 64, this.cena, false);
    const ctx = tex.getContext() as CanvasRenderingContext2D;
    const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(0.18, "rgba(255,255,255,0.35)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 64, 64);
    tex.update();
    const mh = new StandardMaterial("horizonte_luz_ne_halo", this.cena);
    mh.disableLighting = true;
    mh.emissiveColor = new Color3(1, 0.8, 0.5);
    mh.opacityTexture = tex;
    mh.alphaMode = Constants.ALPHA_ADD;
    mh.fogEnabled = false;
    mh.backFaceCulling = false;
    halo.material = mh;
    halo.isPickable = false;
    malha.setEnabled(false);
    this.luzNE = { malha, mat };
  }

  /** Mistura cada pedaço com a cor do céu pela distância à câmera; `poeira` (0 a 1) engrossa a névoa. */
  atualizar(tempo: number, camera: Vector3, poeira: number): void {
    const fundo = this.cena.clearColor, nevoa = this.cena.fogColor;
    const ceu: Cor = [(fundo.r + nevoa.r) / 2, (fundo.g + nevoa.g) / 2, (fundo.b + nevoa.b) / 2];
    // brilho do dia: a cor da névoa de dia tem luminância ~0,85; à noite cai para ~0,04
    const lum = 0.3 * nevoa.r + 0.59 * nevoa.g + 0.11 * nevoa.b;
    const brilho = Math.min(1.15, Math.max(0.05, lum / 0.85));
    const escondido = poeira > 0.55;
    const extra = 1 - Math.pow(1 - Math.min(1, poeira / 0.55), 2);
    for (const p of this.pedacos) {
      for (const m of p.malhas) m.setEnabled(!escondido);
      if (escondido) continue;
      let k = p.nevoa ?? 0;
      if (p.nevoa === undefined) {
        const d = Math.hypot(p.cx! - camera.x, p.cz! - camera.z);
        k = Math.max(NEVOA_MINIMA, 1 - Math.exp(-Math.pow(DENSIDADE_HORIZONTE * d, 2)));
      }
      k = k + (1 - k) * extra;
      p.mat.emissiveColor.set(
        p.cor[0] * brilho * (1 - k) + ceu[0] * k,
        p.cor[1] * brilho * (1 - k) + ceu[1] * k,
        p.cor[2] * brilho * (1 - k) + ceu[2] * k,
      );
    }
    if (this.ceu) {
      this.ceu.mat.emissiveColor.set(fundo.r, fundo.g, fundo.b);
    }
    if (this.luzNE) {
      const noite = brilho < 0.3 && poeira < 0.3;
      // dois lampejos curtos a cada 2,6 s, como um farol de obstáculo
      const fase = tempo % 2.6;
      const aceso = fase < 0.18 || (fase > 0.42 && fase < 0.6);
      this.luzNE.malha.setEnabled(noite && aceso);
    }
  }

  dispose(): void {
    for (const p of this.pedacos) {
      for (const m of p.malhas) m.dispose();
      p.mat.dispose();
    }
    this.pedacos = [];
    if (this.ceu) {
      this.ceu.malha.dispose();
      this.ceu.mat.dispose();
    }
    if (this.luzNE) {
      this.luzNE.malha.dispose(false, true);
      this.luzNE.mat.dispose();
    }
  }
}
