import {
  ColorCurves, Color4, DefaultRenderingPipeline, GlowLayer, ImageProcessingConfiguration, SSAO2RenderingPipeline,
  type Camera, type Scene,
} from "@babylonjs/core";

export interface Grade { exposicao: number; contraste: number; vinheta: number; vinhetaCor: [number, number, number]; bloom: number; grao: number; saturacao: number; }

/** Ajuste de imagem por estética (seção 6): o subsolo quente e fechado, a superfície estourada. */
export const GRADES: Record<string, Grade> = {
  praca: { exposicao: 2.0, contraste: 1.08, vinheta: 2.4, vinhetaCor: [0.08, 0.04, 0.0], bloom: 0.55, grao: 9, saturacao: 10 },
  galerias: { exposicao: 2.1, contraste: 1.1, vinheta: 2.8, vinhetaCor: [0.0, 0.05, 0.05], bloom: 0.6, grao: 14, saturacao: -10 },
  capela: { exposicao: 2.0, contraste: 1.08, vinheta: 2.6, vinhetaCor: [0.06, 0.03, 0.0], bloom: 0.9, grao: 8, saturacao: 15 },
  duto: { exposicao: 2.8, contraste: 1.1, vinheta: 3.6, vinhetaCor: [0, 0, 0], bloom: 0.8, grao: 18, saturacao: -15 },
  boca: { exposicao: 1.9, contraste: 1.08, vinheta: 2.6, vinhetaCor: [0.1, 0.0, 0.0], bloom: 0.75, grao: 12, saturacao: 5 },
  superficie: { exposicao: 1.0, contraste: 1.08, vinheta: 1.2, vinhetaCor: [0.3, 0.25, 0.15], bloom: 0.25, grao: 10, saturacao: -25 },
  superficie_noite: { exposicao: 1.9, contraste: 1.1, vinheta: 2.8, vinhetaCor: [0, 0, 0.05], bloom: 1.0, grao: 16, saturacao: -10 },
  teste: { exposicao: 1, contraste: 1, vinheta: 0, vinhetaCor: [0, 0, 0], bloom: 0.3, grao: 0, saturacao: 0 },
};

/**
 * Pós-processamento. WebGPU ("alta"): bloom em meia resolução, SSAO e grão; WebGL2 ("media"):
 * versão simplificada, sem SSAO e com bloom mais barato. O GlowLayer faz as lâmpadas e o musgo brilharem.
 */
export class PosProcessamento {
  readonly pipeline: DefaultRenderingPipeline;
  readonly brilho: GlowLayer;
  private ssao: SSAO2RenderingPipeline | null = null;
  private atual: Grade = GRADES.praca;
  private alvo: Grade = GRADES.praca;

  constructor(cena: Scene, camera: Camera, qualidade: "alta" | "media") {
    this.brilho = new GlowLayer("brilho", cena, { mainTextureSamples: qualidade === "alta" ? 4 : 1, blurKernelSize: qualidade === "alta" ? 48 : 24 });
    this.brilho.intensity = 0.7;
    const p = new DefaultRenderingPipeline("pos", true, cena, [camera]);
    p.fxaaEnabled = true;
    p.bloomEnabled = true;
    p.bloomThreshold = 0.75;
    p.bloomKernel = qualidade === "alta" ? 64 : 32;
    p.bloomScale = 0.5;
    p.imageProcessingEnabled = true;
    p.imageProcessing.toneMappingEnabled = true;
    p.imageProcessing.toneMappingType = ImageProcessingConfiguration.TONEMAPPING_ACES;
    p.imageProcessing.vignetteEnabled = true;
    p.imageProcessing.vignetteWeight = 2;
    p.imageProcessing.vignetteBlendMode = ImageProcessingConfiguration.VIGNETTEMODE_MULTIPLY;
    p.grainEnabled = qualidade === "alta";
    p.sharpenEnabled = qualidade === "alta";
    if (p.sharpenEnabled) p.sharpen.edgeAmount = 0.25;
    this.pipeline = p;
    if (qualidade === "alta") {
      try {
        this.ssao = new SSAO2RenderingPipeline("ssao", cena, { ssaoRatio: 0.5, blurRatio: 0.5 }, [camera], true);
        this.ssao.radius = 1.2;
        this.ssao.totalStrength = 1.1;
        this.ssao.samples = 12;
        this.ssao.maxZ = 60;
      } catch (e) {
        console.warn("[pos] SSAO indisponível", e);
      }
    }
  }

  ativo = true;

  /** Modo econômico: remove pós-processamento, SSAO e brilho. */
  desligar(): void {
    if (!this.ativo) return;
    this.ativo = false;
    this.ssao?.dispose();
    this.pipeline.dispose();
    this.brilho.dispose();
  }

  definir(estetica: string): void {
    this.alvo = GRADES[estetica] ?? GRADES.praca;
  }

  atualizar(dt: number, poeira: number): void {
    if (!this.ativo) return;
    const k = Math.min(1, dt * 1.5);
    const a = this.atual, b = this.alvo;
    const mix = (x: number, y: number) => x + (y - x) * k;
    this.atual = {
      exposicao: mix(a.exposicao, b.exposicao), contraste: mix(a.contraste, b.contraste), vinheta: mix(a.vinheta, b.vinheta),
      vinhetaCor: a.vinhetaCor.map((v, i) => mix(v, b.vinhetaCor[i])) as [number, number, number],
      bloom: mix(a.bloom, b.bloom), grao: mix(a.grao, b.grao), saturacao: mix(a.saturacao, b.saturacao),
    };
    const g = this.atual;
    const ip = this.pipeline.imageProcessing;
    ip.exposure = g.exposicao * (1 + poeira * 0.15);
    ip.contrast = g.contraste * (1 - poeira * 0.25);
    ip.vignetteWeight = g.vinheta + poeira * 2;
    ip.vignetteColor = new Color4(...g.vinhetaCor, 0);
    this.pipeline.bloomWeight = g.bloom;
    if (this.pipeline.grainEnabled) this.pipeline.grain.intensity = g.grao + poeira * 20;
    if (!ip.colorCurves) ip.colorCurves = new ColorCurves();
    ip.colorCurvesEnabled = true;
    ip.colorCurves.globalSaturation = g.saturacao - poeira * 30;
  }
}
