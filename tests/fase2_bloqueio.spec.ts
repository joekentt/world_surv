import { expect, test, type Page } from "@playwright/test";
import * as fs from "node:fs";
import { CFG } from "../src/config";
import { abrir, registrar } from "./util";

/**
 * Fase 2, tarefa 7 (revisão 2): teste de bloqueio por EPI da seção 5.3 de docs/spec/05-mapa.md.
 *
 * Pelo navmesh da superfície (src/npc/navegacaoNiveis.ts, gancho window.__vc.rotaNav), calcula a rota mais
 * curta da Boca do Poço a cada destino e a volta pela saída aberta mais próxima, em cada momento da
 * história (docs/spec/04-mundo-roteiro.md): só a Boca até concluir a missão 3; Boca e Escotilha Oeste
 * depois dela; e a Escotilha Leste também, com a tarefa opcional.
 *
 * Regra: a ida e volta correndo (7 m/s, no plano) ultrapassa o filtro efetivo do nível anterior
 * (filtro / 1,3) e cabe no efetivo do nível exigido com pelo menos 30 s de folga. As ruínas cabem no básico.
 *
 * Convenção dos pontos (tempo de verdade na superfície): a ida começa onde a eclusa solta o jogador
 * (entrada "boca", 8 m ao norte do centro da Boca); a volta termina no ponto de uso da saída (a porta
 * da eclusa, ou o lado do alçapão de cada escotilha, que são as entradas das áreas). O destino é o ponto
 * do navmesh mais próximo do centro do marco (a base do monumento do Marco, o topo da colina da Antena).
 * Para referência, a tabela também traz a variante medida do centro da Boca (origem), como na seção 5.2.
 */

type V3 = [number, number, number];
type Rota = { ok: boolean; motivo?: string; comprimento: number; horizontal: number; pontos: V3[]; inicio?: V3; fim?: V3 };

const MUNDO = "superficie_aberta";
const CORRIDA = CFG.movimento.correr;
const MULT = CFG.epi.multiplicadorCorrida;
const FOLGA = 30;
const FILTROS = { basico: CFG.epi.filtroBasico, nivel2: CFG.epi.filtroNivel2, nivel3: CFG.epi.filtroNivel3 };
type Nivel = keyof typeof FILTROS;
const efetivo = (n: Nivel) => FILTROS[n] / MULT;
const ANTERIOR: Record<Nivel, Nivel | null> = { basico: null, nivel2: "basico", nivel3: "nivel2" };

const area = (id: string) => JSON.parse(fs.readFileSync(`content/areas/${id}.json`, "utf8"));
const entrada = (id: string, nome: string): V3 => { const e = area(id).entradas[nome]; return [e.x, e.y, e.z]; };

/** Saídas seguras: ponto de uso (onde o jogador fica para entrar) e o centro da seção 5.2. */
const SAIDAS: Record<string, { uso: V3; centro: [number, number] }> = {
  boca: { uso: (() => { const s = area("superficie_boca").saidas[0]; return [s.x, s.y + 0.1, s.z] as V3; })(), centro: [0, 0] },
  oeste: { uso: entrada("superficie_escotilha_oeste", "escotilha"), centro: [-178, 115] },
  leste: { uso: entrada("superficie_escotilha_leste", "escotilha"), centro: [191, 76] },
};
const INICIO = entrada("superficie_boca", "boca");

/** Destinos: centro (x, y, z) e a caixa de busca da projeção no navmesh. */
const abrigoB = area("superficie_ruinas").abrigos.find((a: { id: string }) => a.id === "abrigo_ruinas_b");
const DESTINOS: Record<string, { ponto: V3; ext: V3; nivel: Nivel; nome: string }> = {
  ruinas_abrigo_b: { ponto: [(abrigoB.min[0] + abrigoB.max[0]) / 2, abrigoB.min[1] + 0.2, (abrigoB.min[2] + abrigoB.max[2]) / 2], ext: [4, 1.5, 4], nivel: "basico", nome: "Ruínas: abrigo B (~101 m)" },
  ruinas_borda_norte: { ponto: [0, 0, 127], ext: [3, 2, 3], nivel: "basico", nome: "Ruínas: borda norte (127 m)" },
  marco: { ponto: [-51, 0.84, 255], ext: [3, 1.5, 3], nivel: "nivel2", nome: "O Marco" },
  antena: { ponto: [38, 27.4, 484], ext: [4, 3, 4], nivel: "nivel3", nome: "A Antena (topo da colina)" },
};

/**
 * Momentos da história: saídas abertas e os destinos em que a regra vale. O Marco só entra no primeiro:
 * a Escotilha Oeste abre ao concluir a missão 3 (a do Marco) justamente porque, aberta, a volta por ela
 * caberia no filtro básico (exemplo da seção 5.3). A Leste abre na tarefa opcional, sem momento fixo na
 * spec 04; o caso "Leste antes da missão 3" é medido e só informado.
 */
