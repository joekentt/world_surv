import {
  Color4, DynamicTexture, GPUParticleSystem, ParticleSystem, Vector3, type IParticleSystem, type Scene, type Texture,
} from "@babylonjs/core";

interface Fonte { area: string; tipo: "poeira" | "vapor" | "fumaca" | "nevoa" | "gota" | "faisca"; x: number; y: number; z: number; }

/** Fontes de partículas por área (seção 8: poeira das frestas, vapor da bomba, fumaça das cozinhas). */
const FONTES: Fonte[] = [
  ...[-66, -42, -18, 6, 30].map((x) => ({ area: "praca", tipo: "poeira" as const, x, y: 11.5, z: 2 })),
  { area: "praca", tipo: "vapor", x: 18.3, y: 2.2, z: 2.9 },
  { area: "praca", tipo: "vapor", x: 17.5, y: 5.2, z: 3.3 },
  { area: "praca", tipo: "fumaca", x: -4, y: 1.0, z: 2.7 },
  ...[62, 88, 116].map((x) => ({ area: "galerias", tipo: "poeira" as const, x, y: 9.0, z: 2 })),
  { area: "galerias", tipo: "fumaca", x: 92, y: 0.4, z: 2.6 },
  { area: "galerias", tipo: "faisca", x: 100.5, y: 1.1, z: 2.0 },
  ...[-130, -110].map((x) => ({ area: "capela", tipo: "poeira" as const, x, y: 8.5, z: 2.4 })),
  { area: "capela", tipo: "poeira", x: -142, y: 8.0, z: 2.2 },
  ...[14, 31, 52, 66, 90, 104].map((x) => ({ area: "duto_norte", tipo: "gota" as const, x, y: 4.5, z: 1.2 })),
  ...[19, 21.5, 24].map((x) => ({ area: "boca_do_poco", tipo: "nevoa" as const, x, y: 0.2, z: 1.6 })),
  { area: "boca_do_poco", tipo: "nevoa", x: 36, y: 0.2, z: 2.0 },
];

function texturaMacia(cena: Scene): Texture {
  const existente = cena.getTextureByName("particula_macia") as Texture | null;
  if (existente) return existente;
  const t = new DynamicTexture("particula_macia", 64, cena, false);
  const ctx = t.getContext() as CanvasRenderingContext2D;
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.4, "rgba(255,255,255,0.45)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  t.update();
  t.hasAlpha = true;
  return t;
}

/** Partículas por área e a poeira da superfície (leve sempre, densa na tempestade). */
export class Particulas {
  private porArea = new Map<string, IParticleSystem[]>();
  private poeiraSup: IParticleSystem | null = null;
  private tempestade: IParticleSystem | null = null;

  constructor(private cena: Scene, private qualidade: "alta" | "media") {}

  private sistema(nome: string, capacidade: number): ParticleSystem {
    const ps = new ParticleSystem(nome, capacidade, this.cena);
    ps.particleTexture = texturaMacia(this.cena);
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    return ps;
  }

  aoCarregar(area: string): void {
    const lista: IParticleSystem[] = [];
    const fator = this.qualidade === "alta" ? 1 : 0.5;
    for (const f of FONTES.filter((x) => x.area === area)) {
      const ps = this.sistema(`ps_${area}_${f.tipo}_${f.x}`, Math.round(200 * fator));
      ps.emitter = new Vector3(f.x, f.y, f.z);
      if (f.tipo === "poeira") {
        ps.createBoxEmitter(new Vector3(-0.1, -1, 0), new Vector3(0.1, -1, 0), new Vector3(-0.6, 0, -0.4), new Vector3(0.6, 0, 0.4));
        ps.color1 = new Color4(0.75, 0.68, 0.55, 0.35); ps.color2 = new Color4(0.6, 0.55, 0.45, 0.2); ps.colorDead = new Color4(0.5, 0.45, 0.4, 0);
        ps.minSize = 0.03; ps.maxSize = 0.09; ps.minLifeTime = 5; ps.maxLifeTime = 8; ps.emitRate = 14 * fator;
        ps.minEmitPower = 0.8; ps.maxEmitPower = 1.6; ps.gravity = new Vector3(0, -0.15, 0);
      } else if (f.tipo === "vapor" || f.tipo === "fumaca") {
        ps.createConeEmitter(0.25, Math.PI / 8);
        const vapor = f.tipo === "vapor";
        ps.color1 = vapor ? new Color4(0.9, 0.9, 0.9, 0.22) : new Color4(0.35, 0.32, 0.3, 0.3);
        ps.color2 = vapor ? new Color4(0.8, 0.82, 0.85, 0.12) : new Color4(0.25, 0.23, 0.22, 0.2);
        ps.colorDead = new Color4(0.5, 0.5, 0.5, 0);
        ps.minSize = 0.3; ps.maxSize = 0.8; ps.minLifeTime = 2.5; ps.maxLifeTime = 4.5; ps.emitRate = 10 * fator;
        ps.minEmitPower = 0.4; ps.maxEmitPower = 0.9; ps.gravity = new Vector3(0.05, 0.25, 0);
        ps.addSizeGradient(0, 0.3); ps.addSizeGradient(1, 1.6);
        ps.minAngularSpeed = -0.4; ps.maxAngularSpeed = 0.4;
      } else if (f.tipo === "nevoa") {
        ps.createBoxEmitter(new Vector3(-0.2, 0.05, -0.1), new Vector3(0.2, 0.15, 0.1), new Vector3(-1.2, 0, -0.6), new Vector3(1.2, 0.3, 0.6));
        ps.color1 = new Color4(0.95, 0.75, 0.72, 0.07); ps.color2 = new Color4(0.85, 0.6, 0.6, 0.04); ps.colorDead = new Color4(0.8, 0.6, 0.6, 0);
        ps.minSize = 0.8; ps.maxSize = 1.8; ps.minLifeTime = 4; ps.maxLifeTime = 7; ps.emitRate = 7 * fator;
        ps.minEmitPower = 0.1; ps.maxEmitPower = 0.3; ps.gravity = Vector3.Zero();
      } else if (f.tipo === "gota") {
        ps.createPointEmitter(new Vector3(0, -1, 0), new Vector3(0, -1, 0));
        ps.color1 = new Color4(0.7, 0.85, 0.9, 0.7); ps.color2 = new Color4(0.6, 0.75, 0.85, 0.5); ps.colorDead = new Color4(0.6, 0.7, 0.8, 0);
        ps.minSize = 0.03; ps.maxSize = 0.05; ps.minLifeTime = 0.9; ps.maxLifeTime = 1.0; ps.emitRate = 1.2;
        ps.minEmitPower = 0.1; ps.maxEmitPower = 0.2; ps.gravity = new Vector3(0, -9.8, 0);
      } else if (f.tipo === "faisca") {
        ps.createSphereEmitter(0.05);
        ps.blendMode = ParticleSystem.BLENDMODE_ADD;
        ps.color1 = new Color4(1, 0.8, 0.3, 1); ps.color2 = new Color4(1, 0.5, 0.1, 1); ps.colorDead = new Color4(1, 0.3, 0, 0);
        ps.minSize = 0.015; ps.maxSize = 0.03; ps.minLifeTime = 0.3; ps.maxLifeTime = 0.6; ps.emitRate = 0;
        ps.manualEmitCount = 0; ps.minEmitPower = 1; ps.maxEmitPower = 2.5; ps.gravity = new Vector3(0, -6, 0);
        (ps as unknown as { _faisca: boolean })._faisca = true;
      }
      ps.start();
      lista.push(ps);
    }
    this.porArea.set(area, lista);
  }

