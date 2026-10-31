import { expect, test, type Page } from "@playwright/test";
import { abrir, medirFps, registrar } from "./util";

const avaliar = (p: Page, f: string) => p.evaluate(f);
const teleportar = (p: Page, x: number, y = 0) => p.evaluate(([x, y]) => (window.__vc.teleportar as (x: number, y: number) => void)(x, y), [x, y]);

test("fase 4: vila viva com 20 NPCs, turnos de luz, conversas e reação", async ({ page }) => {
  test.setTimeout(600_000);
  await abrir(page, "area=praca&render=webgl2");
  const c0 = await avaliar(page, "window.__vc.npcs()") as { simulados: number };
  expect(c0.simulados).toBe(20);
  // percorre a vila para instanciar todos os moradores
  for (const x of [-120, -60, 0, 60, 110, -20]) {
    await teleportar(page, x);
    await page.waitForTimeout(6000);
  }
  await page.waitForFunction(() => (window.__vc.npcs as () => { modelos: number })().modelos >= 19, null, { timeout: 180_000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "tests/screenshots/fase-4/01_praca_primeiro_turno.png" });
  const fps = await medirFps(page, 10);
  const cont = await avaliar(page, "window.__vc.npcs()") as { visiveis: number; modelos: number };
  registrar("fase-4", { fpsPracaComNpcs_webgl2_swiftshader: Number(fps.toFixed(1)), modelosCarregados: cont.modelos, visiveisNaPraca: cont.visiveis });

  // posições antes e depois da troca de turno
  const antes = await avaliar(page, "window.__vc.jogo.npcs.npcs.map(n => [n.def.id, n.x, n.z])") as [string, number, number][];
  await avaliar(page, "window.__vc.jogo.npcs.pularTurno()");
  await page.waitForTimeout(500);
  const andando = await avaliar(page, "window.__vc.jogo.npcs.npcs.filter(n => n.andando).length") as number;
  expect(andando).toBeGreaterThan(5);
  await avaliar(page, "window.__vc.jogo.turnos.acelerar = 1");
  await page.waitForTimeout(15000);
  const depois = await avaliar(page, "window.__vc.jogo.npcs.npcs.map(n => [n.def.id, n.x, n.z])") as [string, number, number][];
  const moveram = antes.filter(([id, x, z], i) => Math.hypot(depois[i][1] - x, depois[i][2] - z) > 0.5 && id === depois[i][0]).length;
  expect(moveram).toBeGreaterThan(4);
  await page.screenshot({ path: "tests/screenshots/fase-4/02_segundo_turno_andando.png" });

  // descanso: lâmpadas baixam
  await avaliar(page, "window.__vc.jogo.npcs.pularTurno(); window.__vc.jogo.npcs.pularTurno()");
  expect(await avaliar(page, "window.__vc.turno()")).toBe("descanso");
  await page.waitForFunction(() => (window.__vc.jogo as { turnos: { fatorLuz: number } }).turnos.fatorLuz < 0.5, null, { timeout: 120_000 });
  await page.screenshot({ path: "tests/screenshots/fase-4/03_descanso_luz_baixa.png" });
  await avaliar(page, "window.__vc.jogo.npcs.pularTurno()");

  // conversa de fundo: dois NPCs parados perto do jogador
  await page.evaluate(() => {
    const j = window.__vc.jogo as { npcs: { npcs: { def: { id: string }; x: number; z: number; caminho: unknown[]; emCasa: boolean; ocupadoAte: number }[]; ["relogioConversa"]: number } };
    const [a, b] = j.npcs.npcs.filter((n) => ["varredor", "idoso_banco"].includes(n.def.id));
    for (const [n, x] of [[a, -31], [b, -29]] as const) { n.x = x; n.z = 1.6; n.caminho = []; n.emCasa = false; n.ocupadoAte = 0; }
    j.npcs["relogioConversa"] = 0;
  });
  await teleportar(page, -30);
  await page.waitForFunction(() => document.querySelectorAll(".balao").length > 0, null, { timeout: 120_000 });
  await page.screenshot({ path: "tests/screenshots/fase-4/04_conversa_de_fundo.png" });
  const fala = await page.evaluate(() => document.querySelector(".balao")?.textContent);
  registrar("fase-4", { exemploConversa: fala });
});
