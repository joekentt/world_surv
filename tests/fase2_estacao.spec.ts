import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

/**
 * Fase 2, tarefa 4 (revisão 2): Estação Aurora e Boca do Poço, em blocos, com a eclusa como troca de mundo
 * (subsolo <-> superfície). Percursos andando de verdade (física, degraus da escada rolante parada, escadas de
 * mão do poço), guiados por pontos de passagem no relógio do jogo. Layout em tools/areas/subsolo_estacao.py.
 */

type Estado = { x: number; y: number; z: number; estado: string; area?: string; mundo: string; yaw: number };
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

async function distanciaExtra(p: Page, d: number) {
  await p.evaluate((d) => { (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = d; }, d);
}

/**
 * Anda pelos pontos (x, z) com direção forçada, a cada quadro do jogo (dentro da página), e devolve
 * a menor altura dos pés no caminho e as áreas atravessadas. Falha se ficar 4 s de jogo sem avançar.
 */
async function rota(p: Page, pontos: Ponto[], correr = true, tol = 0.35): Promise<Resultado> {
  return p.evaluate(([pontos, correr, tol]) => new Promise<Resultado>((ok) => {
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
}

/** Encaixa na escada de mão com E e sobe (W) ou desce (S) até sair dela. */
async function usarEscada(p: Page, sentido: "subir" | "descer"): Promise<{ y: number; x: number; z: number; area?: string }> {
  await tecla(p, "KeyE", true); await esperarJogo(p, 0.1); await tecla(p, "KeyE", false);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado === "escada", null, { timeout: 30_000 });
  const k = sentido === "subir" ? "KeyW" : "KeyS";
  await tecla(p, k, true);
  await p.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "escada", null, { timeout: 120_000 });
  await esperarJogo(p, sentido === "subir" ? 0.3 : 0.1);
  await tecla(p, k, false);
  await esperarJogo(p, 0.4);
  const e = await estado(p);
  return { y: r2(e.y), x: r2(e.x), z: r2(e.z), area: e.area };
}

async function preparar(p: Page, consulta = "area=estacao_aurora&entrada=duto") {
  await p.setViewportSize({ width: 640, height: 360 });
  const erros: string[] = [];
  p.on("console", (m) => { if (m.type() === "error" || /uniform|shader/i.test(m.text())) erros.push(m.text()); });
  await abrir(p, `${consulta}&render=webgl2&qualidade=alta`);
  await esperarJogo(p, 1.0);
  return erros;
}

function exigir(r: Resultado, trecho: string) {
  expect(r.ok, `${trecho}: ${r.motivo}`).toBeTruthy();
}

/** Aperta E (interagir) por um instante. */
async function interagir(p: Page) {
  await tecla(p, "KeyE", true); await esperarJogo(p, 0.1); await tecla(p, "KeyE", false);
}

/** Pontos de pé das escadas do poço (base = 0,38 m atrás do eixo, ver Jogador.pontosEscada). */
const BASE_A: Ponto = [176.2, 204.37];   // A e C: ao sul da coluna central, sobem olhando para o norte
const BASE_B: Ponto = [177.6, 205.63];   // B e D: ao norte da coluna, sobem olhando para o sul

/** Sobe o poço inteiro, de -25 a 0, pelos quatro lances; devolve os patamares e o tempo de jogo. */
async function subirPoco(p: Page) {
  const t0 = await tempo(p);
  const patamares: number[] = [];
  let area: string | undefined;
  for (let i = 0; i < 4; i++) {
    const r = await rota(p, [i % 2 === 0 ? BASE_A : BASE_B], false, 0.2);
    exigir(r, `pé da escada ${i + 1}`);
    const topo = await usarEscada(p, "subir");
    patamares.push(topo.y);
    area = topo.area;
  }
  return { patamares, area, tempo_s: r2((await tempo(p)) - t0) };
}

test.describe("fase 2: Estação Aurora e Boca do Poço", () => {
  test.setTimeout(1_200_000);

  test("a) do fim do duto à estação, andando, e pela escada rolante parada até o mezanino", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    const ini = await estado(page);
    expect(ini.area).toBe("duto_tunel");
    expect(ini.mundo).toBe("subsolo");

    // pelo portão aberto do fim do duto até a ilha da plataforma
    let r = await rota(page, [[139, 205], [143, 205], [150, 205], [156, 203.85]]);
    exigir(r, "portão do duto até a escada rolante");
    m.portao = { areas: r.areas, yMinimo: r2(r.yMin), yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(r.areas).toEqual(expect.arrayContaining(["duto_tunel", "estacao_aurora"]));
    expect(r.y).toBeGreaterThan(-25.1);
    expect(r.y).toBeLessThan(-24.9);

    // escada rolante sul (24 degraus de 0,25 m), andando, até o mezanino em -19
    r = await rota(page, [[163, 203.85], [169.6, 203.85], [172, 200.6]], false);
    exigir(r, "subindo a escada rolante");
    const mez = await estado(page);
    m.escadaRolante = { yFinal: r2(mez.y), tempo_s: r2(r.t), area: mez.area };
    expect(mez.y).toBeGreaterThan(-19.1);
    expect(mez.y).toBeLessThan(-18.9);
    expect(mez.area).toBe("estacao_aurora");

    // pelo mezanino, contornando o poço, até os bancos do ponto de descanso
    r = await rota(page, [[182, 200.6], [187.5, 205.0], [190.0, 208.4]]);
    exigir(r, "mezanino até o ponto de descanso");
    m.pontoDeDescanso = { x: r2(r.x), y: r2(r.y), z: r2(r.z) };
    expect(r.y).toBeGreaterThan(-19.1);

    // desce pela outra escada rolante e vai até a porta do poço, na face sul
    r = await rota(page, [[182, 209.5], [172, 209.5], [169.6, 206.15], [158, 206.15], [156, 201.2], [176.85, 200.8], [176.85, 203.2]], false);
    exigir(r, "descida e porta do poço");
    m.descidaAtePoco = { yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(r.y).toBeGreaterThan(-25.1);
    expect(r.y).toBeLessThan(-24.9);

    // screenshot: plataforma com as escadas rolantes paradas e o mezanino ao fundo
    await posicionar(page, 148.0, -25, 201.0, 72 * GRAU, 72 * GRAU, 14 * GRAU);
    await distanciaExtra(page, 3.5);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/estacao_01_escadas_rolantes.png" });
    await distanciaExtra(page, 0);

    m.errosConsole = erros.length;
    registrar("fase-2", { estacao_a_duto_ate_mezanino: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("b) sobe o poço de 25 m pela escada de mão até a eclusa", async ({ page }) => {
    const erros = await preparar(page, "area=estacao_aurora&entrada=poco");
    const m: Record<string, unknown> = {};
    const ini = await estado(page);
    expect(ini.area).toBe("estacao_aurora");
    expect(ini.y).toBeLessThan(-24.9);

    // screenshot: o poço visto de baixo (personagem a 2 m do fundo na primeira escada, câmera olhando para cima)
    let r = await rota(page, [BASE_A], false, 0.2);
    exigir(r, "pé da primeira escada");
    await interagir(page);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().estado === "escada", null, { timeout: 30_000 });
    await tecla(page, "KeyW", true);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().y > -23.2, null, { timeout: 30_000 });
    await tecla(page, "KeyW", false);
    await page.evaluate((y) => (window.__vc.definirCamera as (y: number, p?: number) => void)(y, -30 * Math.PI / 180), -12 * GRAU);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/estacao_02_poco_de_baixo.png" });
    await tecla(page, "KeyS", true);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "escada", null, { timeout: 30_000 });
    await tecla(page, "KeyS", false);
    await esperarJogo(page, 0.5);

    const s = await subirPoco(page);
    m.subida = s;
    expect(s.patamares[0]).toBeGreaterThan(-18.8);
    expect(s.patamares[1]).toBeGreaterThan(-12.6);
    expect(s.patamares[2]).toBeGreaterThan(-6.3);
    expect(s.patamares[3]).toBeGreaterThan(-0.1);
    expect(s.patamares[3]).toBeLessThan(0.1);
    expect(s.area).toBe("boca_estacao");
    m.desnivel_m = r2(s.patamares[3] - ini.y);

    // da escada até a porta externa da eclusa, pela casa do poço e pelos chuveiros
    r = await rota(page, [[174.0, 204.0], [174.0, 208.8], [178.0, 209.6], [178.0, 213.0], [178.0, 217.0], [178.0, 219.1]], false);
    exigir(r, "topo do poço até a eclusa");
    m.ateEclusa = { x: r2(r.x), y: r2(r.y), z: r2(r.z), tempo_s: r2(r.t) };
    expect(r.yMin).toBeGreaterThan(-0.1);

    // screenshot: descontaminação e eclusa, olhando para a porta externa
    await posicionar(page, 178.6, 0, 211.2, 0, 4 * GRAU, 8 * GRAU);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/estacao_03_eclusa_descontaminacao.png" });

    m.errosConsole = erros.length;
    registrar("fase-2", { estacao_b_poco: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("c) usa a eclusa (E) para chegar à superfície e volta pela eclusa ao subsolo", async ({ page }) => {
    const erros = await preparar(page, "area=boca_estacao&entrada=superficie");
    const m: Record<string, unknown> = {};
    await page.evaluate(() => (window.__vc.jogo as { estado: { dar: (k: string, n: number) => void } }).estado.dar("filtro_reposicao", 2));
    let e = await estado(page);
    expect(e.area).toBe("boca_estacao");
    expect(e.mundo).toBe("subsolo");

    const r = await rota(page, [[178.0, 219.1]], false, 0.25);
    exigir(r, "até a porta externa");
    const t0 = await tempo(page);
    await interagir(page);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().mundo === "superficie_aberta", null, { timeout: 60_000 });
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "travado", null, { timeout: 60_000 });
    await esperarJogo(page, 1.0);
    e = await estado(page);
    m.subida = { mundo: e.mundo, area: e.area, x: r2(e.x), y: r2(e.y), z: r2(e.z), tempo_eclusa_s: r2((await tempo(page)) - t0) };
    expect(e.area).toBe("superficie_boca");
    expect(Math.hypot(e.x - 0, e.z - 3)).toBeLessThan(1.0);
    const carregadas = await page.evaluate(() => [...(window.__vc.jogo as { areas: { carregadas: Map<string, unknown> } }).areas.carregadas.keys()]);
    m.subida = { ...(m.subida as object), areasCarregadas: carregadas };
    expect(carregadas).not.toContain("estacao_aurora");
    expect(carregadas).not.toContain("boca_estacao");

    // screenshot: saída na superfície
    await posicionar(page, 0, 0, 3, 0, 180 * GRAU, 12 * GRAU);
    await esperarJogo(page, 3.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/estacao_04_saida_superficie.png" });

    // volta: eclusa da superfície -> topo do poço (entrada "superficie")
    await posicionar(page, 0, 0, 2.0, 180 * GRAU);
    const r2v = await rota(page, [[0, 0.9]], false, 0.25);
    exigir(r2v, "até a eclusa na superfície");
    const t1 = await tempo(page);
    await interagir(page);
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().mundo === "subsolo", null, { timeout: 60_000 });
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().estado !== "travado", null, { timeout: 60_000 });
    await esperarJogo(page, 1.0);
    e = await estado(page);
    m.volta = { mundo: e.mundo, area: e.area, x: r2(e.x), y: r2(e.y), z: r2(e.z), tempo_eclusa_s: r2((await tempo(page)) - t1) };
    expect(e.mundo).toBe("subsolo");
    expect(e.area).toBe("boca_estacao");
    expect(Math.hypot(e.x - 178, e.z - 217.6)).toBeLessThan(1.0);
    expect(Math.abs(e.y)).toBeLessThan(0.1);

    m.errosConsole = erros.length;
    registrar("fase-2", { estacao_c_eclusa: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
