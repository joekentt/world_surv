import * as fs from "node:fs";
import { expect, test, type Page } from "@playwright/test";
import { abrir, registrar } from "./util";

/**
 * Fase 2 (revisão 2): "Novo jogo" no mundo novo e sinalização de rota em neon (seção 7 de
 * docs/spec/07-arte-personagens-vila.md). Letreiros e faixas de luz em tools/areas/sinalizacao.py.
 *  a) o menu começa na praça da Vila Cisterna (área vila_praca, mundo "subsolo"), sem a introdução da revisão 1;
 *  b) o navmesh liga o ponto inicial à eclusa, e todo trecho dessa rota tem um letreiro de rota a menos de 40 m;
 *  c) screenshots da vista inicial e dos letreiros no duto, na estação, no topo do poço e na saída da eclusa.
 */

type V3 = [number, number, number];
type Estado = { x: number; y: number; z: number; estado: string; area?: string; mundo: string; yaw: number };
type Rota = { ok: boolean; motivo?: string; comprimento: number; horizontal: number; pontos: V3[]; escadas: number };
type Letreiro = { id: string; area: string; x: number; y: number; z: number; r: number; texto: string; sub?: string; seta?: string };

const GRAU = Math.PI / 180;
const DIR = "tests/screenshots/fase-2";
const js = <T = unknown>(p: Page, f: string) => p.evaluate(f) as Promise<T>;
const estado = (p: Page) => js<Estado>(p, "window.__vc.estado()");
const tempo = (p: Page) => js<number>(p, "window.__vc.jogo.tempo");
const r2 = (v: number) => Number(v.toFixed(2));
const area = (id: string) => JSON.parse(fs.readFileSync(`content/areas/${id}.json`, "utf8"));
const TEXTOS = JSON.parse(fs.readFileSync("content/textos/letreiros.json", "utf8")) as Record<string, string>;
/** Distância máxima (m) de qualquer ponto da rota até o letreiro de rota mais próximo. */
const DIST_MAX = 40;

async function esperarJogo(p: Page, s: number) {
  const t0 = await tempo(p);
  await p.waitForFunction((alvo) => (window.__vc.jogo as { tempo: number }).tempo >= alvo, t0 + s, { timeout: 240_000 });
}

/** Teleporta, aponta a câmera e espera as áreas próximas carregarem (e o nome da área sumir da tela). */
async function vista(p: Page, x: number, y: number, z: number, yaw: number, pitch: number, extra = 0, espera = 5) {
  await p.evaluate(([x, y, z, yw, pt, d]) => {
    (window.__vc.teleportar as (x: number, y: number, z: number, yaw: number) => void)(x, y, z, yw);
    (window.__vc.definirCamera as (y: number, p?: number) => void)(yw, pt);
    (window.__vc.jogo as { camera: { distanciaExtra: number } }).camera.distanciaExtra = d;
  }, [x, y, z, yaw, pitch, extra] as const);
  await esperarJogo(p, espera);
}

/** Pontos ao longo da polilinha, a cada `passo` m (em 3D). */
function amostrar(pontos: V3[], passo: number): V3[] {
  const r: V3[] = [];
  for (let i = 1; i < pontos.length; i++) {
    const [a, b] = [pontos[i - 1], pontos[i]];
    const l = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    const n = Math.max(1, Math.ceil(l / passo));
    for (let k = 0; k < n; k++) r.push([a[0] + ((b[0] - a[0]) * k) / n, a[1] + ((b[1] - a[1]) * k) / n, a[2] + ((b[2] - a[2]) * k) / n]);
  }
  r.push(pontos[pontos.length - 1]);
  return r;
}

