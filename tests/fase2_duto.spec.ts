import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

/**
 * Fase 2, tarefa 3 (revisão 2): Duto Norte, Caverna da Fenda e Galeria dos Contrabandistas, em blocos.
 * Percursos andando de verdade (física, rampas, degraus e escada de mão), guiados por pontos de passagem
 * no relógio do jogo. Layout em tools/areas/subsolo_duto.py.
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

test.describe("fase 2: Duto Norte, Caverna da Fenda e Galeria dos Contrabandistas", () => {
  test.setTimeout(1_200_000);

  test("a) da praça da vila ao fim do Duto Norte, andando pelas rampas e pelos desvios dos destroços", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    await posicionar(page, 0, 0, -6, 0);
    expect((await estado(page)).area).toBe("vila_praca");

    // praça -> boca do duto na parede norte -> primeira rampa (0 -> -5 m)
    let r = await rota(page, [[-1, 30], [-1, 44], [-1, 60], [-1, 100]]);
    exigir(r, "praça até o pé da primeira rampa");
    m.boca_e_rampa1 = { areas: r.areas, yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(r.areas).toEqual(expect.arrayContaining(["vila_praca", "vila_cisterna", "duto_tunel"]));
    expect(r.y).toBeGreaterThan(-5.1);
    expect(r.y).toBeLessThan(-4.9);
    let yMin = r.yMin;

    // desabamento: sobe os degraus da plataforma de manutenção e passa por cima dela
    r = await rota(page, [[2.75, 106], [2.75, 108.2], [2.75, 125]]);
    exigir(r, "subindo na plataforma");
    const naPlataforma = r2(r.y);
    expect(naPlataforma).toBeGreaterThan(-4.2);
    r = await rota(page, [[2.75, 146], [-1, 149]]);
    exigir(r, "descendo da plataforma");
    m.desvioDesabamento = { yNaPlataforma: naPlataforma, yDepois: r2(r.y) };
    yMin = Math.min(yMin, r.yMin);

    // segunda rampa (-5 -> -10 m) com o vagonete descarrilado: desvio pela faixa oeste
    r = await rota(page, [[-1, 166], [-2.6, 170.5], [-2.6, 181], [-1, 184.5], [-1, 197]]);
    exigir(r, "rampa 2 e vagonete");
    m.rampa2 = { yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(r.y).toBeLessThan(-9.9);
    yMin = Math.min(yMin, r.yMin);

    // curva e trecho leste: rampas até -20 m, vagão tombado (desvio pela faixa norte) e rampa final até -25 m
    r = await rota(page, [[0, 205], [8, 205], [60, 205]]);
    exigir(r, "curva e rampa 3");
    r = await rota(page, [[93, 205], [94, 207.6], [115, 207.6], [117, 205], [138.5, 205]]);
    exigir(r, "vagão tombado e rampa final");
    yMin = Math.min(yMin, r.yMin);
    const fim = await estado(page);
    m.fimDoDuto = { x: r2(fim.x), y: r2(fim.y), z: r2(fim.z), area: fim.area };
    expect(fim.area).toBe("duto_tunel");
    expect(fim.y).toBeGreaterThan(-25.1);
    expect(fim.y).toBeLessThan(-24.9);
    m.yMinimoNoPercurso = r2(yMin);
    expect(yMin).toBeGreaterThan(-25.2);

    // screenshot: trecho norte, de frente para o desabamento, com a lanterna e a plataforma de manutenção à direita
    await posicionar(page, -1.2, -5, 107, 4 * GRAU, 4 * GRAU, 6 * GRAU);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/duto_01_tunel_lanterna.png" });

    m.errosConsole = erros.length;
    registrar("fase-2", { duto_a_vila_ate_o_fim: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("b) Caverna da Fenda: atravessa a ponte de corda andando, volta ao duto pelo circuito e sobe ao mirante", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    await posicionar(page, -1, -5, 100, 90 * GRAU);

    // passagem A até a cabeceira sul da ponte
    let r = await rota(page, [[3, 103], [14, 103], [30, 104], [40, 110], [40, 116.8]]);
    exigir(r, "passagem A até a ponte");
    m.passagemA = { areas: r.areas };
    expect(r.areas).toEqual(expect.arrayContaining(["duto_tunel", "duto_fenda"]));

    // ponte: 22 m andando, de cabeceira a cabeceira
    r = await rota(page, [[40, 129]], false, 0.3);
    exigir(r, "primeira metade da ponte");
    const meio = await estado(page);
    r = await rota(page, [[40, 141.4]], false, 0.3);
    exigir(r, "segunda metade da ponte");
    m.ponte = { yMeio: r2(meio.y), areaMeio: meio.area, yMinimo: r2(r.yMin), yFinal: r2(r.y), tempo_s: r2(r.t) };
    expect(meio.area).toBe("duto_fenda");
    expect(meio.y).toBeLessThan(-5.4);
    expect(r.yMin).toBeGreaterThan(-5.9);
    expect(r.y).toBeGreaterThan(-5.1);

    // mirante: escadaria esculpida até 4 m acima da borda, avançando sobre o abismo
    r = await rota(page, [[44, 144], [47, 144], [55, 144], [60, 137]]);
    exigir(r, "subida ao mirante");
    m.mirante = { y: r2(r.y), x: r2(r.x), z: r2(r.z) };
    expect(r.y).toBeGreaterThan(-1.1);
    expect(r.y).toBeLessThan(-0.9);
    await posicionar(page, 54.8, -1, 135, -115 * GRAU, -115 * GRAU, 32 * GRAU);
    await distanciaExtra(page, 3.0);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/duto_03_mirante_fenda.png" });
    await distanciaExtra(page, 0);

    // volta ao duto pela passagem B (circuito)
    r = await rota(page, [[55, 144], [47, 144], [40, 150], [30, 155], [14, 155], [2, 155]]);
    exigir(r, "passagem B de volta ao duto");
    m.voltaPassagemB = { areas: r.areas, yFinal: r2(r.y) };
    expect((await estado(page)).area).toBe("duto_tunel");

    // ponte vista de lado: personagem no meio da ponte olhando para oeste, câmera a leste e um pouco acima
    await posicionar(page, 40, -5.7, 128, -90 * GRAU, -90 * GRAU, 38 * GRAU);
    await distanciaExtra(page, 3.5);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/duto_02_ponte_abismo.png" });
    await distanciaExtra(page, 0);

    m.errosConsole = erros.length;
    registrar("fase-2", { duto_b_fenda: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });

  test("c) Galeria dos Contrabandistas até a escada da Escotilha Oeste e subida até o alçapão", async ({ page }) => {
    const erros = await preparar(page);
    const m: Record<string, unknown> = {};
    await posicionar(page, 0, -10, 205, 0);
    expect((await estado(page)).area).toBe("duto_tunel");

    let r = await rota(page, [[0, 212], [0, 249], [0, 253], [0, 281]]);
    exigir(r, "galeria até o depósito");
    m.trecho1 = { areas: r.areas, yFinal: r2(r.y) };
    expect(r.areas).toContain("duto_contrabandistas");
    expect(r.y).toBeGreaterThan(-8.6);

    // screenshot: galeria estreita, olhando para o depósito
    await posicionar(page, 0, -8.5, 270, 0, 0, 2 * GRAU);
    await esperarJogo(page, 5.0);
    await page.screenshot({ path: "tests/screenshots/fase-2/duto_04_galeria.png" });

    r = await rota(page, [[0, 287], [0, 299], [0, 303], [0, 313], [0, 318.7]], true, 0.25);
    exigir(r, "depósito até a escada da escotilha");
    m.baseEscada = { x: r2(r.x), y: r2(r.y), z: r2(r.z), tempo_s: r2(r.t) };
    expect(r.y).toBeGreaterThan(-7.1);

    const topo = await usarEscada(page, "subir");
    m.topoEscada = topo;
    m.distanciaAteOAlcapao = r2(3.6 - topo.y);
    expect(topo.area).toBe("duto_contrabandistas");
    expect(topo.y).toBeGreaterThan(0.9);
    expect(topo.z).toBeGreaterThan(319.6);

    m.errosConsole = erros.length;
    registrar("fase-2", { duto_c_galeria: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
