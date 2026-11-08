import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

/**
 * Fase 2, tarefa 2 (revisão 2): Vila Cisterna em três níveis, em blocos.
 * Percursos andando de verdade (física e escadas), guiados por pontos de passagem no relógio do jogo.
 * Layout em tools/areas/subsolo_vila.py.
 */

type Estado = { x: number; y: number; z: number; estado: string; area?: string; yaw: number };
type Ponto = [number, number];
type Resultado = { ok: boolean; motivo?: string; yMin: number; x: number; y: number; z: number; t: number; areas: string[] };

const GRAU = Math.PI / 180;
const js = <T = unknown>(p: Page, f: string) => p.evaluate(f) as Promise<T>;
const estado = (p: Page) => js<Estado>(p, "window.__vc.estado()");
const tempo = (p: Page) => js<number>(p, "window.__vc.jogo.tempo");
const tecla = (p: Page, c: string, v: boolean) => p.evaluate(([c, v]) => (window.__vc.tecla as (c: string, v: boolean) => void)(c as string, v as boolean), [c, v] as const);
const r2 = (v: number) => Number(v.toFixed(2));

async function esperarJogo(p: Page, s: number) {
  const t0 = await tempo(p);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + s, { timeout: 240_000 });
}

async function posicionar(p: Page, x: number, y: number, z: number, yaw: number, yawCamera = yaw, pitch?: number) {
  await p.evaluate(([x, y, z, yp, yc, pt]) => {
    (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, yp);
    (window.__vc.definirCamera as (y: number, p?: number) => void)(yc, pt ?? undefined);
  }, [x, y, z, yaw, yawCamera, pitch ?? null] as const);
  await esperarJogo(p, 0.6);
}

/**
 * Anda pelos pontos (x, z) com direção forçada, a cada quadro do jogo (dentro da página), e devolve
 * a menor altura dos pés no caminho e as áreas atravessadas. Falha se ficar 4 s de jogo sem avançar.
 */
