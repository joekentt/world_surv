import { Color3, MeshBuilder, PointLight, StandardMaterial, Vector3, type Mesh } from "@babylonjs/core";
import roteiro from "../../content/textos/roteiro.json";
import sermoes from "../../content/dialogos/sermoes.json";
import type { Jogo } from "../core/jogo";
import { avaliar, type Condicao } from "./condicoes";
import { aplicarEfeitos, type Efeito } from "./efeitos";

type Linha = { quem: string; texto: string };
const R = roteiro as unknown as {
  intro: string[]; gravacao: Linha[]; achado: string[]; radio: string[];
  desfechos: Record<string, { reacao: Linha[]; efeitos: Efeito[]; epilogo: string[] }>;
  fim: { titulo: string; subtitulo: string; obrigado: string };
  muro: Record<string, string>; fotos: string[];
};
const S = sermoes as unknown as { variantes: { se?: Condicao; falas: string[] }[] };

/**
 * Momentos de roteiro que não cabem numa conversa: introdução, gravação de Darci, desfechos,
 * epílogo na superfície com a luz no horizonte, sermão da Capela, rádio da Caravana e o Muro.
 */
export class Roteiro {
  private relogioSermao = 0;
  private indiceSermao = 0;
  private relogioRadio = 12;
  private luzHorizonte: { malha: Mesh; luz: PointLight } | null = null;
  emEpilogo = false;

  constructor(private jogo: Jogo) {}

  private espera(ms: number): Promise<void> {
    return new Promise((r) => setTimeout(r, ms));
  }

  async introducao(): Promise<void> {
    const j = this.jogo;
    j.travarParaDialogo(true);
    await j.hud.escurecer(true, 10);
    for (const t of R.intro) await j.ui.dialogo.fala("", t, false);
    j.ui.dialogo.fechar();
    await j.hud.escurecer(false, 900);
    j.travarParaDialogo(false);
  }

  /** Monólogo da gravação encontrada na Antena. */
  async tocarGravacao(): Promise<void> {
    const j = this.jogo;
    j.travarParaDialogo(true);
    j.audio.laco("radio", 0.25);
    for (const l of R.gravacao) await j.ui.dialogo.fala(l.quem, l.texto, false);
    j.audio.laco("radio", 0);
    j.ui.dialogo.fechar();
    j.travarParaDialogo(false);
  }

  async achado(): Promise<void> {
    const j = this.jogo;
    if (j.estado.qtd("gravador_darci") > 0) return;
    j.travarParaDialogo(true);
    for (const t of R.achado) await j.ui.dialogo.fala("", t, false);
    j.ui.dialogo.fechar();
    j.travarParaDialogo(false);
    aplicarEfeitos(j, [{ dar: "mascara_darci" }, { dar: "gravador_darci" }, { missao: "m4", estado: "ativa", etapa: 1 }]);
    await this.tocarGravacao();
  }

  async desfecho(qual: string): Promise<void> {
    const j = this.jogo;
    const d = R.desfechos[qual];
    if (!d || j.estado.flag("desfecho")) return;
    j.estado.definirFlag("desfecho", qual);
    aplicarEfeitos(j, d.efeitos);
    aplicarEfeitos(j, [{ missao: "m4", estado: "concluida", etapa: 2 }]);
    j.travarParaDialogo(true);
    for (const l of d.reacao) await j.ui.dialogo.fala(l.quem, l.texto, l.quem === "Você");
    j.ui.dialogo.fechar();
    j.travarParaDialogo(false);
    this.atualizarMuro();
    await j.salvar();
    await this.espera(800);
    await this.epilogo(qual);
  }

