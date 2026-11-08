import {
  Color3, Color4, DynamicTexture, GlowLayer, Mesh, ParticleSystem, StandardMaterial, Texture, Vector3, VertexData, type Scene,
} from "@babylonjs/core";

/**
 * Parede de tempestade no limite jogável da superfície (seção 5.2): uma cortina de poeira em três camadas
 * (duas no WebGL2), afastadas 4, 20 e 48 m do limite, com textura de ruído gerada aqui e rolada a cada quadro
 * (o vento corre ao longo da parede e a poeira sobe). A densidade vem da cor dos vértices: quase opaca junto
 * ao chão e rala no alto, até sumir no céu. Perto da parede, um sistema leve de partículas solta rajadas de
 * poeira. A colisão do limite continua nas caixas invisíveis da área (`tools/areas/superficie.py`).
 *
 * Custo: 12 malhas (8 no WebGL2) de poucos triângulos, um material por camada sem luz nem névoa da cena e
 * duas texturas 256 x 128 compartilhadas; nada de shader próprio, então roda igual em WebGPU e WebGL2.
 */

type Lim = { x0: number; x1: number; z0: number; z1: number };

/** Camadas: afastamento do limite (m), altura do topo, metros de parede por repetição da textura e cor. */
const CAMADAS = [
  { o: 4, h: 190, u: 70, v: 38, cor: [0.74, 0.62, 0.45] },
  { o: 20, h: 260, u: 110, v: 60, cor: [0.79, 0.68, 0.51] },
  { o: 48, h: 340, u: 160, v: 90, cor: [0.85, 0.76, 0.6] },
];
/** Alturas das linhas de vértices acima do chão e a densidade em cada uma (0 a 1). */
const PERFIL: [number, number][] = [[-25, 1], [4, 0.97], [16, 0.92], [40, 0.86], [80, 0.62], [130, 0.32], [1, 0]];

