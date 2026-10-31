import interface_ from "../../content/textos/interface.json";

/** Textos fixos da interface (content/textos/interface.json). */
export const UI = interface_;

/** Busca um texto por chave e troca {variáveis}. */
export function textos(chave: string, vars: Record<string, string | number> = {}): string {
  const bruto = (interface_ as Record<string, string>)[chave] ?? chave;
  return bruto.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}