async function rota(p: Page, pontos: Ponto[], correr = true, tol = 0.35): Promise<Resultado> {
  const r = await p.evaluate(([pontos, correr, tol]) => new Promise<Resultado>((ok) => {
    const vc = window.__vc as Record<string, any>;
    const jogo = vc.jogo;
    let i = 0;
    let yMin = Infinity;
    let melhor = Infinity;
    let tMelhor = jogo.tempo;
    const t0 = jogo.tempo;
    const areas: string[] = [];
    const obs = jogo.cena.onBeforeRenderObservable.add(() => {
      const e = vc.estado();
      yMin = Math.min(yMin, e.y);
      if (e.area && areas[areas.length - 1] !== e.area) areas.push(e.area);
      const [tx, tz] = pontos[i];
      const dx = tx - e.x, dz = tz - e.z;
      const d = Math.hypot(dx, dz);
      const ultimo = i === pontos.length - 1;
      const fim = (motivo?: string) => {
        jogo.cena.onBeforeRenderObservable.remove(obs);
        vc.direcaoForcada(null);
        vc.tecla("ShiftLeft", false);
        ok({ ok: !motivo, motivo, yMin, x: e.x, y: e.y, z: e.z, t: jogo.tempo - t0, areas });
      };
      if (d < (ultimo ? tol : Math.max(tol, 0.6))) {
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
  return r;
}

/** Encaixa na escada de mão com E e sobe (W) ou desce (S) até sair dela. */
async function usarEscada(p: Page, sentido: "subir" | "descer"): Promise<{ y: number; x: number; z: number }> {
  await tecla(p, "KeyE", true); await esperarJogo(p, 0.1); await tecla(p, "KeyE", false);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado === "escada", null, { timeout: 30_000 });
  const k = sentido === "subir" ? "KeyW" : "KeyS";
  await tecla(p, k, true);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "escada", null, { timeout: 120_000 });
  await esperarJogo(p, sentido === "subir" ? 0.3 : 0.1);
  await tecla(p, k, false);
  await esperarJogo(p, 0.4);
  const e = await estado(p);
  return { y: r2(e.y), x: r2(e.x), z: r2(e.z) };
}

async function preparar(p: Page) {
  await p.setViewportSize({ width: 640, height: 360 });
  const erros: string[] = [];
  p.on("console", (m) => { if (m.type() === "error" || /uniform|shader/i.test(m.text())) erros.push(m.text()); });
  await abrir(p, "area=vila_cisterna&render=webgl2&qualidade=alta");
  await esperarJogo(p, 1.0);
  return erros;
}

function exigir(r: Resultado, trecho: string) {
  expect(r.ok, `${trecho}: ${r.motivo}`).toBeTruthy();
}

test.describe("fase 2: Vila Cisterna em três níveis", () => {
  test.setTimeout(1_200_000);

  test("a) da praça às passarelas pela escada de mão e pela escadaria, até a Capela a 10 m", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    const e0 = await estado(page);
    m.inicio = { area: e0.area, y: r2(e0.y), mundo: (e0 as unknown as { mundo: string }).mundo };
    expect(e0.area).toBe("vila_praca");

    // praça (a ponte da passarela a 8 m passa por cima) com o Portão da Caravana ao fundo
    await posicionar(page, 0, 0, -6, 180 * GRAU, 180 * GRAU, 0);
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 1.5; });
    await esperarJogo(page, 5.0); // espera o nome da área sumir
    await page.screenshot({ path: "tests/screenshots/fase-2/vila_01_praca_portao.png" });
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 0; });

    // 1) escada de mão: praça -> pé da escada da passarela leste -> sobe com E e W -> Capela pela porta sul
    await posicionar(page, 0, 0, -12, 90 * GRAU);
    let r = await rota(page, [[0, -4.2], [44, -4.2], [49.45, -5]]);
    exigir(r, "até a escada de mão");
    m.escadaDeMao_chaoYMin = r2(r.yMin);
    const topo = await usarEscada(page, "subir");
    m.escadaDeMao_topo = topo;
    expect(topo.y).toBeGreaterThan(9.9);
    r = await rota(page, [[51.5, -4], [51.5, 9], [51.5, 11], [51.5, 14.5]]);
    exigir(r, "passarela leste até a Capela");
    m.passarelaLeste = { yMin: r2(r.yMin), yFinal: r2(r.y), areas: r.areas };
    expect(r.yMin).toBeGreaterThan(9.8);
    expect(r.areas).toContain("vila_capela");
    let e = await estado(page);
    expect(e.area).toBe("vila_capela");
    expect(e.y).toBeGreaterThan(9.8);

    // 2) escadaria: praça -> pé da escadaria -> dois lances até 10 m -> passarela norte -> Capela pela porta oeste
    await posicionar(page, 0, 0, -12, 0);
    r = await rota(page, [[-3, 13.5], [-40, 13.5], [-40, 20.5], [-37.5, 20.5]]);
    exigir(r, "até a escadaria");
    r = await rota(page, [[-18.5, 20.5], [-18.5, 23.5]], false);
    exigir(r, "subindo a escadaria");
    m.escadaria = { yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(r.y).toBeGreaterThan(9.9);
    // vista do alto (sacada da Capela, 10 m): mercado, praça, colunas e casas até o fundo da caverna
    await posicionar(page, 45, 10, 10.6, 245 * GRAU, 245 * GRAU, 18 * GRAU);
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 2.5; });
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/vila_02_vista_passarela.png" });
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 0; });
    await posicionar(page, -18.5, 10, 23.5, 90 * GRAU);
    r = await rota(page, [[43, 23.5], [48, 23.5]]);
    exigir(r, "passarela norte até a Capela");
    m.passarelaNorte = { yMin: r2(r.yMin), yFinal: r2(r.y), areas: r.areas };
    expect(r.yMin).toBeGreaterThan(9.8);
    e = await estado(page);
    expect(e.area).toBe("vila_capela");
    m.capela = { area: e.area, y: r2(e.y) };

    // Capela: facho sobre o altar, vitrais, bancos
    await posicionar(page, 50, 10, 22, 90 * GRAU, 90 * GRAU, 4 * GRAU);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/vila_04_capela.png" });

    m.errosConsole = erros.length;
    registrar("fase-2", { vila_a_passarelas: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("b) praça -> Galerias pelo acesso oeste -> fundo do poço de 20 m -> volta à praça pelo acesso leste", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    const escadas: unknown[] = [];

    await posicionar(page, 0, 0, -12, 0);
    // acesso oeste: escadaria de 5 m até o corredor G1
    let r = await rota(page, [[-3, -0.25], [-25, -0.25], [-35.75, -0.25]]);
    exigir(r, "descendo o acesso oeste");
    m.acessoOeste = { yFinal: r2(r.y), areas: r.areas };
    expect(r.y).toBeLessThan(-4.9);
    expect(r.y).toBeGreaterThan(-5.2);
    expect(r.areas).toContain("vila_galerias");
    // G1 até o andar de entrada do poço (-5) e topo da primeira escada
    r = await rota(page, [[-35.75, -12], [-35.75, -18.5], [-35, -19.9]], false, 0.3);
    exigir(r, "G1 até o poço");
    let yMin = r.yMin;

    // vista do poço desde a boca no piso da caverna: barracos em andares, escadas e a grade lá embaixo
    await posicionar(page, -40, 0, -31.5, 0, 0, 65 * GRAU);
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 2.5; });
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/vila_03_poco_galerias.png" });
    await page.evaluate(() => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = 0; });
    await posicionar(page, -35, -5, -19.9, 180 * GRAU);

    // descida: quatro escadas de mão de 5 m (-5 -> -10 -> -15 -> -20 -> -25)
    const descida: [Ponto[]][] = [[[[-35.6, -24], [-36.3, -28.6], [-36.3, -29]]], [[[-40, -28], [-45, -28], [-45, -27.7]]], [[[-44.2, -25.5], [-43.8, -19.6], [-43.7, -19]]], [[]]];
    for (const [i, [caminho]] of descida.entries()) {
      const s = await usarEscada(page, "descer");
      escadas.push({ desceu: i + 1, ...s });
      yMin = Math.min(yMin, s.y);
      if (caminho.length) {
        r = await rota(page, caminho, false, 0.3);
        exigir(r, `andar ${i + 1} do poço`);
        yMin = Math.min(yMin, r.yMin);
      }
    }
    // no fundo: anda sobre a grade do poço profundo
    r = await rota(page, [[-40, -20], [-40, -24]], false);
    exigir(r, "sobre a grade");
    const fundo = await estado(page);
    m.fundoDoPoco = { y: r2(fundo.y), area: fundo.area };
    m.alturaDoPoco = r2(-5 - fundo.y);
    expect(fundo.y).toBeGreaterThan(-25.2);
    expect(fundo.y).toBeLessThan(-24.8);
    yMin = Math.min(yMin, r.yMin);

    // subida pelas mesmas escadas
    const subida: Ponto[][] = [[[-42.57, -19]], [[-43.8, -19.6], [-44.6, -25.5], [-45, -26.57]], [[-44, -28], [-37.43, -28.4], [-37.43, -29]], [[-36.2, -27], [-35.2, -22.5], [-35, -21.43]]];
    for (const [i, caminho] of subida.entries()) {
      r = await rota(page, caminho, false, 0.25);
      exigir(r, `até a escada ${i + 1} da subida`);
      const s = await usarEscada(page, "subir");
      escadas.push({ subiu: i + 1, ...s });
    }
    const andar5 = await estado(page);
    expect(andar5.y).toBeGreaterThan(-5.1);

    // volta pelo G1 e pelo G3 (sob a praça) até o acesso leste, que sobe para o piso da caverna
    r = await rota(page, [[-35.75, -18.5], [-35.75, -12], [-30, -12], [29, -12], [39.5, -12], [39.5, -8.5], [22, -8.5]]);
    exigir(r, "G3 e acesso leste");
    yMin = Math.min(yMin, r.yMin);
    m.voltaPraca = { y: r2(r.y), areas: r.areas, tempo_s: r2(r.t) };
    const fim = await estado(page);
    expect(fim.y).toBeGreaterThan(-0.1);
    expect(fim.y).toBeLessThan(0.3);
    expect(fim.area).toBe("vila_praca");
    m.escadas = escadas;
    m.yMinimoNoPercurso = r2(yMin);
    expect(yMin).toBeGreaterThan(-25.3);
    m.errosConsole = erros.length;
    registrar("fase-2", { vila_b_galerias: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
