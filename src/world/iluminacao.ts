import { Color3, Color4, Scene, Vector3, type DirectionalLight, type HemisphericLight, type Light, type Material } from "@babylonjs/core";

export interface Perfil {
  fundo: [number, number, number];
  ambiente: [number, number, number];
  ambienteInt: number;
  chao: [number, number, number];
  nevoa: [number, number, number];
  densidadeNevoa: number;
  sol: number;
  corSol?: [number, number, number];
  exposicao?: number;
  lanterna: boolean;
}

/** Luz e cor de cada estética (seção 6 do MVP). */
export const PERFIS: Record<string, Perfil> = {
  teste: { fundo: [0.05, 0.045, 0.04], ambiente: [0.8, 0.75, 0.7], ambienteInt: 0.45, chao: [0.2, 0.18, 0.15], nevoa: [0.05, 0.045, 0.04], densidadeNevoa: 0, sol: 0, lanterna: false },
  praca: { fundo: [0.06, 0.045, 0.03], ambiente: [1.0, 0.78, 0.55], ambienteInt: 0.45, chao: [0.25, 0.18, 0.1], nevoa: [0.12, 0.085, 0.05], densidadeNevoa: 0.018, sol: 0, lanterna: false },
  galerias: { fundo: [0.02, 0.05, 0.05], ambiente: [0.55, 0.9, 0.85], ambienteInt: 0.36, chao: [0.08, 0.14, 0.13], nevoa: [0.03, 0.07, 0.07], densidadeNevoa: 0.022, sol: 0, lanterna: false },
  capela: { fundo: [0.05, 0.035, 0.025], ambiente: [1.0, 0.85, 0.6], ambienteInt: 0.22, chao: [0.2, 0.12, 0.08], nevoa: [0.1, 0.07, 0.04], densidadeNevoa: 0.02, sol: 0, lanterna: false },
  duto: { fundo: [0.005, 0.008, 0.01], ambiente: [0.45, 0.6, 0.65], ambienteInt: 0.22, chao: [0.02, 0.04, 0.04], nevoa: [0.0, 0.01, 0.012], densidadeNevoa: 0.04, sol: 0, lanterna: true },
  boca: { fundo: [0.05, 0.01, 0.01], ambiente: [1.0, 0.5, 0.45], ambienteInt: 0.32, chao: [0.15, 0.05, 0.04], nevoa: [0.18, 0.08, 0.07], densidadeNevoa: 0.045, sol: 0, lanterna: false },
  superficie_noite: { fundo: [0.02, 0.03, 0.07], ambiente: [0.35, 0.42, 0.65], ambienteInt: 0.35, chao: [0.05, 0.05, 0.08], nevoa: [0.03, 0.04, 0.08], densidadeNevoa: 0.006, sol: 0.5, corSol: [0.5, 0.6, 0.9], lanterna: true },
  superficie: { fundo: [0.95, 0.9, 0.74], ambiente: [1.0, 0.96, 0.85], ambienteInt: 0.85, chao: [0.6, 0.55, 0.45], nevoa: [0.9, 0.85, 0.7], densidadeNevoa: 0.012, sol: 3.2, corSol: [1.0, 0.95, 0.82], lanterna: false },
};

/**
 * Aplica o perfil de luz da área atual com transição suave e mantém acesas só as luzes
 * pontuais mais próximas da câmera (limite por material: 6 em WebGPU, 4 em WebGL2).
 */
export class Iluminacao {
  private atual: Perfil = PERFIS.praca;
  private alvo: Perfil = PERFIS.praca;
  private t = 1;
  private luzes: Light[] = [];
  private relogio = 0;
  /** Multiplicador das lâmpadas da vila (turno de descanso). */
  fatorLampadas = 1;
  /** Escurecimento extra (tempestade). */
  poeiraExtra = 0;
  readonly maxLuzes: number;

  constructor(private cena: Scene, private ambiente: HemisphericLight, private sol: DirectionalLight, qualidade: "alta" | "media") {
    this.maxLuzes = qualidade === "alta" ? 6 : 4;
    cena.fogMode = Scene.FOGMODE_EXP2;
    cena.onNewMaterialAddedObservable.add((m) => this.ajustarMaterial(m));
    for (const m of cena.materials) this.ajustarMaterial(m);
  }

