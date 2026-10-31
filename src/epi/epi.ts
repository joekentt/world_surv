import { CFG } from "../config";
import type { Jogo } from "../core/jogo";
import type { Medidores } from "../ui/medidores";
import { textos } from "../ui/textos";

const E = CFG.epi;
const T = CFG.tempestade;

export type FaseTempestade = "calma" | "aviso" | "ativa";

/**
 * Equipamento de proteção na superfície: filtro (tempo de ar) e integridade da roupa.
 * Com qualquer um zerado, a saúde cai sem parar; saúde zerada é a morte.
 */
export class SistemaEPI {
  filtro = 0;
  roupa = 0;
  saude: number = E.saudeMaxima;
  ativo = false;
  tempestade: FaseTempestade = "calma";
  private relogioTempestade = 0;
  private tempoNaSuperficie = 0;
  private direcaoVento = 1;
  private ultimoAlerta = 0;
  private tempoAlerta = 0;
  morto = false;
  /** Chamado quando a saúde chega a zero. */
  aoMorrer: (() => void) | null = null;

  constructor(private jogo: Jogo, private medidores: Medidores) {
    jogo.jogador.aoCairForte = (vy) => {
      if (!this.ativo) return;
      const excesso = vy - CFG.movimento.velocidadeQuedaDano;
      const dano = CFG.movimento.danoRoupaPorQueda * (1 + excesso / 6) * (jogo.estado.d.upgrades.roupaReforcada ? E.multiplicadorReforcada : 1);
      this.roupa = Math.max(0, this.roupa - dano);
      jogo.audio.tocar("dano", 0.8);
      jogo.camera.tremor = 0.35;
      medidores.piscarDano();
      jogo.hud.mensagemCurta(textos("epi.quedaRasgou"), 2.5);
    };
  }

  /** Coloca um filtro novo e repara a roupa (na eclusa, antes de subir). */
  equipar(): void {
    this.filtro = this.jogo.estado.capacidadeFiltro();
    this.roupa = this.jogo.estado.capacidadeRoupa();
    this.saude = E.saudeMaxima;
    this.morto = false;
  }

  entrarSuperficie(): void {
    this.ativo = true;
    this.tempoNaSuperficie = 0;
    this.tempestade = "calma";
    this.relogioTempestade = T.primeiraNaoAntesDe + Math.random() * (T.intervaloMax - T.intervaloMin);
  }

  sairSuperficie(): void {
    this.ativo = false;
    this.tempestade = "calma";
    this.jogo.jogador.empurrao = 0;
    this.jogo.iluminacao.poeiraExtra = 0;
    this.jogo.audio.laco("tempestade", 0);
    this.jogo.audio.laco("respiracao", 0);
  }

  /** Força uma tempestade (testes e eventos de roteiro). */
  forcarTempestade(): void {
    if (!this.ativo) return;
    this.relogioTempestade = 0.01;
    this.tempestade = "calma";
  }

  get fracaoFiltro(): number {
    return this.filtro / this.jogo.estado.capacidadeFiltro();
  }

  get fracaoRoupa(): number {
    return this.roupa / this.jogo.estado.capacidadeRoupa();
  }

  atualizar(dt: number): void {
    const j = this.jogo;
    if (!this.ativo || this.morto) {
      if (!this.ativo && this.saude < E.saudeMaxima) this.saude = Math.min(E.saudeMaxima, this.saude + E.regeneracaoSaude * dt);
      this.medidores.atualizarEPI(this, false);
      return;
    }
    this.tempoNaSuperficie += dt;
    this.atualizarTempestade(dt);
    const multF = this.tempestade === "ativa" ? T.multiplicadorFiltro : 1;
    const multR = (this.tempestade === "ativa" ? T.multiplicadorRoupa : 1) * (j.estado.d.upgrades.roupaReforcada ? E.multiplicadorReforcada : 1);
    this.filtro = Math.max(0, this.filtro - E.drenoFiltroPorSegundo * multF * dt);
    this.roupa = Math.max(0, this.roupa - E.drenoRoupaPoeira * multR * dt);
    const semProtecao = this.filtro <= 0 || this.roupa <= 0;
    if (semProtecao) {
      this.saude = Math.max(0, this.saude - E.danoSemProtecao * dt);
      if (j.tempo - this.ultimoAlerta > 0.9) {
        this.ultimoAlerta = j.tempo;
        j.audio.tocar("alerta_grave", 0.6);
        j.jogador.personagem.tem("tossir");
      }
      this.medidores.piscarDano();
    }
    // alertas sonoros de filtro baixo, cada vez mais frequentes
    const f = this.fracaoFiltro;
    if (f < E.alertaFiltro && f > 0) {
      const intervalo = f < E.criticoFiltro ? 0.8 : 2.4;
      this.tempoAlerta -= dt;
      if (this.tempoAlerta <= 0) {
        this.tempoAlerta = intervalo;
        j.audio.tocar("alerta", f < E.criticoFiltro ? 0.7 : 0.45);
      }
    }
    j.audio.laco("respiracao", 0.25 + (1 - f) * 0.45);
    j.jogador.fatorVelocidade = j.estado.pesoTotal() > j.estado.pesoMaximo() * 0.75 ? 0.85 : 1;
    if (this.saude <= 0 && !this.morto) {
      this.morto = true;
      this.aoMorrer?.();
    }
    this.medidores.atualizarEPI(this, true);
  }

  private atualizarTempestade(dt: number): void {
    const j = this.jogo;
    this.relogioTempestade -= dt;
    if (this.tempestade === "calma" && this.relogioTempestade <= 0) {
      this.tempestade = "aviso";
      this.relogioTempestade = T.aviso;
      this.direcaoVento = Math.random() < 0.5 ? -1 : 1;
      j.audio.tocar("sirene", 0.9);
      j.hud.mensagemCurta(textos("epi.tempestadeAviso"), T.aviso);
      this.medidores.alertaTempestade(true);
    } else if (this.tempestade === "aviso" && this.relogioTempestade <= 0) {
      this.tempestade = "ativa";
      this.relogioTempestade = T.duracao;
      j.camera.tremor = 0.6;
    } else if (this.tempestade === "ativa" && this.relogioTempestade <= 0) {
      this.tempestade = "calma";
      this.relogioTempestade = T.intervaloMin + Math.random() * (T.intervaloMax - T.intervaloMin);
      this.medidores.alertaTempestade(false);
      j.hud.mensagemCurta(textos("epi.tempestadePassou"), 3);
    }
    const intensidadeAlvo = this.tempestade === "ativa" ? 1 : this.tempestade === "aviso" ? 0.25 : 0;
    const p = j.iluminacao.poeiraExtra;
    j.iluminacao.poeiraExtra = p + (intensidadeAlvo - p) * Math.min(1, dt * 0.8);
    j.jogador.empurrao = this.tempestade === "ativa" ? this.direcaoVento * T.empurraoVento : 0;
    j.audio.laco("tempestade", j.iluminacao.poeiraExtra * 0.9);
    j.audio.laco("vento", 0.35 * (1 - j.iluminacao.poeiraExtra));
  }
}