/** Ruído de valor periódico (em fBm) para a textura da poeira: emenda nas bordas, sem costura visível. */
function texturaPoeira(cena: Scene, nome: string, semente: number, contraste: number, minimo: number): DynamicTexture {
  const W = 256, H = 128;
  const tex = new DynamicTexture(nome, { width: W, height: H }, cena, true);
  const ctx = tex.getContext() as CanvasRenderingContext2D;
  const img = ctx.createImageData(W, H);
  const h = (i: number, j: number, p: number, q: number) => {
    const s = Math.sin((((i % p) + p) % p) * 127.1 + (((j % q) + q) % q) * 311.7 + semente * 74.7) * 43758.5453;
    return s - Math.floor(s);
  };
  const valor = (x: number, y: number, p: number, q: number) => {
    const i = Math.floor(x), j = Math.floor(y);
    const fx = x - i, fy = y - j;
    const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
    const a = h(i, j, p, q), b = h(i + 1, j, p, q), c = h(i, j + 1, p, q), d = h(i + 1, j + 1, p, q);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  };
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      let n = 0, amp = 0.55, tot = 0;
      for (let o = 0; o < 5; o++) {
        const p = 4 << o, q = 2 << o;
        n += valor((x / W) * p, (y / H) * q, p, q) * amp;
        tot += amp;
        amp *= 0.5;
      }
      n /= tot;
      const k = Math.min(1, Math.max(0, 0.5 + (n - 0.5) * contraste));
      const v = Math.round(255 * (minimo + (1 - minimo) * k));
      const idx = (y * W + x) * 4;
      img.data[idx] = img.data[idx + 1] = img.data[idx + 2] = v;
      img.data[idx + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  tex.update(false);
  tex.wrapU = Texture.WRAP_ADDRESSMODE;
  tex.wrapV = Texture.WRAP_ADDRESSMODE;
  return tex;
}

export class ParedeTempestade {
  private malhas: Mesh[] = [];
  private mats: { mat: StandardMaterial; cor: number[] }[] = [];
  private tons: DynamicTexture;
  private densidade: DynamicTexture;
  private rajadas: ParticleSystem;
  private readonly lim: Lim;

  constructor(private cena: Scene, lim: Lim, qualidade: "alta" | "media", altura: (x: number, z: number) => number) {
    this.lim = lim;
    // tons: variação de claro e escuro da poeira; densidade: buracos e rolos mais densos (canal de opacidade)
    this.tons = texturaPoeira(cena, "tempestade_tons", 3, 1.6, 0.7);
    this.densidade = texturaPoeira(cena, "tempestade_densidade", 11, 2.2, 0.3);
    this.densidade.getAlphaFromRGB = true;
    const camadas = qualidade === "alta" ? CAMADAS : [CAMADAS[0], CAMADAS[2]];
    for (const [i, c] of camadas.entries()) {
      const mat = new StandardMaterial(`tempestade_${i}`, cena);
      mat.disableLighting = true;
      mat.diffuseColor = Color3.Black();
      mat.specularColor = Color3.Black();
      mat.emissiveColor = new Color3(c.cor[0], c.cor[1], c.cor[2]);
      mat.diffuseTexture = this.tons; // sem luz, a cor final é emissiva × textura × cor dos vértices
      mat.opacityTexture = this.densidade;
      mat.backFaceCulling = false;
      mat.fogEnabled = false;
      this.mats.push({ mat, cor: c.cor });
      const x0 = lim.x0 - c.o, x1 = lim.x1 + c.o, z0 = lim.z0 - c.o, z1 = lim.z1 + c.o;
      // um lado por malha, para a ordenação das transparências funcionar de qualquer ponto do mapa
      const lados: [number, number, number, number][] = [[x0, z0, x1, z0], [x1, z0, x1, z1], [x1, z1, x0, z1], [x0, z1, x0, z0]];
      let s0 = 0;
      for (const [j, [ax, az, bx, bz]] of lados.entries()) {
        const m = this.lado(`tempestade_${i}_${j}`, ax, az, bx, bz, s0 + i * 37, c, altura);
        s0 += Math.hypot(bx - ax, bz - az);
        m.material = mat;
        this.malhas.push(m);
      }
    }
    for (const camada of cena.effectLayers) if (camada instanceof GlowLayer) for (const m of this.malhas) camada.addExcludedMesh(m);
    this.rajadas = this.criarRajadas(qualidade);
  }

  /** Faixa vertical de um lado do retângulo, com vértices a cada ~24 m e linhas nas alturas do PERFIL. */
  private lado(nome: string, ax: number, az: number, bx: number, bz: number, s0: number, c: typeof CAMADAS[number], altura: (x: number, z: number) => number): Mesh {
    const comp = Math.hypot(bx - ax, bz - az);
    const n = Math.max(2, Math.ceil(comp / 24));
    const pos: number[] = [], uv: number[] = [], cor: number[] = [], ind: number[] = [];
    const linhas = PERFIL.length;
    for (let k = 0; k <= n; k++) {
      const t = k / n;
      const x = ax + (bx - ax) * t, z = az + (bz - az) * t;
      const chao = altura(x, z);
      for (let r = 0; r < linhas; r++) {
        const [dy, dens] = PERFIL[r];
        const y = r === linhas - 1 ? chao + c.h : chao + dy;
        pos.push(x, y, z);
        uv.push((s0 + comp * t) / c.u, (y - chao) / c.v);
        cor.push(1, 1, 1, dens);
      }
    }
    for (let k = 0; k < n; k++) {
      for (let r = 0; r < linhas - 1; r++) {
        const a = k * linhas + r, b = (k + 1) * linhas + r;
        ind.push(a, b, b + 1, a, b + 1, a + 1);
      }
    }
    const vd = new VertexData();
    vd.positions = pos;
    vd.indices = ind;
    vd.uvs = uv;
    vd.colors = cor;
    const m = new Mesh(nome, this.cena);
    vd.applyToMesh(m);
    m.hasVertexAlpha = true;
    m.isPickable = false;
    m.freezeWorldMatrix();
    return m;
  }

  /** Rajadas de poeira junto à parede mais próxima do jogador (só a menos de 60 m dela). */
  private criarRajadas(qualidade: "alta" | "media"): ParticleSystem {
    const ps = new ParticleSystem("tempestade_rajadas", qualidade === "alta" ? 160 : 70, this.cena);
    const t = new DynamicTexture("tempestade_rajada", 64, this.cena, false);
    const ctx = t.getContext() as CanvasRenderingContext2D;
    const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, "rgba(255,255,255,0.9)");
    g.addColorStop(0.5, "rgba(255,255,255,0.35)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 64, 64);
    t.update();
    t.hasAlpha = true;
    ps.particleTexture = t;
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.emitter = new Vector3(0, 0, 0);
    ps.minSize = 6;
    ps.maxSize = 16;
    ps.minLifeTime = 3;
    ps.maxLifeTime = 5;
    ps.minEmitPower = 1;
    ps.maxEmitPower = 1;
    ps.addSizeGradient(0, 0.5);
    ps.addSizeGradient(1, 1.4);
    ps.color1 = new Color4(0.78, 0.66, 0.48, 0.28);
    ps.color2 = new Color4(0.7, 0.6, 0.44, 0.18);
    ps.colorDead = new Color4(0.75, 0.65, 0.5, 0);
    ps.minAngularSpeed = -0.3;
    ps.maxAngularSpeed = 0.3;
    ps.emitRate = 0;
    ps.start();
    return ps;
  }

  /** Rola as texturas, acompanha a cor da névoa (noite e tempestade) e posiciona as rajadas. */
  atualizar(dt: number, jogador: Vector3, poeira: number): void {
    this.tons.uOffset = (this.tons.uOffset + dt * 0.05) % 1;
    this.tons.vOffset = (this.tons.vOffset - dt * 0.012) % 1;
    this.densidade.uOffset = (this.densidade.uOffset + dt * 0.11) % 1;
    this.densidade.vOffset = (this.densidade.vOffset - dt * 0.03) % 1;
    const nevoa = this.cena.fogColor;
    const lum = 0.3 * nevoa.r + 0.59 * nevoa.g + 0.11 * nevoa.b;
    const brilho = Math.min(1.1, Math.max(0.06, lum / 0.85));
    for (const { mat, cor } of this.mats) {
      // de dia, a cor da camada; à noite e na tempestade, puxada para a cor da névoa
      const k = Math.min(1, poeira * 0.7);
      mat.emissiveColor.set(
        cor[0] * brilho * (1 - k) + nevoa.r * k,
        cor[1] * brilho * (1 - k) + nevoa.g * k,
        cor[2] * brilho * (1 - k) + nevoa.b * k,
      );
    }
    // parede mais próxima: ponto do limite mais perto do jogador, com o vento correndo ao longo dela
    const l = this.lim;
    const dists = [jogador.x - l.x0, l.x1 - jogador.x, jogador.z - l.z0, l.z1 - jogador.z];
    const lado = dists.indexOf(Math.min(...dists));
    const d = dists[lado];
    const ps = this.rajadas;
    if (d > 60) {
      ps.emitRate = 0;
      return;
    }
    const em = ps.emitter as Vector3;
    const fora = 6;
    const px = lado === 0 ? l.x0 - fora : lado === 1 ? l.x1 + fora : jogador.x;
    const pz = lado === 2 ? l.z0 - fora : lado === 3 ? l.z1 + fora : jogador.z;
    em.set(px, jogador.y + 2, pz);
    const ao = lado < 2 ? new Vector3(0, 0, 1) : new Vector3(1, 0, 0);
    const para = lado === 0 ? 1 : lado === 1 ? -1 : 0, paraZ = lado === 2 ? 1 : lado === 3 ? -1 : 0;
    ps.minEmitBox = new Vector3(-30 * ao.x - 2, -1, -30 * ao.z - 2);
    ps.maxEmitBox = new Vector3(30 * ao.x + 2, 10, 30 * ao.z + 2);
    // sopra ao longo da parede e um pouco para dentro do mapa
    ps.direction1 = new Vector3(ao.x * 9 + para * 1.5, 0.2, ao.z * 9 + paraZ * 1.5);
    ps.direction2 = new Vector3(ao.x * 15 + para * 4, 1.2, ao.z * 15 + paraZ * 4);
    ps.emitRate = (1 - d / 60) * (ps.getCapacity() / 3.5);
  }

  dispose(): void {
    for (const m of this.malhas) m.dispose();
    for (const { mat } of this.mats) mat.dispose();
    this.tons.dispose();
    this.densidade.dispose();
    this.rajadas.dispose();
  }
}
