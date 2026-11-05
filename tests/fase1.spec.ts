import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

/**
 * Fase 1 (revisão 2): câmera e movimento em terceira pessoa.
 * Os seis critérios da seção 3.4 e os parâmetros de movimento da seção 3.3.
 * Tempos são medidos no relógio do jogo (o SwiftShader roda a poucos fps).
 */

type Reg = { quadro: number; t: number; yawCamera: number; yaw: number; vel: number; x: number; z: number; recentralizando: boolean };
type Estado = { x: number; y: number; z: number; estado: string; vx: number; vz: number; yaw: number; yawCamera: number; pitch: number };
const GRAU = Math.PI / 180;

const js = <T = unknown>(p: Page, f: string) => p.evaluate(f) as Promise<T>;
const estado = (p: Page) => js<Estado>(p, "window.__vc.estado()");
const tempo = (p: Page) => js<number>(p, "window.__vc.jogo.tempo");
const tecla = (p: Page, c: string, v: boolean) => p.evaluate(([c, v]) => (window.__vc.tecla as (c: string, v: boolean) => void)(c as string, v as boolean), [c, v] as const);
const dif = (a: number, b: number) => { let d = a - b; while (d > Math.PI) d -= 2 * Math.PI; while (d <= -Math.PI) d += 2 * Math.PI; return d; };

async function esperarJogo(p: Page, s: number) {
  const t0 = await tempo(p);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + s, { timeout: 240_000 });
}
async function registro(p: Page, desde: number): Promise<Reg[]> {
  return p.evaluate((t) => (window.__vc.registro as Reg[]).filter((r) => r.t >= t), desde);
}
async function preparar(p: Page) {
  await p.setViewportSize({ width: 640, height: 360 });
  await abrir(p, "area=sala_teste&render=webgl2&qualidade=alta");
  await js(p, "window.__vc.gravar = true");
  await esperarJogo(p, 0.5);
}
async function girarCamera(p: Page, yaw: number) {
  await p.evaluate((y) => (window.__vc.definirCamera as (y: number) => void)(y), yaw);
}
async function posicionar(p: Page, x: number, y: number, z: number, yawPersonagem: number, yawCamera: number, pitch?: number) {
  await p.evaluate(([x, y, z, yp, yc, pt]) => {
    (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, yp);
    (window.__vc.definirCamera as (y: number, p?: number) => void)(yc, pt ?? undefined);
  }, [x, y, z, yawPersonagem, yawCamera, pitch ?? null] as const);
  await esperarJogo(p, 0.3);
}

