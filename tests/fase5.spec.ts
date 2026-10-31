import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

const js = (p: Page, f: string) => p.evaluate(f);
const missao = async (p: Page, id: string) => (await js(p, `window.__vc.missoes()['${id}'] || {estado:'inativa',etapa:0}`)) as { estado: string; etapa: number };

/** Conduz um diálogo até o fim, escolhendo as opções pela ordem dada (trecho do texto). */
async function conduzir(p: Page, escolhas: string[] = []) {
  const fila = [...escolhas];
  for (let i = 0; i < 400; i++) {
    const s = await p.evaluate(() => {
      const j = window.__vc.jogo as { ui: { dialogo: { aberto: boolean } }; dialogo: { ativo: boolean }; roteiro: { emEpilogo: boolean } };
      return { aberto: j.ui.dialogo.aberto, ativo: j.dialogo.ativo, opcoes: document.querySelectorAll(".dialogo .opcoes li").length };
    });
    if (!s.aberto && !s.ativo) {
      if (i > 2) return;
      await p.waitForTimeout(150);
      continue;
    }
    if (s.opcoes > 0) {
      const t = fila.shift() ?? "Até mais";
      const ok = await js(p, `window.__vc.escolher(${JSON.stringify(t)})`);
      if (!ok) await js(p, `window.__vc.escolher('')`);
    } else {
      await js(p, "window.__vc.avancar()");
    }
    await p.waitForTimeout(30);
  }
}
async function falar(p: Page, id: string, escolhas: string[] = []) {
  await js(p, `window.__vc.falar('${id}')`);
  await conduzir(p, escolhas);
}

