import type { EstadoMissao } from "../core/estado";
import type { Jogo } from "../core/jogo";

/**
 * Efeitos disparados por diálogos e gatilhos de missão (JSON em content/):
 *   { "missao": "m1", "estado": "ativa", "etapa": 1 }   { "flag": "x", "valor": true }
 *   { "dar": "item", "qtd": 1 }   { "tirar": "item", "qtd": 1 }   { "tirarTodos": "item" }
 *   { "cotas": 5 }   { "upgrade": "filtro", "valor": 2 }   { "abrirLoja": "bento" }
 *   { "mensagem": "texto" }   { "desfecho": "conselho" }   { "gravacao": true }   { "salvar": true }
 */
export type Efeito = Record<string, unknown>;

export function aplicarEfeitos(jogo: Jogo, efeitos: Efeito[] | undefined): void {
  if (!efeitos) return;
  const e = jogo.estado;
  for (const ef of efeitos) {
    if (typeof ef.missao === "string") {
      const atual = e.missao(ef.missao);
      const estado = (ef.estado as EstadoMissao) ?? "ativa";
      const etapa = typeof ef.etapa === "number" ? ef.etapa : estado === atual.estado ? atual.etapa : 0;
      e.definirMissao(ef.missao, estado, etapa);
      jogo.missoes.anunciar(ef.missao, estado, etapa);
    }
    if (typeof ef.flag === "string") e.definirFlag(ef.flag, (ef.valor as boolean | number | string) ?? true);
    if (typeof ef.dar === "string") e.dar(ef.dar, Number(ef.qtd ?? 1));
    if (typeof ef.tirar === "string") e.dar(ef.tirar, -Number(ef.qtd ?? 1));
    if (typeof ef.tirarTodos === "string") e.dar(ef.tirarTodos, -e.qtd(ef.tirarTodos));
    if (typeof ef.cotas === "number") {
      e.mudarCotas(ef.cotas);
      jogo.audio.tocar("moedas", 0.6);
    }
    if (typeof ef.upgrade === "string") {
      (e.d.upgrades as Record<string, unknown>)[ef.upgrade] = ef.valor ?? true;
      e.avisar("upgrade");
    }
    if (typeof ef.mensagem === "string") jogo.hud.mensagemCurta(ef.mensagem, 3.5);
    if (typeof ef.abrirLoja === "string") jogo.depoisDoDialogo = () => jogo.loja.abrir(ef.abrirLoja as string);
    if (typeof ef.desfecho === "string") jogo.depoisDoDialogo = () => void jogo.roteiro.desfecho(ef.desfecho as string);
    if (ef.gravacao) jogo.depoisDoDialogo = () => void jogo.roteiro.tocarGravacao();
    if (ef.salvar) void jogo.salvar();
  }
}
