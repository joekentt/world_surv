import { Color3, DynamicTexture, MeshBuilder, StandardMaterial, Texture, type AbstractMesh, type Mesh, type Scene, type TransformNode } from "@babylonjs/core";
import textosLetreiros from "../../content/textos/letreiros.json";
import type { CorNeon, FaceLetreiro, LetreiroDef, SetaLetreiro } from "./tipos";

/**
 * Letreiros de neon da sinalização de rota (seção 7 de docs/spec/07-arte-personagens-vila.md): placa escura com
 * moldura de tubo, seta e nome do destino desenhados num DynamicTexture e usados como textura emissiva, sem luz
 * real (o limite de luzes do WebGL2 não muda); o GlowLayer da cena faz o halo. Posições em tools/areas/sinalizacao.py.
 */

const TEXTOS = textosLetreiros as Record<string, string>;

/** Texto de um letreiro pela chave de content/textos/letreiros.json. */
export function textoLetreiro(chave: string): string {
  return TEXTOS[chave] ?? chave;
}

/** Tubo (cor saturada), núcleo (quase branco, o centro aceso do tubo) e halo de cada cor de neon. */
const CORES: Record<CorNeon, { tubo: string; nucleo: string; halo: string }> = {
  ciano: { tubo: "#2ef2ff", nucleo: "#e6feff", halo: "#00d8ff" },
  magenta: { tubo: "#ff3ccf", nucleo: "#ffe6f8", halo: "#ff12b0" },
  ambar: { tubo: "#ffae2a", nucleo: "#fff2d6", halo: "#ff8c00" },
  verde: { tubo: "#a6ff2a", nucleo: "#f2ffdc", halo: "#76ff00" },
};

/** Pixels por metro da textura (limitada a 2048 px de largura). */
const PX_POR_M = 170;
/** Intensidade da textura emissiva: o subsolo tem exposição alta e o neon estouraria em branco; na superfície, cheia. */
const NIVEL_EMISSAO = { subsolo: 0.62, superficie: 1.15 };
const FONTE = "'Arial Narrow', 'Liberation Sans Narrow', 'Roboto Condensed', 'DejaVu Sans Condensed', Arial, sans-serif";
const ANGULO_SETA: Record<SetaLetreiro, number> = { direita: 0, desce: Math.PI / 2, esquerda: Math.PI, frente: -Math.PI / 2, sobe: -Math.PI / 2 };

function retanguloArredondado(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

/** Desenha um traço duas vezes: halo largo e borrado na cor do tubo e núcleo fino quase branco. */
function neon(c: CanvasRenderingContext2D, cor: (typeof CORES)[CorNeon], largura: number, desenhar: () => void): void {
  c.save();
  c.lineCap = "round";
  c.lineJoin = "round";
  c.shadowColor = cor.halo;
  c.shadowBlur = largura * 2.2;
  c.strokeStyle = cor.tubo;
  c.lineWidth = largura;
  desenhar();
  c.stroke();
  c.shadowBlur = largura * 0.8;
  c.strokeStyle = cor.nucleo;
  c.lineWidth = largura * 0.42;
  c.stroke();
  c.restore();
}

function seta(c: CanvasRenderingContext2D, cx: number, cy: number, tam: number, direcao: SetaLetreiro, cor: (typeof CORES)[CorNeon]): void {
  const a = ANGULO_SETA[direcao];
  const p = (x: number, y: number): [number, number] => [cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a)];
  const l = tam * 0.42;
  neon(c, cor, tam * 0.11, () => {
    c.beginPath();
    c.moveTo(...p(-l, 0));
    c.lineTo(...p(l, 0));
    c.moveTo(...p(l * 0.05, -l * 0.8));
    c.lineTo(...p(l, 0));
    c.lineTo(...p(l * 0.05, l * 0.8));
  });
}

/** Escreve o texto em tubo de neon, reduzindo a fonte até caber em `largura`. */
function texto(c: CanvasRenderingContext2D, s: string, x: number, y: number, largura: number, altura: number, cor: (typeof CORES)[CorNeon]): void {
  let tam = altura;
  c.font = `bold ${tam}px ${FONTE}`;
  const medida = c.measureText(s).width;
  if (medida > largura) tam = Math.floor((tam * largura) / medida);
  c.save();
  c.font = `bold ${tam}px ${FONTE}`;
  c.textBaseline = "middle";
  c.textAlign = "center";
  c.shadowColor = cor.halo;
  c.shadowBlur = tam * 0.35;
  c.fillStyle = cor.tubo;
  c.fillText(s, x, y);
  c.shadowBlur = tam * 0.12;
  c.fillStyle = cor.nucleo;
  c.fillText(s, x, y);
  c.restore();
}

