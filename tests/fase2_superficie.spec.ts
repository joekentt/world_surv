import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import { abrir, medirFps, registrar } from "./util";

/**
 * Fase 2, tarefa 5 (revisão 2): superfície aberta de 640 x 675 m, em blocos (tools/areas/superficie.py).
 * Percursos correndo de verdade (física, terreno com relevo, ponte, viaduto e encosta) no relógio do jogo,
 * guiados pelas rotas de referência gravadas na área base. Mede as distâncias de rota contra a regra de
 * bloqueio da seção 5.3 (ida e volta correndo a 7 m/s) e compara o fps com a sala de teste.
 * O filtro do EPI fica cheio e a tempestade desligada durante os percursos.
 */

type Estado = { x: number; y: number; z: number; estado: string; area?: string; yaw: number };
type Ponto = [number, number];
type Resultado = { ok: boolean; motivo?: string; yMin: number; yMax: number; x: number; y: number; z: number; t: number; dist: number; areas: string[] };

const BASE = JSON.parse(fs.readFileSync("content/areas/superficie_aberta.json", "utf8"));
const ROTAS = BASE.rotasReferencia as Record<string, Ponto[]> & { pontos: Record<string, Ponto> };
const CORRIDA = 7.0;
const GRAU = Math.PI / 180;
const DIR = "tests/screenshots/fase-2";

const js = <T = unknown>(p: Page, f: string) => p.evaluate(f) as Promise<T>;
const estado = (p: Page) => js<Estado>(p, "window.__vc.estado()");
const tempo = (p: Page) => js<number>(p, "window.__vc.jogo.tempo");
const tecla = (p: Page, c: string, v: boolean) => p.evaluate(([c, v]) => (window.__vc.tecla as (c: string, v: boolean) => void)(c as string, v as boolean), [c, v] as const);
const r2 = (v: number) => Number(v.toFixed(2));
const comprimento = (r: Ponto[]) => r.slice(1).reduce((s, q, i) => s + Math.hypot(q[0] - r[i][0], q[1] - r[i][1]), 0);
/**
 * Distância de rota da Boca (origem) ao ponto: o percorrido correndo, mais os trechos retos da origem ao
 * primeiro ponto da rota (a saída da eclusa) e do último ponto ao centro do destino (a tabela da seção 5.3
 * mede da Boca ao ponto).
 */
const daBoca = (r: Ponto[], percorrido: number, destino: Ponto) =>
  Math.hypot(r[0][0], r[0][1]) + percorrido + Math.hypot(destino[0] - r[r.length - 1][0], destino[1] - r[r.length - 1][1]);
/** Ida e volta correndo, em segundos, para uma distância de ida (m). */
const idaEVolta = (d: number) => (2 * d) / CORRIDA;

async function esperarJogo(p: Page, s: number) {
  const t0 = await tempo(p);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + s, { timeout: 240_000 });
}

async function posicionar(p: Page, x: number, y: number, z: number, yaw: number, yawCamera = yaw, pitch?: number) {
  await p.evaluate(([x, y, z, yp, yc, pt]) => {
    (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, yp);
    (window.__vc.definirCamera as (y: number, p?: number) => void)(yc, pt ?? undefined);
  }, [x, y, z, yaw, yawCamera, pitch ?? null] as const);
  await esperarJogo(p, 0.8);
}