  private ajustarMaterial(m: Material): void {
    const mm = m as unknown as { maxSimultaneousLights?: number };
    if (mm.maxSimultaneousLights !== undefined) mm.maxSimultaneousLights = this.maxLuzes + 2;
  }

  definirPerfil(nome: string, imediato = false): void {
    const p = PERFIS[nome] ?? PERFIS.praca;
    if (p === this.alvo) return;
    this.atual = this.misturado();
    this.alvo = p;
    this.t = imediato ? 1 : 0;
  }

  registrarLuzes(luzes: Light[]): void {
    this.luzes.push(...luzes);
  }

  removerLuzes(luzes: Light[]): void {
    this.luzes = this.luzes.filter((l) => !luzes.includes(l));
  }

  private misturado(): Perfil {
    const k = this.t;
    const mix = (a: number[], b: number[]) => a.map((v, i) => v + (b[i] - v) * k) as [number, number, number];
    const a = this.atual, b = this.alvo;
    return {
      fundo: mix(a.fundo, b.fundo), ambiente: mix(a.ambiente, b.ambiente), ambienteInt: a.ambienteInt + (b.ambienteInt - a.ambienteInt) * k,
      chao: mix(a.chao, b.chao), nevoa: mix(a.nevoa, b.nevoa), densidadeNevoa: a.densidadeNevoa + (b.densidadeNevoa - a.densidadeNevoa) * k,
      sol: a.sol + (b.sol - a.sol) * k, corSol: mix(a.corSol ?? [1, 1, 1], b.corSol ?? [1, 1, 1]), lanterna: b.lanterna,
    };
  }

  get perfil(): Perfil {
    return this.alvo;
  }

  atualizar(dt: number, foco: Vector3, tempo: number): void {
    this.t = Math.min(1, this.t + dt * 1.2);
    const p = this.misturado();
    const poeira = this.poeiraExtra;
    const nevoa = p.nevoa.map((v, i) => v * (1 - poeira) + [0.75, 0.62, 0.45][i] * poeira) as [number, number, number];
    this.cena.clearColor = new Color4(...(p.fundo.map((v, i) => v * (1 - poeira) + nevoa[i] * poeira) as [number, number, number]), 1);
    this.cena.fogColor = new Color3(...nevoa);
    this.cena.fogDensity = p.densidadeNevoa + poeira * 0.06;
    this.ambiente.diffuse = new Color3(...p.ambiente);
    this.ambiente.groundColor = new Color3(...p.chao);
    this.ambiente.intensity = p.ambienteInt * (this.alvo.sol > 0 ? 1 - poeira * 0.4 : 0.3 + 0.7 * this.fatorLampadas);
    this.sol.intensity = p.sol * (1 - poeira * 0.7);
    this.sol.diffuse = new Color3(...(p.corSol ?? [1, 1, 1]));
    this.sol.setEnabled(p.sol > 0.01);
    if (p.sol > 0.01) this.sol.position.set(foco.x + 20, 40, -30);

    // luzes pontuais: piscar e seleção das mais próximas
    for (const l of this.luzes) {
      const base = (l as unknown as { _base: number })._base ?? l.intensity;
      const pisca = (l as unknown as { _piscar: boolean })._piscar;
      let f = this.alvo.sol > 0 ? 1 : this.fatorLampadas;
      if (pisca) {
        const fase = l.uniqueId * 1.7;
        const ruido = Math.sin(tempo * 13 + fase) + Math.sin(tempo * 7.3 + fase * 2.1);
        f *= ruido > 1.55 ? 0.15 : 1;
      }
      l.intensity = base * f;
    }
    this.relogio -= dt;
    if (this.relogio <= 0) {
      this.relogio = 0.3;
      const ordenadas = [...this.luzes].sort((a, b) => dist(a, foco) - dist(b, foco));
      ordenadas.forEach((l, i) => l.setEnabled(i < this.maxLuzes));
    }
  }
}

function dist(l: Light, p: Vector3): number {
  const pos = (l as unknown as { position?: Vector3 }).position;
  return pos ? Vector3.DistanceSquared(pos, p) : 0;
}