function desenharFace(c: CanvasRenderingContext2D, w: number, h: number, face: FaceLetreiro, corPadrao: CorNeon): void {
  const cor = CORES[face.cor ?? corPadrao];
  c.fillStyle = "#08070c";
  c.fillRect(0, 0, w, h);
  const m = h * 0.07;
  neon(c, cor, h * 0.03, () => retanguloArredondado(c, m, m, w - 2 * m, h - 2 * m, h * 0.1));
  const lado = h - 4 * m;
  let x0 = 2.5 * m, x1 = w - 2.5 * m;
  if (face.seta) {
    const direita = face.seta === "direita";
    const cx = direita ? x1 - lado / 2 : x0 + lado / 2;
    seta(c, cx, h / 2, lado, face.seta, cor);
    if (direita) x1 -= lado + m;
    else x0 += lado + m;
  }
  const larg = x1 - x0, cx = (x0 + x1) / 2;
  if (face.sub) {
    texto(c, textoLetreiro(face.texto), cx, h * 0.38, larg, h * 0.42, cor);
    texto(c, textoLetreiro(face.sub), cx, h * 0.73, larg, h * 0.2, cor);
  } else {
    texto(c, textoLetreiro(face.texto), cx, h / 2, larg, h * 0.56, cor);
  }
}

function materialFace(cena: Scene, nome: string, def: LetreiroDef, face: FaceLetreiro, nivel: number): StandardMaterial {
  let w = Math.round(def.largura * PX_POR_M), h = Math.round(def.altura * PX_POR_M);
  if (w > 2048) {
    h = Math.round((h * 2048) / w);
    w = 2048;
  }
  const tex = new DynamicTexture(`${nome}_tex`, { width: w, height: h }, cena, true, Texture.TRILINEAR_SAMPLINGMODE);
  desenharFace(tex.getContext() as unknown as CanvasRenderingContext2D, w, h, face, def.cor);
  tex.update();
  tex.anisotropicFilteringLevel = 8;
  tex.wrapU = tex.wrapV = Texture.CLAMP_ADDRESSMODE;
  tex.level = nivel;
  const mat = new StandardMaterial(`${nome}_mat`, cena);
  mat.diffuseColor = Color3.Black();
  mat.specularColor = Color3.Black();
  mat.emissiveTexture = tex;
  mat.disableLighting = true;
  return mat;
}

function materialCaixa(cena: Scene): StandardMaterial {
  const id = "letreiro_caixa";
  const existente = cena.getMaterialByName(id) as StandardMaterial | null;
  if (existente) return existente;
  const m = new StandardMaterial(id, cena);
  m.diffuseColor = new Color3(0.06, 0.06, 0.07);
  m.specularColor = new Color3(0.2, 0.2, 0.22);
  return m;
}

/**
 * Monta os letreiros de uma área sob `raiz` e devolve as malhas e uma função que libera as texturas e os
 * materiais (a raiz da área é descartada sem os materiais).
 */
export function construirLetreiros(cena: Scene, defs: LetreiroDef[], raiz: TransformNode, prefixo: string, superficie = false): { malhas: AbstractMesh[]; liberar: () => void } {
  const nivel = superficie ? NIVEL_EMISSAO.superficie : NIVEL_EMISSAO.subsolo;
  const malhas: AbstractMesh[] = [];
  const materiais: StandardMaterial[] = [];
  const PROF = 0.08;
  for (const def of defs) {
    const nome = `letreiro_${prefixo}_${def.id}`;
    const yaw = (def.r * Math.PI) / 180;
    // normal da face legível: (sin r, 0, cos r); o plano do Babylon mostra a frente para -Z local
    const nx = Math.sin(yaw), nz = Math.cos(yaw);
    const caixa = MeshBuilder.CreateBox(`${nome}_caixa`, { width: def.largura + 0.1, height: def.altura + 0.1, depth: PROF }, cena);
    caixa.position.set(def.x - nx * (PROF / 2 + 0.005), def.y, def.z - nz * (PROF / 2 + 0.005));
    caixa.rotation.y = yaw;
    caixa.material = materialCaixa(cena);
    const pecas: Mesh[] = [caixa];
    const faces: [FaceLetreiro, number, number][] = [[def, yaw + Math.PI, 0]];
    if (def.verso) faces.push([def.verso, yaw, -(PROF + 0.01)]);
    for (const [i, [face, rot, recuo]] of faces.entries()) {
      const plano = MeshBuilder.CreatePlane(`${nome}_face${i}`, { width: def.largura, height: def.altura }, cena);
      plano.position.set(def.x + nx * recuo, def.y, def.z + nz * recuo);
      plano.rotation.y = rot;
      const mat = materialFace(cena, `${nome}_face${i}`, def, face, nivel);
      materiais.push(mat);
      plano.material = mat;
      pecas.push(plano);
    }
    if (def.suspenso !== undefined && def.suspenso > def.y + def.altura / 2) {
      const topo = def.y + def.altura / 2;
      const alt = def.suspenso - topo;
      for (const lado of [-1, 1]) {
        const cabo = MeshBuilder.CreateBox(`${nome}_cabo`, { width: 0.03, height: alt, depth: 0.03 }, cena);
        const dx = lado * def.largura * 0.38;
        cabo.position.set(def.x - nx * PROF / 2 + nz * dx, topo + alt / 2, def.z - nz * PROF / 2 - nx * dx);
        cabo.material = materialCaixa(cena);
        pecas.push(cabo);
      }
    }
    for (const m of pecas) {
      m.parent = raiz;
      m.isPickable = false;
      m.freezeWorldMatrix();
      malhas.push(m);
    }
  }
  return {
    malhas,
    liberar: () => {
      for (const m of materiais) {
        m.emissiveTexture?.dispose();
        m.dispose();
      }
    },
  };
}
