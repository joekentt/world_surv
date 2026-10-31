import { expect, type Page } from "@playwright/test";
import * as fs from "node:fs";

export async function abrir(page: Page, query: string): Promise<void> {
  const erros: string[] = [];
  page.on("pageerror", (e) => erros.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
  await page.goto("/?" + query);
  await page.waitForFunction(() => window.__vc?.pronto || window.__vc?.erro, null, { timeout: 120_000 });
  const erro = await page.evaluate(() => window.__vc.erro);
  expect(erro, `erro ao iniciar: ${erro}\n${erros.join("\n")}`).toBeFalsy();
}

/** Mede o fps médio contando quadros com requestAnimationFrame durante `segundos`. */
export async function medirFps(page: Page, segundos = 10): Promise<number> {
  return page.evaluate((s) => new Promise<number>((ok) => {
    let quadros = 0;
    const t0 = performance.now();
    const passo = () => {
      quadros++;
      if (performance.now() - t0 < s * 1000) requestAnimationFrame(passo);
      else ok(quadros / ((performance.now() - t0) / 1000));
    };
    requestAnimationFrame(passo);
  }), segundos);
}

export function registrar(fase: string, dados: Record<string, unknown>): void {
  const dir = `tests/screenshots/${fase}`;
  fs.mkdirSync(dir, { recursive: true });
  const arq = `${dir}/medicoes.json`;
  const atual = fs.existsSync(arq) ? JSON.parse(fs.readFileSync(arq, "utf8")) : {};
  Object.assign(atual, dados);
  fs.writeFileSync(arq, JSON.stringify(atual, null, 2));
}
