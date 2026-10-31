import nomes from "../../content/itens/itens.json";
import { CFG } from "../config";

type Nome = { nome: string; plural: string; descricao: string };
const NOMES = nomes as Record<string, Nome>;
const DADOS = CFG.inventario.itens as Record<string, { peso: number; preco: number }>;

export function nomeItem(id: string, n = 1): string {
  const d = NOMES[id];
  if (!d) return id;
  return n === 1 ? d.nome : d.plural;
}

export function descricaoItem(id: string): string {
  return NOMES[id]?.descricao ?? "";
}

export function pesoItem(id: string): number {
  return DADOS[id]?.peso ?? 0;
}

export function precoItem(id: string): number {
  return DADOS[id]?.preco ?? 0;
}

/** Itens que podem ser vendidos no mercado (têm preço). */
export function vendaveis(): string[] {
  return Object.keys(DADOS).filter((k) => DADOS[k].preco > 0);
}
