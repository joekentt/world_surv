import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

type Epi = { filtro: number; roupa: number; saude: number; ativo: boolean; tempestade: string; morto: boolean };
const epi = (p: Page) => p.evaluate(() => (window.__vc.epi as () => Epi)());
const est = (p: Page) => p.evaluate(() => (window.__vc.estado as () => { x: number; mundo: string; area?: string })());
const jogo = (p: Page, f: string) => p.evaluate(f);
const teleportar = (p: Page, x: number, y = 0) => p.evaluate(([x, y]) => (window.__vc.teleportar as (x: number, y: number) => void)(x, y), [x, y]);
async function apertarE(p: Page) {
  await p.evaluate(() => (window.__vc.tecla as (c: string, v: boolean) => void)("KeyE", true));
  await p.waitForTimeout(500);
  await p.evaluate(() => (window.__vc.tecla as (c: string, v: boolean) => void)("KeyE", false));
}
const tempoJogo = (p: Page) => p.evaluate(() => (window.__vc.jogo as { tempo: number }).tempo);
async function esperarJogo(p: Page, s: number) {
  const t0 = await tempoJogo(p);
  await p.waitForFunction((a) => (window.__vc.jogo as { tempo: number }).tempo >= a, t0 + s, { timeout: 120_000 });
}

test("fase 3: subida completa com EPI, coleta, tempestade, morte e volta", async ({ page }) => {
  test.setTimeout(600_000);
  await abrir(page, "area=boca_do_poco&render=webgl2");
  // sobe pela eclusa
  await teleportar(page, 35.5);
  await page.waitForTimeout(800);
  await apertarE(page);
  await page.waitForFunction(() => (window.__vc.estado as () => { mundo: string })().mundo === "superficie", null, { timeout: 90_000 });
  await page.waitForFunction(() => (window.__vc.epi as () => { ativo: boolean })().ativo, null, { timeout: 30_000 });
  const e0 = await epi(page);
  expect(e0.filtro).toBeGreaterThan(80);
  const filtros = await jogo(page, "window.__vc.jogo.estado.qtd('filtro_reposicao')");
  expect(filtros).toBe(1);
  await esperarJogo(page, 3);
  const e1 = await epi(page);
  expect(e1.filtro).toBeLessThan(e0.filtro - 2);
  expect(e1.roupa).toBeLessThan(e0.roupa);
  await page.screenshot({ path: "tests/screenshots/fase-3/01_superficie_hud.png" });

  // coleta: sucata em x = 26
  await teleportar(page, 26);
  await page.waitForTimeout(1500);
  await apertarE(page);
  await page.waitForFunction(() => ((window.__vc.jogo as { estado: { qtd(i: string): number } }).estado.qtd("sucata")) >= 1, null, { timeout: 30_000 });
  await page.screenshot({ path: "tests/screenshots/fase-3/02_coleta.png" });

  // limite de peso
  await jogo(page, "window.__vc.jogo.estado.dar('sucata', 9)");
  await teleportar(page, 33);
  await page.waitForTimeout(1500);
  await apertarE(page);
  await page.waitForTimeout(1500);
  expect(await jogo(page, "window.__vc.jogo.estado.qtd('sucata')")).toBe(10);
  await page.screenshot({ path: "tests/screenshots/fase-3/03_mochila_cheia.png" });
  await jogo(page, "window.__vc.jogo.estado.dar('sucata', -9)");

  // tempestade: dreno acelerado
  await jogo(page, "window.__vc.jogo.epi.forcarTempestade()");
  await page.waitForFunction(() => (window.__vc.epi as () => { tempestade: string })().tempestade === "aviso", null, { timeout: 60_000 });
  await page.screenshot({ path: "tests/screenshots/fase-3/04_aviso_tempestade.png" });
  await jogo(page, "window.__vc.jogo.epi['relogioTempestade'] = 0.01");
  await page.waitForFunction(() => (window.__vc.epi as () => { tempestade: string })().tempestade === "ativa", null, { timeout: 60_000 });
  const a = await epi(page);
  await esperarJogo(page, 2);
  const b = await epi(page);
  const drenoTempestade = (a.filtro - b.filtro) / 2;
  registrar("fase-3", { drenoFiltroTempestadePorSegundo: Number(drenoTempestade.toFixed(2)) });
  expect(drenoTempestade).toBeGreaterThan(1.8);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: "tests/screenshots/fase-3/05_tempestade.png" });

  // filtro zerado: dano contínuo e morte
  await jogo(page, "window.__vc.jogo.epi.filtro = 0; window.__vc.jogo.epi.saude = 25");
  await page.waitForFunction(() => (window.__vc.epi as () => { morto: boolean })().morto, null, { timeout: 120_000 });
  await page.waitForTimeout(3500);
  await page.screenshot({ path: "tests/screenshots/fase-3/06_morte.png" });
  await page.waitForFunction(() => (window.__vc.estado as () => { mundo: string })().mundo === "vila", null, { timeout: 120_000 });
  expect(await jogo(page, "window.__vc.jogo.estado.qtd('sucata')")).toBe(0); // perdeu o que coletou
  await page.waitForTimeout(2000);
  await page.screenshot({ path: "tests/screenshots/fase-3/07_acordou_na_vila.png" });

  // nova subida e volta pela escotilha com descontaminação
  await jogo(page, "window.__vc.jogo.transicionar('boca_do_poco', 'superficie')");
  await page.waitForFunction(() => (window.__vc.estado as () => { mundo: string })().mundo === "boca", null, { timeout: 90_000 });
  await teleportar(page, 35.5);
  await page.waitForTimeout(800);
  await apertarE(page);
  await page.waitForFunction(() => (window.__vc.estado as () => { mundo: string })().mundo === "superficie", null, { timeout: 90_000 });
  await teleportar(page, 4.5);
  await page.waitForTimeout(1200);
  await apertarE(page);
  await page.waitForFunction(() => (window.__vc.estado as () => { mundo: string })().mundo === "boca", null, { timeout: 90_000 });
  expect((await epi(page)).ativo).toBe(false);
  await page.screenshot({ path: "tests/screenshots/fase-3/08_volta_eclusa.png" });
  expect(await jogo(page, "window.__vc.jogo.estado.qtd('filtro_reposicao')")).toBe(0);
  // sem filtro de reposição a eclusa não abre
  await teleportar(page, 35.5);
  await page.waitForTimeout(800);
  await apertarE(page);
  await page.waitForTimeout(3000);
  expect((await est(page)).mundo).toBe("boca");
});
