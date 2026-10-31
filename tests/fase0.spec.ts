import { expect, test } from "@playwright/test";
import { abrir, medirFps, registrar } from "./util";

for (const render of ["webgpu", "webgl2"] as const) {
  test(`fase 0: cena de validação em ${render}`, async ({ page }) => {
    await abrir(page, `cena=teste&render=${render}`);
    const ativo = await page.evaluate(() => window.__vc.renderizador);
    if (render === "webgl2") expect(ativo).toBe("webgl2");
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `tests/screenshots/fase-0/cena_teste_${ativo}.png` });
    const fps = await medirFps(page, 10);
    registrar("fase-0", { [`fps_${render}_pedido_${ativo}_ativo`]: Number(fps.toFixed(1)) });
    console.log(`renderizador pedido ${render}, ativo ${ativo}: ${fps.toFixed(1)} fps`);
    expect(fps).toBeGreaterThan(1);
  });
}