  aoDescarregar(area: string): void {
    for (const ps of this.porArea.get(area) ?? []) ps.dispose();
    this.porArea.delete(area);
  }

  private garantirSuperficie(): void {
    if (this.poeiraSup) return;
    const leve = this.sistema("ps_poeira_superficie", this.qualidade === "alta" ? 600 : 250);
    leve.emitter = new Vector3(0, 3, 2);
    leve.createBoxEmitter(new Vector3(1.5, -0.1, 0), new Vector3(2.5, 0.1, 0), new Vector3(-14, -3, -4), new Vector3(14, 6, 10));
    leve.color1 = new Color4(0.85, 0.78, 0.62, 0.25); leve.color2 = new Color4(0.75, 0.68, 0.55, 0.15); leve.colorDead = new Color4(0.7, 0.6, 0.5, 0);
    leve.minSize = 0.04; leve.maxSize = 0.12; leve.minLifeTime = 3; leve.maxLifeTime = 6; leve.emitRate = 40;
    leve.minEmitPower = 0.6; leve.maxEmitPower = 1.4; leve.gravity = Vector3.Zero();
    this.poeiraSup = leve;
    const cap = this.qualidade === "alta" ? 6000 : 1500;
    const forte: IParticleSystem = this.qualidade === "alta" && GPUParticleSystem.IsSupported
      ? new GPUParticleSystem("ps_tempestade", { capacity: cap }, this.cena)
      : new ParticleSystem("ps_tempestade", cap, this.cena);
    forte.particleTexture = texturaMacia(this.cena);
    forte.emitter = new Vector3(0, 3, 0);
    (forte as ParticleSystem).createBoxEmitter(new Vector3(8, -0.5, 0), new Vector3(14, 0.6, 0), new Vector3(-16, -2, -6), new Vector3(16, 9, 14));
    forte.color1 = new Color4(0.8, 0.66, 0.45, 0.4); forte.color2 = new Color4(0.7, 0.55, 0.38, 0.3); forte.colorDead = new Color4(0.6, 0.5, 0.35, 0);
    forte.minSize = 0.1; forte.maxSize = 0.6; forte.minLifeTime = 1.2; forte.maxLifeTime = 2.4; forte.emitRate = 0;
    forte.minEmitPower = 1; forte.maxEmitPower = 2; forte.gravity = Vector3.Zero();
    forte.start();
    this.tempestade = forte;
  }

  atualizar(x: number, y: number, superficie: boolean, poeira: number, ventoDir: number, tempo: number): void {
    if (superficie) {
      this.garantirSuperficie();
      (this.poeiraSup!.emitter as Vector3).set(x, y + 2.5, 2);
      if (!this.poeiraSup!.isStarted()) this.poeiraSup!.start();
      (this.tempestade!.emitter as Vector3).set(x, y + 3, 0);
      this.tempestade!.emitRate = poeira * (this.qualidade === "alta" ? 2600 : 700);
      const d = ventoDir || 1;
      (this.tempestade as ParticleSystem).direction1 = new Vector3(8 * d, -0.5, 0);
      (this.tempestade as ParticleSystem).direction2 = new Vector3(14 * d, 0.6, 0);
    } else if (this.poeiraSup?.isStarted()) {
      this.poeiraSup.stop();
      if (this.tempestade) this.tempestade.emitRate = 0;
    }
    // faíscas da oficina da Nita em rajadas
    for (const lista of this.porArea.values()) {
      for (const ps of lista) {
        if ((ps as unknown as { _faisca?: boolean })._faisca && Math.sin(tempo * 3.1) > 0.97) (ps as ParticleSystem).manualEmitCount = 18;
      }
    }
  }
}
