import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

type Estado = { x: number; y: number; area?: string; mundo: string };
const estado = (p: Page) => p.evaluate(() => (window.__vc.estado as () => Estado)());
const teleportar = (p: Page, x: number, y = 0) =>
  p.evaluate(([x, y]) => (window.__vc.teleportar as (x: number, y: number) => void)(x, y), [x, y]);
const carregadas = (p: Page) => p.evaluate(() => [...(window.__vc.jogo as { areas: { carregadas: Map<string, unknown> } }).areas.carregadas.keys()].sort());

async function interagir(p: Page, mundoEsperado: string) {
  await p.evaluate(() => (window.__vc.tecla as (c: string, v: boolean) => void)("KeyE", true));
  await p.waitForTimeout(400);
  await p.evaluate(() => (window.__vc.tecla as (c: string, v: boolean) => void)("KeyE", false));
  await p.waitForFunction((m) => (window.__vc.estado as () => { mundo: string })().mundo === m, mundoEsperado, { timeout: 90_000 });
}

async function foto(p: Page, nome: string) {
  await p.waitForTimeout(3000);
  await p.screenshot({ path: `tests/screenshots/fase-2/${nome}.png` });
}

test("fase 2: percurso das Galerias Secas até a Antena", async ({ page }) => {
  test.setTimeout(600_000);
  const t0 = Date.now();
  await abrir(page, "area=galerias&render=webgl2");
  await teleportar(page, 120);
  await foto(page, "01_galerias");
  // streaming dentro da vila: a capela ainda não deve estar carregada
  expect(await carregadas(page)).not.toContain("capela");
  await teleportar(page, 0);
  await foto(page, "02_praca");
  await teleportar(page, -100);
  await page.waitForFunction(() => [...(window.__vc.jogo as { areas: { carregadas: Map<string, unknown> } }).areas.carregadas.keys()].includes("capela"), null, { timeout: 60_000 });
  await foto(page, "03_capela");
  expect(await carregadas(page)).not.toContain("galerias");
  // escotilha do Duto Norte, no alto da escada da praça
  await teleportar(page, 49.5, 5.0);
  await page.waitForTimeout(1500);
  await interagir(page, "duto");
  await foto(page, "04_duto_tunel");
  await teleportar(page, 100, 1.1);
  await foto(page, "05_duto_caverna");
  await teleportar(page, 129.5, 2.2);
  await page.waitForTimeout(800);
  await interagir(page, "boca");
  await foto(page, "06_boca_do_poco");
  await teleportar(page, 35.5);
  await page.waitForTimeout(800);
  await interagir(page, "superficie");
  await foto(page, "07_superficie_sucata");
  for (const [x, nome] of [[180, "08_superficie_ruinas"], [250, "09_marco"], [340, "10_superficie_antena"], [446, "11_antena"]] as const) {
    await teleportar(page, x);
    await page.waitForFunction((x) => (window.__vc.estado as () => { area?: string })().area !== undefined, x, { timeout: 60_000 });
    await foto(page, nome);
  }
  const fim = await estado(page);
  expect(fim.area).toBe("superficie_antena");
  expect(await carregadas(page)).not.toContain("superficie_sucata");
  registrar("fase-2", { percursoSegundos: Math.round((Date.now() - t0) / 1000), areasNoFim: await carregadas(page) });
});
