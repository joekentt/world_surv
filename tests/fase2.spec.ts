import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import { abrir, medirFps, registrar } from "./util";

/**
 * Fase 2 (revisão 2), critério de avanço: "o personagem percorre das Galerias Secas até a Antena sem travar".
 *
 * Percurso integrado, andando e correndo de verdade (física, rampas, escadas de mão, eclusa), em trechos:
 * Galerias -> praça -> Duto Norte -> Estação Aurora -> poço (quatro lances de escada) -> eclusa ->
 * superfície -> Antena. Cada trecho pede ao navmesh em vários níveis (window.__vc.rotaNav) a rota da
 * posição atual até o alvo e guia o personagem por ela com direção forçada, a cada quadro do jogo; as
 * escadas da rota (ligações fora da malha) são usadas com E e W/S. Sem teleporte entre os trechos.
 * Em cada trecho confere a área e o mundo no fim e que o personagem não caiu no vazio (altura mínima e
 * nenhum salto de posição, que seria a volta automática ao último chão firme).
 * Também mede o fps correndo na superfície (só referência: SwiftShader) e tira os screenshots do critério
 * (passarelas da vila e alto da Antena). O filtro do EPI fica cheio e a tempestade desligada.
 */

type V3 = [number, number, number];
type Ponto = [number, number];
type Estado = { x: number; y: number; z: number; estado: string; area?: string; mundo: string; yaw: number };
type Rota = { ok: boolean; motivo?: string; comprimento: number; horizontal: number; pontos: V3[]; escadas: number };
type Resultado = { ok: boolean; motivo?: string; yMin: number; salto: number; x: number; y: number; z: number; t: number; dist: number; areas: string[] };

const GRAU = Math.PI / 180;
const DIR = "tests/screenshots/fase-2";
const js = <T = unknown>(p: Page, f: string) => p.evaluate(f) as Promise<T>;
const estado = (p: Page) => js<Estado>(p, "window.__vc.estado()");
const tempo = (p: Page) => js<number>(p, "window.__vc.jogo.tempo");
const tecla = (p: Page, c: string, v: boolean) => p.evaluate(([c, v]) => (window.__vc.tecla as (c: string, v: boolean) => void)(c as string, v as boolean), [c, v] as const);
const r2 = (v: number) => Number(v.toFixed(2));
const area = (id: string) => JSON.parse(fs.readFileSync(`content/areas/${id}.json`, "utf8"));

async function esperarJogo(p: Page, s: number) {
  const t0 = await tempo(p);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + s, { timeout: 240_000 });
}

async function interagir(p: Page) {
  await tecla(p, "KeyE", true); await esperarJogo(p, 0.1); await tecla(p, "KeyE", false);
}