test.describe("fase 1: critérios da seção 3.4", () => {
  test.setTimeout(900_000);

  test("1. personagem a 90° da câmera andando: a câmera vai para as costas", async ({ page }) => {
    await preparar(page);
    const resultados: Record<string, number> = {};
    // 1a: literal (W relativo à câmera)
    await posicionar(page, 0, 0, -20, 90 * GRAU, 0);
    let t0 = await tempo(page);
    await tecla(page, "KeyW", true);
    await esperarJogo(page, 3);
    await tecla(page, "KeyW", false);
    let regs = await registro(page, t0);
    let ok = regs.find((r) => r.t - t0 <= 2.8 && Math.abs(dif(r.yawCamera, r.yaw)) < 10 * GRAU);
    resultados.literal_s = ok ? Number((ok.t - t0).toFixed(2)) : -1;
    expect(ok, "diferença câmera/costas abaixo de 10° em até 2,8 s").toBeTruthy();
    // 1b: direção fixa no mundo a 90° da câmera, para exercitar a recentralização
    await posicionar(page, 0, 0, -20, 90 * GRAU, 0);
    t0 = await tempo(page);
    await js(page, "window.__vc.direcaoForcada(1, 0)");
    await esperarJogo(page, 3);
    await js(page, "window.__vc.direcaoForcada(null)");
    regs = await registro(page, t0);
    const antesDoAtraso = regs.filter((r) => r.t - t0 < 0.75);
    expect(antesDoAtraso.every((r) => Math.abs(r.yawCamera) < 1 * GRAU), "câmera parada antes de 0,8 s").toBeTruthy();
    ok = regs.find((r) => r.t - t0 <= 2.8 && Math.abs(dif(r.yawCamera, r.yaw)) < 10 * GRAU);
    resultados.direcaoFixa_s = ok ? Number((ok.t - t0).toFixed(2)) : -1;
    registrar("fase-1", { criterio1_segundosAte10graus: resultados });
    expect(ok, "recentralização abaixo de 10° em até 0,8 + 2 s").toBeTruthy();
  });

  test("2. mouse girando enquanto anda: sem recentralizar durante o giro e nos 0,8 s seguintes", async ({ page }) => {
    await preparar(page);
    await posicionar(page, 0, 0, -20, 90 * GRAU, 90 * GRAU);
    await js(page, "window.__vc.direcaoForcada(0, 1)");
    await esperarJogo(page, 1.2);
    const t0 = await tempo(page);
    const yaw0 = (await estado(page)).yawCamera;
    // gira o mouse por 2 s de jogo, guardando o horário de jogo de cada movimento
    const tempos: number[] = [];
    while ((await tempo(page)) < t0 + 2) {
      tempos.push(await js<number>(page, "(window.__vc.mouse(6, 0), window.__vc.jogo.tempo)"));
      await page.waitForTimeout(25);
    }
    await esperarJogo(page, 0.9);
    const regs = await registro(page, t0);
    await js(page, "window.__vc.direcaoForcada(null)");
    // quadros processados depois do primeiro movimento e até 0,8 s depois do último
    const durante = regs.filter((r) => r.t > tempos[0] && r.t < tempos[tempos.length - 1] + 0.8);
    const yaw1 = (await estado(page)).yawCamera;
    registrar("fase-1", { criterio2_giroDoMouseGraus: Number(((yaw1 - yaw0) / GRAU).toFixed(1)) });
    expect(Math.abs(yaw1 - yaw0)).toBeGreaterThan(20 * GRAU);
    expect(durante.some((r) => r.recentralizando), "recentralizou durante ou logo após o giro").toBeFalsy();
  });

  test("3. parado e sem mouse por 5 s: o ângulo da câmera não muda", async ({ page }) => {
    await preparar(page);
    await posicionar(page, 0, 0, -20, 40 * GRAU, 10 * GRAU);
    const t0 = await tempo(page);
    await esperarJogo(page, 5);
    const regs = await registro(page, t0);
    const variacao = Math.max(...regs.map((r) => Math.abs(dif(r.yawCamera, regs[0].yawCamera))));
    registrar("fase-1", { criterio3_variacaoGraus: Number((variacao / GRAU).toFixed(4)) });
    expect(variacao).toBeLessThan(0.01 * GRAU);
  });

  test("4. andando em direção à câmera por 1 s: a câmera gira no máximo 15°", async ({ page }) => {
    await preparar(page);
    await posicionar(page, 0, 0, 0, 0, 0);
    const t0 = await tempo(page);
    await js(page, "window.__vc.direcaoForcada(0, -1)");
    await esperarJogo(page, 1.0);
    await js(page, "window.__vc.direcaoForcada(null)");
    const regs = await registro(page, t0);
    const giro = Math.max(...regs.filter((r) => r.t <= t0 + 1.0).map((r) => Math.abs(dif(r.yawCamera, 0))));
    registrar("fase-1", { criterio4_giroGraus: Number((giro / GRAU).toFixed(2)) });
    expect(giro).toBeLessThan(15 * GRAU);
  });

  test("5. túnel de 2,5 m: câmera girada 360° em várias alturas nunca entra na geometria", async ({ page }) => {
    await preparar(page);
    await posicionar(page, -15, 0, 10, 0, 0);
    await esperarJogo(page, 1.0);
    const falhas: string[] = [];
    let amostras = 0;
    for (const pitch of [-25, 0, 25, 55]) {
      for (let yaw = 0; yaw < 360; yaw += 30) {
        await js(page, `window.__vc.definirCamera(${yaw * GRAU}, ${pitch * GRAU})`);
        await esperarJogo(page, 0.12);
        const r = await js<{ acertou: boolean; camera: number[] }>(page, "window.__vc.raycastCamera()");
        const [cx, cy] = r.camera;
        const dentroDoCorredor = Math.abs(cx - -15) < 1.25 + 1e-3 && cy > 0 && cy < 3;
        amostras++;
        if (r.acertou || !dentroDoCorredor) falhas.push(`yaw ${yaw} pitch ${pitch}: ${r.acertou ? "atrás de parede" : "fora do corredor"} ${r.camera.map((v) => v.toFixed(2))}`);
      }
    }
    await page.screenshot({ path: "tests/screenshots/fase-1/05_corredor.png" });
    registrar("fase-1", { criterio5_amostras: amostras, criterio5_falhas: falhas.length });
    expect(falhas, falhas.join("\n")).toEqual([]);
  });

  test("6. o movimento começa no quadro seguinte ao da tecla", async ({ page }) => {
    await preparar(page);
    await posicionar(page, 0, 0, -20, 0, 0);
    await esperarJogo(page, 0.5);
    const quadro = await js<number>(page, "window.__vc.quadroAtual()");
    await tecla(page, "KeyW", true);
    await page.waitForFunction((q) => (window.__vc.quadroAtual as () => number)() >= q + 2, quadro, { timeout: 60_000 });
    await tecla(page, "KeyW", false);
    const regs = await page.evaluate((q) => (window.__vc.registro as Reg[]).filter((r) => r.quadro > q).slice(0, 2), quadro);
    registrar("fase-1", { criterio6_velocidadeNoQuadroSeguinte: Number(regs[0].vel.toFixed(3)) });
    expect(regs[0].vel).toBeGreaterThan(0);
  });
});

