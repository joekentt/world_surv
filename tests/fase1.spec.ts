import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

type Estado = { x: number; y: number; estado: string; agachado: boolean; vx: number };
const estado = (p: Page) => p.evaluate(() => (window.__vc.estado as () => Estado)());
const tecla = (p: Page, c: string, v: boolean) => p.evaluate(([c, v]) => (window.__vc.tecla as (c: string, v: boolean) => void)(c as string, v as boolean), [c, v] as const);

/** Segura uma tecla por ms de tempo de jogo (o jogo roda devagar no SwiftShader, então usamos o relógio do jogo). */
async function segurar(p: Page, teclas: string[], segundosJogo: number) {
  const t0 = await p.evaluate(() => (window.__vc.jogo as { tempo: number }).tempo);
  for (const t of teclas) await tecla(p, t, true);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + segundosJogo, { timeout: 120_000 });
  const durante = await estado(p);
  for (const t of teclas) await tecla(p, t, false);
  return durante;
}

test("fase 1: andar, correr, pular, agachar, escada e corda no teclado", async ({ page }) => {
  test.setTimeout(600_000);
  await abrir(page, "area=sala_teste&render=webgl2");
  const e0 = await estado(page);
  expect(e0.estado).toBe("chao");
  await page.screenshot({ path: "tests/screenshots/fase-1/01_inicio.png" });

  const e1 = await segurar(page, ["KeyD"], 1.0);
  expect(e1.x - e0.x).toBeGreaterThan(2.0); // ~3,2 m/s

  const correndo = await segurar(page, ["KeyD", "ShiftLeft"], 0.6);
  registrar("fase-1", { velocidadeAndando: Number(e1.vx.toFixed(2)), velocidadeCorrendo: Number(correndo.vx.toFixed(2)) });
  expect(correndo.vx).toBeGreaterThan(5.5); // corrida mais rápida que a caminhada

  // pulo: mede altura máxima
  const yChao = (await estado(page)).y;
  await tecla(page, "Space", true);
  await page.waitForFunction(() => (window.__vc.estado as () => { estado: string })().estado === "ar", null, { timeout: 30_000 });
  let ymax = yChao;
  for (let i = 0; i < 400; i++) {
    const s = await estado(page);
    ymax = Math.max(ymax, s.y);
    if (s.estado === "chao") break;
    await page.waitForTimeout(20);
  }
  await tecla(page, "Space", false);
  registrar("fase-1", { alturaPulo: Number((ymax - yChao).toFixed(2)) });
  expect(ymax - yChao).toBeGreaterThan(1.0);
  await page.screenshot({ path: "tests/screenshots/fase-1/02_pulo.png" });

  // escada em x = 10
  await page.evaluate(() => (window.__vc.jogo as { jogador: { teleportar(x: number, y: number): void } }).jogador.teleportar(10, 0));
  await segurar(page, ["KeyW"], 2.4);
  const e3 = await estado(page);
  await page.screenshot({ path: "tests/screenshots/fase-1/03_escada.png" });
  expect(e3.y).toBeGreaterThan(3.9);

  // túnel baixo: em pé não passa, agachado passa
  await page.evaluate(() => (window.__vc.jogo as { jogador: { teleportar(x: number, y: number): void } }).jogador.teleportar(17, 0));
  await segurar(page, ["KeyD"], 1.5);
  const bloqueado = await estado(page);
  expect(bloqueado.x).toBeLessThan(19.6);
  await segurar(page, ["KeyD", "KeyC"], 4.0);
  const passou = await estado(page);
  await page.screenshot({ path: "tests/screenshots/fase-1/04_agachado.png" });
  expect(passou.x).toBeGreaterThan(24.5);

  // corda em x = 40
  await page.evaluate(() => (window.__vc.jogo as { jogador: { teleportar(x: number, y: number): void } }).jogador.teleportar(40, 0));
  await segurar(page, ["KeyW"], 3.0);
  expect((await estado(page)).y).toBeGreaterThan(5.4);
  await page.screenshot({ path: "tests/screenshots/fase-1/05_corda.png" });
});

test("fase 1: gamepad (mapeamento standard simulado)", async ({ page }) => {
  await page.addInitScript(() => {
    const botoes = Array.from({ length: 17 }, () => ({ pressed: false, touched: false, value: 0 }));
    const pad = { id: "simulado", index: 0, connected: true, mapping: "standard", axes: [0, 0, 0, 0], buttons: botoes, timestamp: 0 };
    (window as unknown as { __pad: typeof pad }).__pad = pad;
    navigator.getGamepads = () => [pad as unknown as Gamepad];
  });
  await abrir(page, "area=sala_teste&render=webgl2");
  const t0 = await estado(page);
  await page.evaluate(() => { (window as unknown as { __pad: { axes: number[] } }).__pad.axes[0] = 1; });
  await page.waitForFunction(() => (window.__vc.estado as () => { vx: number })().vx > 2.5, null, { timeout: 60_000 });
  await page.evaluate(() => { const p = (window as unknown as { __pad: { buttons: { pressed: boolean; value: number }[] } }).__pad; p.buttons[0].pressed = true; p.buttons[0].value = 1; });
  await page.waitForFunction(() => (window.__vc.estado as () => { estado: string })().estado === "ar", null, { timeout: 60_000 });
  await page.evaluate(() => { const p = (window as unknown as { __pad: { axes: number[]; buttons: { pressed: boolean; value: number }[] } }).__pad; p.buttons[0].pressed = false; p.buttons[0].value = 0; p.axes[0] = 0; });
  const t1 = await estado(page);
  expect(t1.x).toBeGreaterThan(t0.x);
  await page.screenshot({ path: "tests/screenshots/fase-1/06_gamepad.png" });
});