async function camera(p: Page, yaw: number, pitch: number, extra = 0) {
  await p.evaluate(([y, pt, d]) => {
    (window.__vc.definirCamera as (y: number, p?: number) => void)(y, pt);
    (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = d;
  }, [yaw, pitch, extra] as const);
  await esperarJogo(p, 0.5);
}

/** Anda pelos pontos (x, z) com direção forçada, a cada quadro do jogo, somando a distância percorrida no plano. */
async function rota(p: Page, pontos: Ponto[], correr = true, tol = 0.8): Promise<Resultado> {
  return p.evaluate(([pontos, correr, tol]) => new Promise<Resultado>((ok) => {
    const vc = window.__vc as Record<string, any>;
    const jogo = vc.jogo;
    let i = 0, yMin = Infinity, yMax = -Infinity, melhor = Infinity, dist = 0;
    let tMelhor = jogo.tempo;
    const t0 = jogo.tempo;
    const areas: string[] = [];
    let ant: { x: number; z: number } | null = null;
    const obs = jogo.cena.onBeforeRenderObservable.add(() => {
      const e = vc.estado();
      yMin = Math.min(yMin, e.y);
      yMax = Math.max(yMax, e.y);
      if (ant) dist += Math.hypot(e.x - ant.x, e.z - ant.z);
      ant = { x: e.x, z: e.z };
      if (e.area && areas[areas.length - 1] !== e.area) areas.push(e.area);
      const [tx, tz] = pontos[i];
      const dx = tx - e.x, dz = tz - e.z;
      const d = Math.hypot(dx, dz);
      const fim = (motivo?: string) => {
        jogo.cena.onBeforeRenderObservable.remove(obs);
        vc.direcaoForcada(null);
        vc.tecla("ShiftLeft", false);
        ok({ ok: !motivo, motivo, yMin, yMax, x: e.x, y: e.y, z: e.z, t: jogo.tempo - t0, dist, areas });
      };
      if (d < (i === pontos.length - 1 ? tol : Math.max(tol, 1.5))) {
        i++;
        melhor = Infinity;
        tMelhor = jogo.tempo;
        if (i >= pontos.length) return fim();
        return;
      }
      if (d < melhor - 0.05) { melhor = d; tMelhor = jogo.tempo; }
      if (jogo.tempo - tMelhor > 4) return fim(`parado perto de (${e.x.toFixed(2)}, ${e.y.toFixed(2)}, ${e.z.toFixed(2)}) indo para o ponto ${i} (${tx}, ${tz})`);
      vc.tecla("ShiftLeft", correr && d > 2.5);
      vc.direcaoForcada(dx / d, dz / d);
    });
  }), [pontos, correr, tol] as const);
}

async function usarEscada(p: Page): Promise<Estado> {
  await tecla(p, "KeyE", true); await esperarJogo(p, 0.1); await tecla(p, "KeyE", false);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado === "escada", null, { timeout: 30_000 });
  await tecla(p, "KeyW", true);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "escada", null, { timeout: 120_000 });
  await esperarJogo(p, 0.3);
  await tecla(p, "KeyW", false);
  await esperarJogo(p, 0.5);
  return estado(p);
}

/** Abre a superfície pela entrada da Boca, com o filtro sempre cheio e sem tempestade. */
async function preparar(p: Page, extra = "") {
  await p.setViewportSize({ width: 640, height: 360 });
  const erros: string[] = [];
  p.on("console", (m) => { if (m.type() === "error" || /uniform|shader/i.test(m.text())) erros.push(m.text()); });
  await abrir(p, `area=superficie_boca&entrada=boca&render=webgl2&qualidade=alta${extra}`);
  await p.evaluate(() => {
    const j = window.__vc.jogo as any;
    j.cena.onBeforeRenderObservable.add(() => {
      j.epi.filtro = j.estado.capacidadeFiltro();
      j.epi.roupa = j.estado.capacidadeRoupa();
      j.epi.relogioTempestade = 1e4;
      j.epi.tempestade = "calma";
    });
  });
  await esperarJogo(p, 1.0);
  return erros;
}

function exigir(r: Resultado, trecho: string) {
  expect(r.ok, `${trecho}: ${r.motivo}`).toBeTruthy();
}