  /** O MVP termina na superfície, à noite, com a luz piscando no horizonte. */
  async epilogo(qual: string): Promise<void> {
    const j = this.jogo;
    this.emEpilogo = true;
    j.travarParaDialogo(true);
    await j.hud.escurecer(true, 1200);
    for (const t of R.desfechos[qual].epilogo) await j.ui.dialogo.fala("", t, false);
    j.ui.dialogo.fechar();
    j.subida.emSequencia = true;
    await j.transicionar("superficie_antena", "epilogo", () => {
      j.iluminacao.definirPerfil("superficie_noite", true);
    });
    j.epi.sairSuperficie();
    j.iluminacao.definirPerfil("superficie_noite", true);
    j.pos.definir("superficie_noite");
    j.jogador.travar(true);
    j.jogador.personagem.virar(1);
    this.criarLuzHorizonte();
    j.camera.distanciaExtra = 6;
    j.camera.alturaExtra = 2.5;
    await this.espera(2500);
    j.hud.telaFim(R.fim.titulo, `${R.fim.subtitulo}<br><br>${R.desfechos[qual].epilogo.at(-1) ?? ""}`, R.fim.obrigado);
    j.estado.definirFlag("fim_visto", true);
  }

  private criarLuzHorizonte(): void {
    if (this.luzHorizonte) return;
    const cena = this.jogo.cena;
    const malha = MeshBuilder.CreateSphere("luz_horizonte", { diameter: 3, segments: 8 }, cena);
    malha.position = new Vector3(620, 14, 380);
    const m = new StandardMaterial("luz_horizonte_mat", cena);
    m.emissiveColor = new Color3(1, 0.85, 0.55);
    m.disableLighting = true;
    malha.material = m;
    malha.infiniteDistance = false;
    const luz = new PointLight("luz_horizonte_pt", malha.position.clone(), cena);
    luz.diffuse = new Color3(1, 0.8, 0.5);
    luz.range = 60;
    this.luzHorizonte = { malha, luz };
  }

  /** A máscara de Darci só aparece no muro se o Conselho o declarar morto. */
  atualizarMuro(): void {
    const mostrar = this.jogo.estado.flag("desfecho") === "conselho";
    for (const m of this.jogo.cena.meshes) if (m.name.includes("mascara_darci_muro")) m.isVisible = mostrar;
  }

  textoMuro(): string {
    const d = this.jogo.estado.flag("desfecho");
    return R.muro[typeof d === "string" ? d : "antes"];
  }

  textoFotos(): string {
    return R.fotos[Math.floor(Math.random() * R.fotos.length)];
  }

  atualizar(dt: number): void {
    const j = this.jogo;
    if (this.luzHorizonte) {
      const on = Math.sin(j.tempo * 2.2) > 0.2 || Math.sin(j.tempo * 7.1) > 0.92;
      this.luzHorizonte.malha.isVisible = on;
      this.luzHorizonte.luz.intensity = on ? 0.8 : 0;
    }
    const p = j.jogador.pes;
    // sermão na vigília, quando o jogador está na capela perto de Teodoro
    const teodoro = j.npcs.porId("teodoro");
    if (teodoro && j.turnos.turno === "vigilia" && j.areas.mundo === "vila" && teodoro.personagem && !teodoro.andando
      && Math.abs(teodoro.x - p.x) < 18) {
      this.relogioSermao -= dt;
      j.audio.laco("sermao", 0.55);
      if (this.relogioSermao <= 0) {
        this.relogioSermao = 5.5;
        const variante = S.variantes.find((v) => avaliar(v.se, j.estado)) ?? S.variantes[S.variantes.length - 1];
        const fala = variante.falas[this.indiceSermao++ % variante.falas.length];
        j.baloes.mostrar(() => teodoro.cabeca(), fala, 5, "sermao");
      }
    } else if (j.areas.mundo === "vila") {
      j.audio.laco("sermao", 0);
    }
    // rádio da Caravana cita outras cidades
    if (j.areas.mundo === "vila" && Math.abs(p.x - 5) < 9) {
      this.relogioRadio -= dt;
      if (this.relogioRadio <= 0) {
        this.relogioRadio = 14;
        j.baloes.mostrar(() => new Vector3(6.5, 1.6, 1.6), R.radio[Math.floor(Math.random() * R.radio.length)], 4.5, "fundo");
      }
    }
  }
}
