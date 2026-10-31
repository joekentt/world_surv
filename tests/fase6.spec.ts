import { test } from "@playwright/test";
import { abrir, registrar } from "./util";

const AREAS: [string, string, number, number][] = [
  ["praca", "praca", 2, 0], ["galerias", "galerias", 98, 0], ["capela", "capela", -134, 0],
  ["duto_norte", "duto_tunel", 30, 0], ["boca_do_poco", "boca_do_poco", 20, 0], ["superficie_marco", "superficie", 246, 0],
];

for (const render of ["webgpu", "webgl2"] as const) {
  test(`fase 6: uma imagem por área (${render})`, async ({ page }) => {
    test.setTimeout(900_000);
    const ativos: Record<string, string> = {};
    for (const [area, nome, x, y] of AREAS) {
      await abrir(page, `area=${area}&render=${render}`);
      await page.evaluate(([x, y]) => (window.__vc.teleportar as (x: number, y: number) => void)(x, y), [x, y]);
      await page.waitForTimeout(area.startsWith("superficie") ? 9000 : 14000);
      ativos[nome] = await page.evaluate(() => window.__vc.renderizador);
      await page.screenshot({ path: `tests/screenshots/fase-6/${render}_${nome}.png` });
    }
    registrar("fase-6", { [`renderizador_${render}`]: ativos });
  });
}