async function camera(p: Page, yaw: number, pitch: number, extra = 0) {
  await p.evaluate(([y, pt, d]) => {
    (window.__vc.definirCamera as (y: number, p?: number) => void)(y, pt);
    (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = d;
  }, [yaw, pitch, extra] as const);
  await esperarJogo(p, 0.5);
}

/**
 * Anda pelos pontos (x, z) com direção forçada, a cada quadro do jogo. Devolve a menor altura dos pés,
 * o maior deslocamento num quadro (um salto grande seria a volta ao último chão firme depois de cair),
 * a distância no plano e as áreas atravessadas. Falha se ficar 4 s de jogo sem se aproximar do ponto.
 */
async function andar(p: Page, pontos: Ponto[], correr: boolean, tol: number): Promise<Resultado> {
  return p.evaluate(([pontos, correr, tol]) => new Promise<Resultado>((ok) => {
    const vc = window.__vc as Record<string, any>;
    const jogo = vc.jogo;
    let i = 0, yMin = Infinity, salto = 0, melhor = Infinity, dist = 0;
    let tMelhor = jogo.tempo;
    const t0 = jogo.tempo;
    const areas: string[] = [];
    let ant: { x: number; y: number; z: number } | null = null;
    const obs = jogo.cena.onBeforeRenderObservable.add(() => {
      const e = vc.estado();
      yMin = Math.min(yMin, e.y);
      if (ant) {
        const passo = Math.hypot(e.x - ant.x, e.y - ant.y, e.z - ant.z);
        salto = Math.max(salto, passo);
        dist += Math.hypot(e.x - ant.x, e.z - ant.z);
      }
      ant = { x: e.x, y: e.y, z: e.z };
      if (e.area && areas[areas.length - 1] !== e.area) areas.push(e.area);
      const [tx, tz] = pontos[i];
      const dx = tx - e.x, dz = tz - e.z;
      const d = Math.hypot(dx, dz);
      const ultimo = i === pontos.length - 1;
      const fim = (motivo?: string) => {
        jogo.cena.onBeforeRenderObservable.remove(obs);
        vc.direcaoForcada(null);
        vc.tecla("ShiftLeft", false);
        ok({ ok: !motivo, motivo, yMin, salto, x: e.x, y: e.y, z: e.z, t: jogo.tempo - t0, dist, areas });
      };
      if (d < (ultimo ? tol : Math.max(tol, 0.9))) {
        i++;
        melhor = Infinity;
        tMelhor = jogo.tempo;
        if (i >= pontos.length) return fim();
        return;
      }
      if (d < melhor - 0.05) { melhor = d; tMelhor = jogo.tempo; }
      if (jogo.tempo - tMelhor > 4) return fim(`parado perto de (${e.x.toFixed(2)}, ${e.y.toFixed(2)}, ${e.z.toFixed(2)}) indo para o ponto ${i} (${tx.toFixed(2)}, ${tz.toFixed(2)})`);
      vc.tecla("ShiftLeft", correr && d > 2.5);
      vc.direcaoForcada(dx / d, dz / d);
    });
  }), [pontos, correr, tol] as const);
}

/**
 * Afasta cada canto da rota do obstáculo que ele contorna (para fora da curva): os cantos do navmesh
 * ficam a um raio da cápsula da parede, e a cápsula raspando a quina perde velocidade.
 */
function afastarCantos(pts: Ponto[], afastamento = 0.35): Ponto[] {
  return pts.map((p, i) => {
    if (i === 0 || i === pts.length - 1) return p;
    const a = pts[i - 1], b = pts[i + 1];
    const l1 = Math.hypot(p[0] - a[0], p[1] - a[1]), l2 = Math.hypot(b[0] - p[0], b[1] - p[1]);
    if (l1 < 0.05 || l2 < 0.05) return p;
    const fx = (p[0] - a[0]) / l1 - (b[0] - p[0]) / l2, fz = (p[1] - a[1]) / l1 - (b[1] - p[1]) / l2;
    const n = Math.hypot(fx, fz);
    return n < 0.05 ? p : [p[0] + (fx / n) * afastamento, p[1] + (fz / n) * afastamento];
  });
}

/** Encaixa na escada com E e sobe (W) ou desce (S) até sair dela. */
async function usarEscada(p: Page, sentido: "subir" | "descer"): Promise<Estado> {
  await interagir(p);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado === "escada", null, { timeout: 30_000 });
  const k = sentido === "subir" ? "KeyW" : "KeyS";
  await tecla(p, k, true);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "escada", null, { timeout: 120_000 });
  await esperarJogo(p, sentido === "subir" ? 0.3 : 0.1);
  await tecla(p, k, false);
  await esperarJogo(p, 0.4);
  return estado(p);
}

type Trecho = { nome: string; navmesh_m: number; percorrido_m: number; tempo_s: number; yMin: number; salto: number; escadas: number; areas: string[]; areaFim?: string; mundoFim: string };

/**
 * Segue a rota do navmesh da posição atual até o alvo: anda pelos pedaços entre escadas e usa cada
 * escada (trecho quase vertical da rota) com E e W/S.
 */
