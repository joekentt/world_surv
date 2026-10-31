import type { Jogo } from "../core/jogo";
import { textos } from "../ui/textos";

/**
 * Ciclo da subida: eclusa (filtro novo, roupa reparada), descontaminação na volta e morte.
 * Ao morrer, o jogador acorda na vila e perde o que coletou nesta subida.
 */
export class Subida {
  private inventarioAntes: Record<string, number> | null = null;
  emSequencia = false;

  constructor(private jogo: Jogo) {
    jogo.aoUsarEclusa = (destino) => this.eclusa(destino);
    jogo.epi.aoMorrer = () => void this.morrer();
  }

  private espera(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }

  async eclusa(destino: string): Promise<boolean> {
    const j = this.jogo;
    const subindo = destino.startsWith("superficie");
    if (subindo) {
      if (j.estado.qtd("filtro_reposicao") < 1) {
        j.hud.mensagemCurta(textos("epi.semFiltro"), 4);
        j.audio.tocar("alerta_grave", 0.5);
        return false;
      }
      this.emSequencia = true;
      j.jogador.travar(true);
      j.estado.dar("filtro_reposicao", -1);
      j.epi.equipar();
      this.inventarioAntes = { ...j.estado.d.itens };
      j.coletaveis.novaSubida();
      j.audio.tocar("eclusa", 0.9);
      j.hud.mensagemCurta(textos("eclusa.saindo"), 3);
      await this.espera(1800);
      j.estado.d.subidas += 1;
      j.estado.avisar("subida");
      j.aposTransicao = () => { j.epi.entrarSuperficie(); this.emSequencia = false; };
      return true;
    }
    // voltando da superfície
    this.emSequencia = true;
    j.jogador.travar(true);
    j.epi.sairSuperficie();
    j.audio.laco("chuveiro", 0.6);
    j.hud.mensagemCurta(textos("eclusa.entrando"), 3);
    await this.espera(1800);
    j.audio.laco("chuveiro", 0);
    this.inventarioAntes = null;
    j.aposTransicao = () => {
      j.hud.mensagemCurta(textos("eclusa.voltou", { s: Math.ceil(j.epi.filtro) }), 3);
      this.emSequencia = false;
      j.estado.avisar("voltou");
    };
    return true;
  }

  async morrer(): Promise<void> {
    const j = this.jogo;
    j.jogador.estado = "morto";
    j.jogador.personagem.tocar("morrer", { loop: false, transicao: 0.2 });
    j.audio.tocar("morte", 0.9);
    j.epi.sairSuperficie();
    await this.espera(1800);
    await j.hud.escurecer(true, 900);
    j.hud.telaMorte(textos("morte.titulo"), textos("morte.texto"));
    if (this.inventarioAntes) {
      const missao = ["mascara_darci", "gravador_darci", "amostra_terra"];
      const guardados = Object.fromEntries(missao.filter((k) => j.estado.qtd(k) && !this.inventarioAntes![k]).map((k) => [k, 0]));
      j.estado.d.itens = { ...this.inventarioAntes, ...guardados };
      for (const k of Object.keys(j.estado.d.itens)) if (!j.estado.d.itens[k]) delete j.estado.d.itens[k];
      j.estado.avisar("itens");
    }
    this.inventarioAntes = null;
    await this.espera(3500);
    j.epi.saude = 100;
    j.epi.morto = false;
    j.jogador.estado = "chao";
    j.estado.definirFlag("mortes", Number(j.estado.flag("mortes") ?? 0) + 1);
    await j.transicionar("praca", "inicio");
    j.hud.telaMorte(null, null);
    j.estado.avisar("acordou");
  }
}