const MOMENTOS: { id: string; nome: string; saidas: string[]; regra: string[]; informativo?: boolean }[] = [
  { id: "inicio", nome: "Missões 1 a 3: só a Boca", saidas: ["boca"], regra: ["ruinas_abrigo_b", "ruinas_borda_norte", "marco", "antena"] },
  { id: "apos_missao_3", nome: "Depois da missão 3: Boca e Escotilha Oeste", saidas: ["boca", "oeste"], regra: ["ruinas_abrigo_b", "ruinas_borda_norte", "antena"] },
  { id: "com_opcional", nome: "Com a tarefa opcional: Boca, Oeste e Leste", saidas: ["boca", "oeste", "leste"], regra: ["ruinas_abrigo_b", "ruinas_borda_norte", "antena"] },
  { id: "leste_antes_m3", nome: "Hipótese: Leste aberta antes da missão 3 (Boca e Leste)", saidas: ["boca", "leste"], regra: ["marco", "antena"], informativo: true },
];

const r1 = (v: number) => Number(v.toFixed(1));
const plano = (a: V3, b: [number, number]) => Math.hypot(a[0] - b[0], a[2] - b[1]);

async function rota(p: Page, a: V3, b: V3, ext?: V3): Promise<Rota> {
  return p.evaluate(([m, a, b, ext]) => (window.__vc.rotaNav as (m: string, a: V3, b: V3, e?: V3) => Promise<Rota>)(m, a, b, ext ?? undefined), [MUNDO, a, b, ext ?? null] as const);
}

test.describe("fase 2: regra de bloqueio por EPI (seção 5.3)", () => {
  test.setTimeout(300_000);

  test("rotas do navmesh da superfície por momento da história", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 180 });
    await abrir(page, "area=superficie_boca&entrada=boca&render=webgl2&qualidade=baixa");
    const info = await page.evaluate((m) => (window.__vc.navmesh as (m: string) => Promise<Record<string, number>>)(m), MUNDO);
    expect(info.poligonos).toBeGreaterThan(1000);

    // idas (da eclusa ao destino) e voltas (do destino a cada saída)
    const idas: Record<string, Rota> = {};
    const voltas: Record<string, Record<string, Rota>> = {};
    for (const [id, d] of Object.entries(DESTINOS)) {
      idas[id] = await rota(page, INICIO, d.ponto, d.ext);
      expect(idas[id].ok, `ida a ${d.nome}: ${idas[id].motivo}`).toBeTruthy();
      voltas[id] = {};
      for (const [s, saida] of Object.entries(SAIDAS)) {
        voltas[id][s] = await rota(page, idas[id].fim!, saida.uso, [0.5, 0.5, 0.5]);
        expect(voltas[id][s].ok, `volta de ${d.nome} pela saída ${s}: ${voltas[id][s].motivo}`).toBeTruthy();
      }
    }

    const tabela: Record<string, unknown>[] = [];
    const falhas: string[] = [];
    for (const mom of MOMENTOS) {
      for (const [id, d] of Object.entries(DESTINOS)) {
        const ida = idas[id];
        const [saida, volta] = mom.saidas.map((s) => [s, voltas[id][s]] as const).sort((a, b) => a[1].horizontal - b[1].horizontal)[0];
        const dist = ida.horizontal + volta.horizontal;
        const t = dist / CORRIDA;
        // variante da seção 5.2: do centro da Boca e até o centro da saída, em linha reta além do navmesh
        const extra = plano(INICIO, SAIDAS.boca.centro) + plano(SAIDAS[saida].uso, SAIDAS[saida].centro);
        const tOrigem = (dist + extra) / CORRIDA;
        const ant = ANTERIOR[d.nivel];
        const min = ant ? efetivo(ant) : 0;
        const max = efetivo(d.nivel) - FOLGA;
        const aplica = mom.regra.includes(id);
        const cumpre = t > min && t <= max;
        const linha = {
          momento: mom.id, destino: id, saidaVolta: saida,
          ida_m: r1(ida.horizontal), volta_m: r1(volta.horizontal), idaEVolta_m: r1(dist), idaEVolta3d_m: r1(ida.comprimento + volta.comprimento),
          tempoCorrendo_s: r1(t), tempoDaOrigem_s: r1(tOrigem),
          filtroExigido: d.nivel, efetivoAnterior_s: r1(min), efetivoExigido_s: r1(efetivo(d.nivel)), folga_s: r1(efetivo(d.nivel) - t),
          cabeNoBasico: t <= efetivo("basico"), regraAplicada: aplica && !mom.informativo, cumpre,
          desvioDoCentro_m: r1(plano(ida.fim!, [d.ponto[0], d.ponto[2]])),
        };
        tabela.push(linha);
        if (aplica && !cumpre) {
          const msg = `${mom.nome} / ${d.nome}: ${r1(t)} s (precisa de > ${r1(min)} s e <= ${r1(max)} s)`;
          if (mom.informativo) console.log(`[informativo] ${msg}`);
          else falhas.push(msg);
        }
      }
    }
    for (const l of tabela) console.log(JSON.stringify(l));
    registrar("fase-2", {
      bloqueio: {
        convencao: "ida da entrada da eclusa (0, 8) ao destino; volta até o ponto de uso da saída aberta mais próxima; tempo = distância no plano / 7 m/s; tempoDaOrigem_s soma os trechos retos até os centros da Boca e da saída",
        navmesh: info, corrida_m_s: CORRIDA, filtrosEfetivos_s: { basico: r1(efetivo("basico")), nivel2: r1(efetivo("nivel2")), nivel3: r1(efetivo("nivel3")) },
        rotas: tabela,
        falhas,
      },
    });
    expect(falhas, falhas.join("\n")).toHaveLength(0);
  });
});