async function seguir(p: Page, nome: string, alvo: V3, ext: V3 = [1.5, 1.5, 1.5], tolFim = 0.6): Promise<Trecho> {
  const e0 = await estado(p);
  const rota = await p.evaluate(([m, a, b, ext]) => (window.__vc.rotaNav as (m: string, a: V3, b: V3, e: V3) => Promise<Rota>)(m, a, b, ext),
    [e0.mundo, [e0.x, e0.y, e0.z] as V3, alvo, ext] as const);
  expect(rota.ok, `${nome}: rota do navmesh: ${rota.motivo}`).toBeTruthy();
  const t0 = await tempo(p);
  let pedaco: Ponto[] = [];
  let yMin = Infinity, salto = 0, dist = 0, escadas = 0;
  const areas: string[] = [];
  const juntar = (r: Resultado) => {
    yMin = Math.min(yMin, r.yMin); salto = Math.max(salto, r.salto); dist += r.dist;
    for (const a of r.areas) if (areas[areas.length - 1] !== a) areas.push(a);
  };
  const pts = rota.pontos;
  for (let i = 1; i <= pts.length; i++) {
    const escada = i < pts.length && Math.abs(pts[i][1] - pts[i - 1][1]) > 1.5 && Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]) < 2;
    pedaco.push([pts[i - 1][0], pts[i - 1][2]]);
    if (!escada && i < pts.length) continue;
    // anda até o pé (ou o topo) da escada, ou até o fim da rota
    const alvoPedaco = afastarCantos(pedaco).slice(1);
    if (alvoPedaco.length) {
      const r = await andar(p, alvoPedaco, !escada, escada ? 0.25 : tolFim);
      juntar(r);
      expect(r.ok, `${nome}: ${r.motivo}`).toBeTruthy();
    }
    if (escada) {
      const subir = pts[i][1] > pts[i - 1][1];
      const ePos = await usarEscada(p, subir ? "subir" : "descer");
      escadas++;
      expect(Math.abs(ePos.y - pts[i][1]), `${nome}: saída da escada ${escadas} em y ${ePos.y}`).toBeLessThan(0.6);
      yMin = Math.min(yMin, ePos.y);
      pedaco = [];
    }
  }
  const e = await estado(p);
  const fim = rota.pontos[rota.pontos.length - 1];
  expect(Math.hypot(e.x - fim[0], e.z - fim[2]), `${nome}: chegou ao alvo`).toBeLessThan(2);
  return { nome, navmesh_m: r2(rota.horizontal), percorrido_m: r2(dist), tempo_s: r2((await tempo(p)) - t0), yMin: r2(yMin), salto: r2(salto), escadas, areas, areaFim: e.area, mundoFim: e.mundo };
}