test.describe("fase 1: movimento (seção 3.3)", () => {
  test.setTimeout(900_000);

  test("velocidades, pulo, degraus, rampas, escada de mão, corda e túnel baixo", async ({ page }) => {
    await preparar(page);
    const m: Record<string, unknown> = {};
    // andar e correr
    await posicionar(page, 0, 0, -30, 0, 0);
    await tecla(page, "KeyW", true);
    await esperarJogo(page, 1.0);
    m.andar = Number(Math.hypot((await estado(page)).vx, (await estado(page)).vz).toFixed(2));
    await tecla(page, "ShiftLeft", true);
    await esperarJogo(page, 0.6);
    const e = await estado(page);
    m.correr = Number(Math.hypot(e.vx, e.vz).toFixed(2));
    await tecla(page, "ShiftLeft", false);
    await tecla(page, "KeyW", false);
    // tempo até parar
    const t0 = await tempo(page);
    await esperarJogo(page, 0.4);
    const regs = await registro(page, t0);
    const parou = regs.find((r) => r.vel < 0.05);
    m.tempoAteParar = parou ? Number((parou.t - t0).toFixed(3)) : -1;
    expect(m.andar).toBeGreaterThan(2.0);
    expect(m.correr).toBeGreaterThan(6.7);
    expect(Number(m.tempoAteParar)).toBeLessThan(0.25);
    await page.screenshot({ path: "tests/screenshots/fase-1/01_area_aberta.png" });

    // pulo: altura máxima
    await posicionar(page, 0, 0, -25, 0, 0);
    const y0 = (await estado(page)).y;
    await tecla(page, "Space", true);
    let ymax = y0;
    const tp = await tempo(page);
    while ((await tempo(page)) < tp + 1.2) { ymax = Math.max(ymax, (await estado(page)).y); await page.waitForTimeout(10); }
    await tecla(page, "Space", false);
    m.alturaPulo = Number((ymax - y0).toFixed(2));
    expect(ymax - y0).toBeGreaterThan(0.95);
    expect(ymax - y0).toBeLessThan(1.3);

    // degraus: 0,30 m passa, 0,40 m não (andando para +Z a partir de z = 2)
    async function andarAte(x: number, z0: number, segundos: number) {
      await posicionar(page, x, 0, z0, 0, 0);
      await tecla(page, "KeyW", true);
      await esperarJogo(page, segundos);
      await tecla(page, "KeyW", false);
      return estado(page);
    }
    m.degrau030 = Number((await andarAte(-5, 2, 1.6)).y.toFixed(2));
    m.degrau040 = Number((await andarAte(-8, 2, 1.6)).y.toFixed(2));
    expect(Number(m.degrau030)).toBeGreaterThan(0.25);
    expect(Number(m.degrau040)).toBeLessThan(0.1);

    // rampas: 30° e 40° sobem até 2 m; 50° não
    m.rampa30 = Number((await andarAte(20, 0, 3.5)).y.toFixed(2));
    m.rampa40 = Number((await andarAte(24, 0, 3.5)).y.toFixed(2));
    m.rampa50 = Number((await andarAte(28, 0, 3.5)).y.toFixed(2));
    await page.screenshot({ path: "tests/screenshots/fase-1/02_rampas.png" });
    expect(Number(m.rampa30)).toBeGreaterThan(1.8);
    expect(Number(m.rampa40)).toBeGreaterThan(1.8);
    expect(Number(m.rampa50)).toBeLessThan(1.0);

    // escadaria até a plataforma de 2 m
    m.escadaria = Number((await andarAte(10, 0, 3.0)).y.toFixed(2));
    expect(Number(m.escadaria)).toBeGreaterThan(1.9);

    // escada de mão: encaixe com E e subida com W
    await posicionar(page, -5, 0, 15.2, 0, 0);
    await tecla(page, "KeyE", true); await esperarJogo(page, 0.1); await tecla(page, "KeyE", false);
    await page.waitForFunction(() => (window.__vc.estado as () => { estado: string })().estado === "escada", null, { timeout: 30_000 });
    await page.screenshot({ path: "tests/screenshots/fase-1/03_escada_de_mao.png" });
    // câmera virada para a escada (de frente para o personagem): ao sair no topo com W ainda pressionado,
    // o personagem segue para cima do bloco e não volta para a beirada
    await girarCamera(page, Math.PI);
    await tecla(page, "KeyW", true);
    await page.waitForFunction(() => { const e = (window.__vc.estado as () => { estado: string; y: number })(); return e.estado === "chao" && e.y > 4.5; }, null, { timeout: 120_000 });
    await esperarJogo(page, 0.4);
    await tecla(page, "KeyW", false);
    await esperarJogo(page, 1.0);
    const topo = await estado(page);
    m.escadaDeMao = Number(topo.y.toFixed(2));
    m.saidaEscadaZ = Number(topo.z.toFixed(2));
    expect(Number(m.escadaDeMao)).toBeGreaterThan(4.9);
    expect(topo.z).toBeGreaterThan(16.4);

    // corda
    await posicionar(page, 5, 0, 16.9, 0, 0);
    await tecla(page, "KeyE", true); await esperarJogo(page, 0.1); await tecla(page, "KeyE", false);
    await page.waitForFunction(() => (window.__vc.estado as () => { estado: string })().estado === "escada", null, { timeout: 30_000 });
    await tecla(page, "KeyW", true); await esperarJogo(page, 2.0);
    await page.screenshot({ path: "tests/screenshots/fase-1/04_corda.png" });
    await page.waitForFunction(() => { const e = (window.__vc.estado as () => { estado: string; y: number })(); return e.estado === "chao" && e.y > 5.5; }, null, { timeout: 120_000 });
    await tecla(page, "KeyW", false);
    m.corda = Number((await estado(page)).y.toFixed(2));
    expect(Number(m.corda)).toBeGreaterThan(5.9);

    // túnel baixo: em pé barra, agachado passa
    m.tunelEmPe = Number((await andarAte(-25, -2, 2.0)).z.toFixed(2));
    await posicionar(page, -25, 0, -2, 0, 0);
    await tecla(page, "KeyC", true); await tecla(page, "KeyW", true);
    await esperarJogo(page, 7.0);
    await tecla(page, "KeyW", false); await tecla(page, "KeyC", false);
    m.tunelAgachado = Number((await estado(page)).z.toFixed(2));
    expect(Number(m.tunelEmPe)).toBeLessThan(0.0);
    expect(Number(m.tunelAgachado)).toBeGreaterThan(6.0);
    registrar("fase-1", { movimento: m });
  });

  test("áreas antigas: bordas laterais sem bloquear a câmera e volta ao chão depois de cair do mapa", async ({ page }) => {
    await page.setViewportSize({ width: 640, height: 360 });
    await abrir(page, "area=praca&render=webgl2&qualidade=alta");
    await esperarJogo(page, 0.5);
    const m: Record<string, unknown> = {};
    // andando para a lateral (+Z) por 3 s: a parede invisível segura o personagem na faixa
    await posicionar(page, -40, 0, 0, 0, 0);
    await tecla(page, "KeyW", true);
    await esperarJogo(page, 3);
    await tecla(page, "KeyW", false);
    let e = await estado(page);
    m.bordaZ = Number(e.z.toFixed(2));
    m.bordaY = Number(e.y.toFixed(2));
    expect(e.z).toBeLessThan(3.2);
    expect(e.y).toBeGreaterThan(-0.5);
    // câmera do lado de fora da faixa (atrás da parede invisível): não é empurrada
    await esperarJogo(page, 1);
    const cam = await js<{ x: number; y: number; z: number }>(page, "window.__vc.camera()");
    m.distanciaCameraNaBorda = Number(Math.hypot(cam.x - e.x, cam.z - e.z).toFixed(2));
    expect(cam.z).toBeLessThan(-0.5);
    expect(Number(m.distanciaCameraNaBorda)).toBeGreaterThan(3.5);
    // queda para fora do mapa: volta ao último chão firme
    await posicionar(page, -40, 0, 0, 0, 0);
    await page.evaluate(() => {
      const j = (window.__vc.jogo as { jogador: { controlador: { getPosition(): { clone(): { z: number } } }; moverPara(v: unknown): void } }).jogador;
      const v = j.controlador.getPosition().clone();
      v.z = 12;
      j.moverPara(v);
    });
    await esperarJogo(page, 0.4);
    m.yDuranteQueda = Number((await estado(page)).y.toFixed(2));
    await esperarJogo(page, 2.6);
    e = await estado(page);
    m.voltaDoVazio = { x: Number(e.x.toFixed(2)), y: Number(e.y.toFixed(2)), z: Number(e.z.toFixed(2)) };
    expect(Number(m.yDuranteQueda)).toBeLessThan(-0.5);
    expect(e.y).toBeGreaterThan(-0.5);
    expect(Math.abs(e.z)).toBeLessThan(1);
    registrar("fase-1", { areasAntigas: m });
  });
});