test("fase 5: campanha do primeiro dia ao desfecho, nos três finais", async ({ page }) => {
  test.setTimeout(2_400_000);
  await page.setViewportSize({ width: 640, height: 360 });
  await abrir(page, "area=praca&render=webgl2&novo=1");
  await page.waitForTimeout(1500);
  await conduzir(page); // introdução
  expect((await missao(page, "m1")).etapa).toBe(0);

  // M1: o primeiro dia
  await falar(page, "mirela", ["Vou levar"]);
  expect(await missao(page, "m1")).toEqual({ estado: "ativa", etapa: 1 });
  expect(await js(page, "window.__vc.jogo.estado.qtd('peca_ventilador')")).toBe(1);
  await page.screenshot({ path: "tests/screenshots/fase-5/01_dialogo_mirela.png" });
  await falar(page, "nita");
  expect((await missao(page, "m1")).etapa).toBe(2);
  await falar(page, "teodoro");
  expect((await missao(page, "m1")).etapa).toBe(3);
  await falar(page, "mirela");
  expect((await missao(page, "m1")).estado).toBe("concluida");
  expect((await missao(page, "m2")).estado).toBe("ativa");

  // tarefas opcionais
  await falar(page, "teodoro", ["A Capela precisa"]);
  await js(page, "window.__vc.jogo.estado.dar('vidro', 3)");
  await falar(page, "teodoro");
  expect((await missao(page, "t1")).estado).toBe("concluida");
  await falar(page, "nita", ["Tem trabalho"]);
  await js(page, "window.__vc.jogo.estado.dar('componente', 3)");
  await falar(page, "nita");
  expect((await missao(page, "t2")).estado).toBe("concluida");

  // M2: a primeira subida (a subida em si é coberta pelo teste da fase 3)
  await falar(page, "ondina");
  expect((await missao(page, "m2")).etapa).toBe(1);
  await js(page, "window.__vc.jogo.estado.dar('sucata', 5); window.__vc.jogo.estado.avisar('voltou')");
  expect((await missao(page, "m2")).etapa).toBe(2);
  await falar(page, "bento");
  await page.waitForFunction(() => (window.__vc.jogo as { paineis: { aberto: string | null } }).paineis.aberto === "loja", null, { timeout: 30_000 });
  await page.screenshot({ path: "tests/screenshots/fase-5/02_loja_bento.png" });
  await js(page, "window.__vc.jogo.paineis.executar('venderTudo', 'sucata')");
  await js(page, "window.__vc.jogo.paineis.fechar()");
  expect((await missao(page, "m2")).estado).toBe("concluida");
  expect((await missao(page, "m3")).estado).toBe("ativa");

  // M3: a escolha
  await falar(page, "teodoro", ["Eu trago"]);
  expect((await missao(page, "m3")).etapa).toBe(1);
  await falar(page, "mirela");
  expect(await js(page, "window.__vc.jogo.estado.flag('m3_mirela_avisou')")).toBe(true);
  await js(page, "window.__vc.jogo.estado.mudarCotas(60)");
  await js(page, "window.__vc.jogo.paineis.abrirLoja('samira'); window.__vc.jogo.paineis.executar('upgrade', 'filtro2')");
  await page.screenshot({ path: "tests/screenshots/fase-5/03_loja_caravana.png" });
  await js(page, "window.__vc.jogo.paineis.fechar()");
  expect(await js(page, "window.__vc.jogo.estado.capacidadeFiltro()")).toBe(150);
  await js(page, "window.__vc.jogo.estado.avisar('interativo:amostra_marco')");
  expect((await missao(page, "m3")).etapa).toBe(2);
  const antesDaEscolha = await js(page, "window.__vc.dados()");
  await falar(page, "teodoro", ["Entregar a amostra"]);
  expect((await missao(page, "m3")).estado).toBe("concluida");
  expect(await js(page, "window.__vc.jogo.estado.flag('m3_ajudou_vigilia')")).toBe(true);
  const precos = await js(page, "({bento: window.__vc.jogo.paineis.precoFiltro('bento'), nita: window.__vc.jogo.paineis.precoFiltro('nita')})") as { bento: number; nita: number };
  registrar("fase-5", { precoFiltroAposAjudarVigilia: precos });
  expect(precos.bento).toBeGreaterThan(3);
  expect(precos.nita).toBeLessThan(3);

  // M4: o registro de Darci
  expect((await missao(page, "m4")).estado).toBe("ativa");
  await js(page, "window.__vc.jogo.paineis.abrirLoja('samira'); window.__vc.jogo.paineis.executar('upgrade', 'filtro3'); window.__vc.jogo.paineis.fechar()");
  expect(await js(page, "window.__vc.jogo.estado.capacidadeFiltro()")).toBe(240);
  await js(page, "void window.__vc.jogo.roteiro.achado()");
  await conduzir(page);
  expect(await missao(page, "m4")).toEqual({ estado: "ativa", etapa: 1 });
  expect(await js(page, "window.__vc.jogo.estado.qtd('gravador_darci')")).toBe(1);

  // save automático no IndexedDB
  await js(page, "window.__vc.jogo.salvar()");
  const salvo = await page.evaluate(() => new Promise((ok) => {
    const r = indexedDB.open("vila_cisterna", 1);
    r.onsuccess = () => { const g = r.result.transaction("saves").objectStore("saves").get("slot1"); g.onsuccess = () => ok(g.result?.missoes?.m4?.etapa); };
  }));
  expect(salvo).toBe(1);
  const antesDoFinal = await js(page, "window.__vc.dados()");

  const finais: Record<string, unknown> = {};
  for (const [qual, acao] of [["vigilia", "teodoro"], ["conselho", "mirela"], ["guardou", "muro"]] as const) {
    await page.evaluate((d) => { (window.__vc.jogo as { estado: { carregar(x: unknown): void } }).estado.carregar(d); }, antesDoFinal);
    await page.evaluate(() => { const j = window.__vc.jogo as { roteiro: { emEpilogo: boolean }; subida: { emSequencia: boolean }; camera: { distanciaExtra: number; alturaExtra: number } }; j.roteiro.emEpilogo = false; j.subida.emSequencia = false; j.camera.distanciaExtra = 0; j.camera.alturaExtra = 0; });
    {
      await page.evaluate(() => document.querySelectorAll(".tela-fim").forEach((e) => e.remove()));
    }
    await js(page, "window.__vc.jogo.transicionar('praca', 'inicio')");
    await page.waitForTimeout(1500);
    if (acao === "muro") {
      await js(page, "window.__vc.jogo.usarInterativo('muro', 'muro')");
      await conduzir(page, ["Guardar"]);
    } else {
      await falar(page, acao, ["Entregar a máscara"]);
    }
    for (let k = 0; k < 200 && !(await page.evaluate(() => !!document.querySelector(".tela-fim.visivel"))); k++) {
      await conduzir(page);
      await page.waitForTimeout(500);
    }
    await page.waitForFunction(() => document.querySelector(".tela-fim.visivel"), null, { timeout: 180_000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `tests/screenshots/fase-5/final_${qual}.png` });
    finais[qual] = { desfecho: await js(page, "window.__vc.jogo.estado.flag('desfecho')"), mundo: await js(page, "window.__vc.estado().mundo"),
      mascaraNoInventario: await js(page, "window.__vc.jogo.estado.qtd('mascara_darci')") };
    expect(await js(page, "window.__vc.jogo.estado.flag('desfecho')")).toBe(qual);
    expect(await js(page, "window.__vc.estado().mundo")).toBe("superficie");
  }
  registrar("fase-5", { finais });
  void antesDaEscolha;
});