test.describe("fase 2: percurso das Galerias Secas até a Antena", () => {
  test.setTimeout(2_400_000);

  test("anda das Galerias à Antena pelo navmesh, sem travar nem cair", async ({ page }) => {
    await page.setViewportSize({ width: 640, height: 360 });
    const erros: string[] = [];
    page.on("console", (m) => { if (m.type() === "error" || /uniform|shader/i.test(m.text())) erros.push(m.text()); });
    await abrir(page, "area=vila_galerias&entrada=inicio&render=webgl2&qualidade=alta");
    await page.evaluate(() => {
      const j = window.__vc.jogo as any;
      j.estado.dar("filtro_reposicao", 2);
      j.cena.onBeforeRenderObservable.add(() => {
        j.epi.filtro = j.estado.capacidadeFiltro();
        j.epi.roupa = j.estado.capacidadeRoupa();
        j.epi.relogioTempestade = 1e4;
        j.epi.tempestade = "calma";
      });
    });
    await esperarJogo(page, 1.0);
    const t0 = Date.now();
    const e0 = await estado(page);
    expect(e0.area).toBe("vila_galerias");
    expect(e0.mundo).toBe("subsolo");
    const trechos: Trecho[] = [];
    const conferir = (t: Trecho, areaFim: string, mundo: string, yPiso: number, contem: string[] = []) => {
      trechos.push(t);
      expect(t.mundoFim, `${t.nome}: mundo`).toBe(mundo);
      expect(t.areaFim, `${t.nome}: área no fim`).toBe(areaFim);
      expect(t.yMin, `${t.nome}: caiu abaixo do piso`).toBeGreaterThan(yPiso);
      expect(t.salto, `${t.nome}: salto de posição (queda e volta ao chão firme)`).toBeLessThan(1.5);
      for (const a of contem) expect(t.areas, `${t.nome}: passou por ${a}`).toContain(a);
    };

    // 1. Galerias Secas -> praça da vila (pelo acesso das Galerias)
    conferir(await seguir(page, "galerias -> praça", [0, 0, -6]), "vila_praca", "subsolo", -5.5);
    // screenshot: das passarelas da vila (10 m), olhando a praça e a vila (critério da fase 2)
    const pas = area("vila_cisterna").entradas.passarela;
    const ePraca = await estado(page);
    await page.evaluate(([x, y, z]) => (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, 0), [pas.x, pas.y, pas.z] as const);
    await camera(page, 160 * GRAU, 14 * GRAU, 2.5);
    await esperarJogo(page, 3.0);
    await page.screenshot({ path: `${DIR}/percurso_01_passarela.png` });
    await page.evaluate(([x, y, z]) => (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, 0), [ePraca.x, ePraca.y, ePraca.z] as const);
    await esperarJogo(page, 1.0);

    // 2. praça -> Duto Norte (túnel, rampas e desvios dos destroços)
    conferir(await seguir(page, "praça -> Duto Norte", [-1, -4, 100], [2, 6, 2]), "duto_tunel", "subsolo", -8);
    // 3. Duto Norte -> Estação Aurora (fim do duto, plataforma)
    conferir(await seguir(page, "Duto Norte -> Estação Aurora", [150, -25, 205], [2, 2, 2]), "estacao_aurora", "subsolo", -26);
    // 4. Estação -> pé do poço -> quatro lances de escada -> porta externa da eclusa
    const eclusa = area("boca_estacao").saidas.find((s: { destino: string }) => s.destino === "superficie_boca");
    const poco = await seguir(page, "Estação -> poço -> eclusa", [eclusa.x, eclusa.y, eclusa.z - 0.5], [1, 1, 1], 0.3);
    conferir(poco, "boca_estacao", "subsolo", -26);
    expect(poco.escadas, "quatro lances de escada no poço").toBe(4);
    // 5. eclusa (E): troca para o mundo da superfície
    await interagir(page);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().mundo === "superficie_aberta", null, { timeout: 60_000 });
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "travado", null, { timeout: 60_000 });
    await esperarJogo(page, 1.0);
    const eSup = await estado(page);
    expect(eSup.area).toBe("superficie_boca");

    // 6. superfície: da Boca à Antena (topo da colina), medindo o fps correndo nas ruínas
    const antena: V3 = [38, 27.4, 484];
    const sup = seguir(page, "Boca -> Antena", antena, [4, 3, 4], 1.0);
    await esperarJogo(page, 4.0);
    const fpsCorrendo = await medirFps(page, 8);
    const tSup = await sup;
    conferir(tSup, "superficie_colina", "superficie_aberta", -6, ["superficie_boca", "superficie_ruinas", "superficie_rio", "superficie_colina"]);
    const eTopo = await estado(page);
    expect(eTopo.y, "no topo da colina").toBeGreaterThan(24);

    // 7. escada de mão até a plataforma do mirante e screenshot do alto da Antena, para o sul (Marco e vila ao fundo)
    const esc = area("superficie_colina").escadas[0];
    const rEsc = await andar(page, afastarCantos([[esc.x, (esc.z ?? 0) - 0.38]]), false, 0.25);
    expect(rEsc.ok, `pé da escada da Antena: ${rEsc.motivo}`).toBeTruthy();
    const plat = await usarEscada(page, "subir");
    expect(plat.y - eTopo.y).toBeGreaterThan(9);
    const fpsTopo = await medirFps(page, 5);
    await camera(page, 195 * GRAU, 10 * GRAU, 2.5);
    await esperarJogo(page, 3.0);
    await page.screenshot({ path: `${DIR}/percurso_02_antena.png` });

    const tempoTotal = trechos.reduce((s, t) => s + t.tempo_s, 0);
    registrar("fase-2", {
      percurso: {
        trechos, tempoDeJogo_s: r2(tempoTotal), tempoReal_s: Math.round((Date.now() - t0) / 1000),
        fpsSuperficieCorrendo: r2(fpsCorrendo), fpsAltoDaAntena: r2(fpsTopo), yPlataformaAntena: r2(plat.y), teleportes: "só para o screenshot das passarelas (ida e volta ao mesmo ponto da praça)",
      },
    });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
