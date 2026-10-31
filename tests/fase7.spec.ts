import { expect, test } from "@playwright/test";
import { medirFps, registrar } from "./util";

for (const render of ["webgpu", "webgl2"] as const) {
  test(`fase 7: build de produção, título e novo jogo (${render})`, async ({ page }) => {
    test.setTimeout(600_000);
    const erros: string[] = [];
    page.on("pageerror", (e) => erros.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
    const externas: string[] = [];
    page.on("request", (r) => { const u = new URL(r.url()); if (u.protocol.startsWith("http") && u.hostname !== "localhost") externas.push(r.url()); });
    await page.goto(`/?render=${render}`);
    await page.waitForSelector(".titulo button", { timeout: 180_000 });
    await page.screenshot({ path: `tests/screenshots/fase-7/${render}_01_titulo.png` });
    await page.click(".titulo button[data-v='novo']");
    // introdução: avança até fechar
    for (let i = 0; i < 40; i++) {
      const aberto = await page.evaluate(() => (window.__vc.jogo as { ui?: { dialogo: { aberto: boolean } } })?.ui?.dialogo.aberto);
      if (!aberto && i > 3) break;
      await page.evaluate(() => (window.__vc.avancar as (() => void) | undefined)?.());
      await page.waitForTimeout(300);
    }
    await page.waitForFunction(() => (window.__vc.missoes as () => Record<string, { estado: string }>)().m1?.estado === "ativa", null, { timeout: 60_000 });
    await page.waitForTimeout(12_000);
    await page.screenshot({ path: `tests/screenshots/fase-7/${render}_02_inicio.png` });
    const ativo = await page.evaluate(() => window.__vc.renderizador);
    const fps = await medirFps(page, 10);
    registrar("fase-7", { [`build_${render}`]: { ativo, fps: Number(fps.toFixed(1)), requisicoesExternas: externas.length } });
    expect(externas, externas.join("\n")).toEqual([]);
    expect(erros.filter((e) => !e.includes("WebGPU") && !e.includes("AudioContext")), erros.join("\n")).toEqual([]);
  });
}