test.describe("fase 2: superfície aberta", () => {
  test.setTimeout(1_200_000);

  test("a) da Boca ao Marco correndo, cruzando o rio pela ponte; o rio barra fora das travessias", async ({ page }) => {
    const erros = await preparar(page);
    const e0 = await estado(page);
    expect(e0.area).toBe("superficie_boca");
    expect(Math.abs(e0.x) + Math.abs(e0.z - 8)).toBeLessThan(1);

    // a.1 Boca -> Marco pela rota de referência (ruínas, brecha no entulho, ponte inteira)
    const r = await rota(page, ROTAS.marco);
    exigir(r, "Boca ao Marco");
    expect(r.areas).toEqual(expect.arrayContaining(["superficie_boca", "superficie_ruinas", "superficie_rio", "superficie_praca_marco"]));
    expect(r.yMin, "não caiu no leito do rio").toBeGreaterThan(-1.5);
    const pm = ROTAS.pontos.marco;
    const dMarco = daBoca(ROTAS.marco, r.dist, pm);
    expect(Math.hypot(r.x - pm[0], r.z - pm[1])).toBeLessThan(8);
    await posicionar(page, pm[0] + 3, r.y + 0.1, pm[1] - 17, -10 * GRAU, -10 * GRAU, -9 * GRAU);
    await camera(page, -10 * GRAU, -9 * GRAU, 2.5);
    await esperarJogo(page, 2.5);
    await page.screenshot({ path: `${DIR}/superficie-3-marco.png` });

    // a.2 rio como obstáculo: correndo para o norte em x = 0 (fora das travessias) não se chega à outra margem
    await posicionar(page, 0, 0.1, 176, 0);
    const bloqueio = await rota(page, [[0, 176], [0, 232]]);
    expect(bloqueio.ok, "atravessou o rio fora das travessias").toBeFalsy();
    expect(bloqueio.z).toBeLessThan(216);

    // a.3 ponte desabada (segunda travessia): desce ao leito pela rampa de entulho e sobe do outro lado
    await posicionar(page, ROTAS.desabada[0][0], 0.2, ROTAS.desabada[0][1], 0);
    const desab = await rota(page, ROTAS.desabada);
    exigir(desab, "ponte desabada");
    expect(desab.yMin).toBeLessThan(-4);
    expect(desab.z).toBeGreaterThan(228);

    // vista da ponte inteira a partir da margem sul
    await posicionar(page, -62, 0.1, 174, 30 * GRAU, 32 * GRAU, 16 * GRAU);
    await camera(page, 32 * GRAU, 16 * GRAU, 6);
    await esperarJogo(page, 2.5);
    await page.screenshot({ path: `${DIR}/superficie-2-rio-ponte.png` });

    registrar("fase-2", {
      superficie_marco: {
        rotaReferencia_m: r2(comprimento(ROTAS.marco)), percorrido_m: r2(r.dist), daBocaAoMarco_m: r2(dMarco), tempoIda_s: r2(r.t),
        idaEVoltaCorrendo_s: r2(idaEVolta(dMarco)), areas: r.areas, yMinNaRota: r2(r.yMin),
      },
      superficie_rio: { bloqueioEmX0: { parouEm: [r2(bloqueio.x), r2(bloqueio.y), r2(bloqueio.z)] }, pontedesabada: { yMin: r2(desab.yMin), percorrido_m: r2(desab.dist) } },
    });
    // seção 5.3: passa do filtro básico efetivo (69 s) e cabe no nível 2 efetivo (115 s) com 30 s de folga
    expect(idaEVolta(dMarco)).toBeGreaterThan(69);
    expect(idaEVolta(dMarco)).toBeLessThanOrEqual(85);
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("b) da Boca à Antena pela encosta; subida pelo viaduto; vista do mirante", async ({ page }) => {
    const erros = await preparar(page);
    const r = await rota(page, ROTAS.antena);
    exigir(r, "Boca à Antena pela encosta");
    const pa = ROTAS.pontos.antena;
    const dAntena = daBoca(ROTAS.antena, r.dist, pa);
    expect(r.areas).toEqual(expect.arrayContaining(["superficie_colina"]));
    const topo = r.y;
    expect(topo, "no topo da colina").toBeGreaterThan(24);

    // escada de mão na face sul até a plataforma do mirante (10 m)
    await posicionar(page, pa[0], topo + 0.1, pa[1] - 8.5, 0);
    const naPlataforma = await usarEscada(page);
    expect(naPlataforma.y - topo).toBeGreaterThan(9.5);
    await posicionar(page, pa[0] - 2, naPlataforma.y + 0.1, pa[1] - 5.5, 190 * GRAU, 190 * GRAU, 12 * GRAU);
    await camera(page, 190 * GRAU, 12 * GRAU, 2.5);
    await esperarJogo(page, 2.5);
    await page.screenshot({ path: `${DIR}/superficie-4-vista-antena.png` });

    // viaduto: sobe pelo vão desabado, corre pelo tabuleiro e sobe a crista até o topo
    await posicionar(page, ROTAS.viaduto[0][0], 0.5, ROTAS.viaduto[0][1], -60 * GRAU);
    const v = await rota(page, ROTAS.viaduto);
    exigir(v, "viaduto até a Antena");
    expect(v.areas).toEqual(expect.arrayContaining(["superficie_viaduto", "superficie_colina"]));
    expect(v.yMax).toBeGreaterThan(24);

    registrar("fase-2", {
      superficie_antena: {
        rotaReferencia_m: r2(comprimento(ROTAS.antena)), percorrido_m: r2(r.dist), daBocaAAntena_m: r2(dAntena), tempoIda_s: r2(r.t),
        idaEVoltaCorrendo_s: r2(idaEVolta(dAntena)), yTopo: r2(topo), yPlataforma: r2(naPlataforma.y),
      },
      superficie_viaduto: { percorrido_m: r2(v.dist), tempo_s: r2(v.t), areas: v.areas },
    });
    // seção 5.3: passa do nível 2 efetivo (115 s) e cabe no nível 3 efetivo (185 s) com 30 s de folga
    expect(idaEVolta(dAntena)).toBeGreaterThan(115);
    expect(idaEVolta(dAntena)).toBeLessThanOrEqual(155);
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("c) saída da Boca olhando para o norte, abrigos das ruínas e fps contra a sala de teste", async ({ page }) => {
    const erros = await preparar(page);
    await camera(page, -7 * GRAU, -5 * GRAU, 1.5);
    await esperarJogo(page, 3.5);
    await page.screenshot({ path: `${DIR}/superficie-1-boca-norte.png` });
    // ruínas: distância até o abrigo mais próximo (seção 5.3: 29 a 36 s de ida e volta, cabe no básico)
    const abrigos = (JSON.parse(fs.readFileSync("content/areas/superficie_ruinas.json", "utf8")).abrigos as { id: string; min: number[]; max: number[] }[]);
    const dAbrigos = abrigos.map((a) => ({ id: a.id, dist: r2(Math.hypot((a.min[0] + a.max[0]) / 2, (a.min[2] + a.max[2]) / 2 - 8)) }));
    expect(Math.min(...dAbrigos.map((a) => a.dist))).toBeGreaterThan(50);
    expect(Math.max(...dAbrigos.map((a) => idaEVolta(a.dist)))).toBeLessThanOrEqual(39);

    // fps: parado na saída da Boca olhando para o norte, e correndo pelas ruínas
    const fpsBoca = await medirFps(page, 8);
    const corrida = rota(page, [[-2, 40], [-10, 120]]);
    const fpsCorrendo = await medirFps(page, 8);
    await corrida;
    const malhas = await js<number>(page, "window.__vc.jogo.cena.getActiveMeshes().length");
    await abrir(page, "area=sala_teste&render=webgl2&qualidade=alta");
    await esperarJogo(page, 1.5);
    const fpsSala = await medirFps(page, 8);
    registrar("fase-2", {
      superficie_fps: { boca: r2(fpsBoca), correndoRuinas: r2(fpsCorrendo), salaTeste: r2(fpsSala), razaoBocaSala: r2(fpsBoca / fpsSala), malhasAtivasRuinas: malhas },
      superficie_abrigos: dAbrigos,
    });
    expect(fpsBoca / fpsSala, `fps boca ${fpsBoca} contra sala ${fpsSala}`).toBeGreaterThan(0.6);
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
