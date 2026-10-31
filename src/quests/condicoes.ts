import type { Estado } from "../core/estado";

/**
 * Condições usadas em diálogos, missões e conversas de fundo (JSON em content/).
 * Um objeto com várias chaves exige todas. Formatos:
 *   { "flag": "x", "valor": true }        flag igual a valor (sem valor: verdadeira)
 *   { "naoFlag": "x" }                     flag ausente ou falsa
 *   { "flagMaior": "x", "valor": 2 }       flag numérica maior que valor
 *   { "missao": "m1", "estado": "ativa" }  estado da missão
 *   { "missao": "m1", "etapa": 2 }         etapa atual da missão (com estado ativa)
 *   { "item": "sucata", "min": 3 }         quantidade no inventário
 *   { "cotas": 10 }                         pelo menos tantas cotas
 *   { "upgrade": "filtro", "min": 2 }      nível de upgrade
 *   { "todas": [...] } / { "alguma": [...] } / { "nao": {...} }
 */
export type Condicao = Record<string, unknown>;

export function avaliar(c: Condicao | undefined | null, e: Estado, contexto: Record<string, unknown> = {}): boolean {
  if (!c || Object.keys(c).length === 0) return true;
  if (Array.isArray(c.todas) && !(c.todas as Condicao[]).every((x) => avaliar(x, e, contexto))) return false;
  if (Array.isArray(c.alguma) && !(c.alguma as Condicao[]).some((x) => avaliar(x, e, contexto))) return false;
  if (c.nao && avaliar(c.nao as Condicao, e, contexto)) return false;
  if (typeof c.flag === "string") {
    const v = e.flag(c.flag);
    if ("valor" in c ? v !== c.valor : !v) return false;
  }
  if (typeof c.naoFlag === "string" && e.flag(c.naoFlag)) return false;
  if (typeof c.flagMaior === "string" && !(Number(e.flag(c.flagMaior) ?? 0) > Number(c.valor ?? 0))) return false;
  if (typeof c.missao === "string") {
    const m = e.missao(c.missao);
    if (typeof c.estado === "string" && m.estado !== c.estado) return false;
    if (typeof c.etapa === "number" && (m.estado !== "ativa" || m.etapa !== c.etapa)) return false;
    if (typeof c.etapaMin === "number" && !(m.estado === "concluida" || (m.estado === "ativa" && m.etapa >= c.etapaMin))) return false;
  }
  if (typeof c.item === "string" && e.qtd(c.item) < Number(c.min ?? 1)) return false;
  if (typeof c.semItem === "string" && e.qtd(c.semItem) > 0) return false;
  if (typeof c.cotas === "number" && e.d.cotas < c.cotas) return false;
  if (typeof c.upgrade === "string") {
    const u = (e.d.upgrades as Record<string, unknown>)[c.upgrade];
    if (typeof u === "number" ? u < Number(c.min ?? 1) : !u) return false;
  }
  if (c.criancas !== undefined && contexto.crianca !== c.criancas) return false;
  return true;
}
