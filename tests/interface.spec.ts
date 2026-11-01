import { expect, test } from "@playwright/test";
import { abrir } from "./util";

test("introdução: a caixa de diálogo fica visível acima da cortina preta", async ({ page }) => {
  test.setTimeout(300_000);
  await page.setViewportSize({ width: 960, height: 540 });
  await abrir(page, "area=praca&render=webgl2&novo=1");
  await page.waitForFunction(() => (window.__vc.jogo as { ui: { dialogo: { aberto: boolean } } }).ui.dialogo.aberto, null, { timeout: 120_000 });
  await page.waitForTimeout(1200);
  const visivel = await page.evaluate(() => {
    const caixa = document.querySelector(".dialogo")!.getBoundingClientRect();
    const alvo = document.elementFromPoint(caixa.left + caixa.width / 2, caixa.top + caixa.height / 2);
    return !!alvo?.closest(".dialogo");
  });
  await page.screenshot({ path: "tests/screenshots/fase-7/introducao_visivel.png" });
  expect(visivel).toBe(true);
  // avançar pelo teclado, como o jogador faria
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Space");
    await page.waitForTimeout(700);
  }
  await page.waitForFunction(() => (window.__vc.missoes as () => Record<string, { estado: string }>)().m1?.estado === "ativa", null, { timeout: 60_000 });
  await page.waitForFunction(() => !(window.__vc.jogo as { ui: { dialogo: { aberto: boolean } } }).ui.dialogo.aberto, null, { timeout: 120_000 });
});