test.describe("fase 2: início pelo menu e sinalização de rota", () => {
  test.setTimeout(1_800_000);

  test("Novo jogo começa na praça da Vila Cisterna, com rota sinalizada até a eclusa", async ({ page }) => {
    const erros: string[] = [];
    page.on("console", (m) => { if (m.type() === "error" || /uniform|shader/i.test(m.text())) erros.push(m.text()); });
    await page.setViewportSize({ width: 1280, height: 720 });
    const m: Record<string, unknown> = {};

    // a) menu sem ?area: "Novo jogo" leva à praça do mundo novo
    await abrir(page, "render=webgl2&qualidade=alta");
    await page.waitForSelector(".titulo button[data-v='novo']", { timeout: 180_000 });
    await page.click(".titulo button[data-v='novo']");
    await page.waitForFunction(() => {
      const e = (window.__vc.estado as () => Estado)();
      return e.area === "vila_praca" && e.estado !== "travado";
    }, null, { timeout: 120_000 });
    await esperarJogo(page, 5.5); // nome da área some; áreas próximas carregadas
    const e0 = await estado(page);
    const inicio = area("vila_praca").entradas.inicio;
    expect(e0.area).toBe("vila_praca");
    expect(e0.mundo).toBe("subsolo");
    expect(Math.hypot(e0.x - inicio.x, e0.z - inicio.z), "no ponto inicial").toBeLessThan(0.5);
    const missoes = await js<Record<string, { estado: string }>>(page, "window.__vc.missoes()");
    expect(missoes.m1?.estado, "sem a primeira missão da revisão 1").not.toBe("ativa");
    const dialogoAberto = await js<boolean>(page, "window.__vc.jogo.ui.dialogo.aberto");
    expect(dialogoAberto, "sem a introdução da revisão 1").toBeFalsy();
    const naCena = await js<string[]>(page, "window.__vc.letreirosNaCena()");
    expect(naCena.some((n) => n.includes("praca_duto")), "letreiro principal montado").toBeTruthy();
    await page.screenshot({ path: `${DIR}/rota_01_inicio.png` });
    m.inicio = { area: e0.area, mundo: e0.mundo, x: r2(e0.x), z: r2(e0.z), yaw: r2(e0.yaw), letreirosNaCena: naCena.length };

    // b) rota do navmesh do ponto inicial até a porta externa da eclusa, e letreiros a menos de 40 m de cada trecho
    const letreiros = await js<Letreiro[]>(page, "window.__vc.letreiros('subsolo')");
    for (const l of letreiros) {
      expect(Object.values(TEXTOS), `texto do letreiro ${l.id}`).toContain(l.texto);
      if (l.sub) expect(Object.values(TEXTOS), `subtítulo do letreiro ${l.id}`).toContain(l.sub);
    }
    // letreiros de rota: os que apontam um destino da rota principal (os da Fenda e das Galerias são desvios)
    const destinos = ["duto_norte", "estacao_aurora", "boca_do_poco", "superficie", "eclusa"].map((k) => TEXTOS[k]);
    const deRota = letreiros.filter((l) => destinos.includes(l.texto));
    const eclusa = area("boca_estacao").saidas.find((s: { destino: string }) => s.destino === "superficie_boca");
    const rota = await page.evaluate(([a, b]) => (window.__vc.rotaNav as (m: string, a: V3, b: V3, e: V3) => Promise<Rota>)("subsolo", a, b, [1, 1, 1]),
      [[e0.x, e0.y, e0.z] as V3, [eclusa.x, eclusa.y, eclusa.z - 0.5] as V3] as const);
    expect(rota.ok, `rota do navmesh: ${rota.motivo}`).toBeTruthy();
    const fim = rota.pontos[rota.pontos.length - 1];
    expect(Math.hypot(fim[0] - eclusa.x, fim[2] - (eclusa.z - 0.5)), "rota chega à eclusa").toBeLessThan(1.5);
    expect(rota.escadas, "sobe o poço pelas escadas").toBeGreaterThanOrEqual(4);
    let pior = { d: 0, p: [0, 0, 0] as V3 };
    const amostras = amostrar(rota.pontos, 2);
    for (const p of amostras) {
      const d = Math.min(...deRota.map((l) => Math.hypot(l.x - p[0], l.y - p[1], l.z - p[2])));
      if (d > pior.d) pior = { d, p };
    }
    m.rota = { comprimento_m: r2(rota.comprimento), horizontal_m: r2(rota.horizontal), escadas: rota.escadas, pontos: rota.pontos.length,
      letreiros: letreiros.length, letreirosDeRota: deRota.length, maiorDistanciaAoLetreiro_m: r2(pior.d), pontoMaisLonge: pior.p.map(r2) };
    expect(pior.d, `ponto da rota longe dos letreiros: (${pior.p.map(r2).join(", ")})`).toBeLessThan(DIST_MAX);
    // do lado da superfície, um letreiro na saída da eclusa aponta a volta
    const sup = await js<Letreiro[]>(page, "window.__vc.letreiros('superficie_aberta')");
    const volta = sup.filter((l) => l.texto === TEXTOS.eclusa && Math.hypot(l.x, l.z) < 20);
    expect(volta.length, "letreiro da eclusa na superfície").toBeGreaterThan(0);

    // c) screenshots dos letreiros (câmera em terceira pessoa, a 10-20 m deles)
    // Duto Norte, antes do primeiro desvio (Caverna da Fenda): placa da Estação Aurora e faixa ciano
    await vista(page, -0.5, -2.5, 78, 0, 6 * GRAU, 0, 6);
    await page.screenshot({ path: `${DIR}/rota_02_galerias_ou_duto.png` });
    // Estação Aurora, logo depois do portão: placa da Boca do Poço sobre a ilha
    await vista(page, 144.5, -25, 201.6, 84 * GRAU, 6 * GRAU, 0, 6);
    await page.screenshot({ path: `${DIR}/rota_03_estacao.png` });
    // topo do poço: casa do poço, placa da eclusa e faixa âmbar no piso
    await vista(page, 174.6, 0, 203.2, 15 * GRAU, 8 * GRAU, -1, 5);
    await page.screenshot({ path: `${DIR}/rota_04_eclusa.png` });
    // superfície: saída da eclusa, olhando de volta para a casamata
    await page.evaluate(() => (window.__vc.jogo as { transicionar: (a: string, e: string) => Promise<void> }).transicionar("superficie_boca", "boca"));
    await page.waitForFunction(() => (window.__vc.estado as () => Estado)().mundo === "superficie_aberta", null, { timeout: 120_000 });
    await vista(page, 0, 0.1, 27, 180 * GRAU, 20 * GRAU, 1.5, 5);
    await page.screenshot({ path: `${DIR}/rota_05_superficie.png` });

    m.errosConsole = erros.length;
    registrar("fase-2", { rota_sinalizada: m });
    expect(erros, erros.join("\n")).toHaveLength(0);
  });
});
