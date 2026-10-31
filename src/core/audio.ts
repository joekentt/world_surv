import { CreateAudioEngineAsync, CreateSoundAsync, type AudioEngineV2, type StaticSound } from "@babylonjs/core";

const BASE = import.meta.env.BASE_URL + "assets/audio/";

const LACOS = ["vento", "tempestade", "goteira", "ventilador", "zumbido_fluor", "multidao", "sermao", "respiracao",
  "chuveiro", "radio", "ambiente_vila", "ambiente_superficie"];
const EFEITOS = ["sirene", "passo_concreto", "passo_areia", "passo_metal", "pulo", "aterrissar", "coleta", "alerta",
  "alerta_grave", "dano", "eclusa", "morte", "moedas", "clique", "porta"];

interface Emissor { som: string; x: number; y: number; raio: number; volume: number; }

/**
 * Áudio sobre o AudioEngineV2 do Babylon. Laços ambientes têm volume suavizado; emissores
 * posicionados (bomba, sermão, mercado) somam volume conforme a distância do jogador.
 */
export class Audio {
  private motor: AudioEngineV2 | null = null;
  private sons = new Map<string, StaticSound>();
  private alvoLaco = new Map<string, number>();
  private atualLaco = new Map<string, number>();
  private emissores: Emissor[] = [];
  volumeGeral = 0.8;

  async iniciar(): Promise<void> {
    try {
      this.motor = await CreateAudioEngineAsync({ volume: this.volumeGeral, resumeOnInteraction: true } as never);
    } catch (e) {
      console.warn("[audio] sem áudio", e);
      return;
    }
    const destravar = () => { void this.motor?.unlockAsync(); };
    window.addEventListener("keydown", destravar, { once: true });
    window.addEventListener("pointerdown", destravar, { once: true });
    await Promise.all([
      ...LACOS.map((n) => this.carregar(n, true)),
      ...EFEITOS.map((n) => this.carregar(n, false)),
    ]);
  }

  private async carregar(nome: string, laco: boolean): Promise<void> {
    if (!this.motor) return;
    try {
      const s = await CreateSoundAsync(nome, BASE + nome + ".wav", { loop: laco, volume: 0, maxInstances: laco ? 1 : 4 } as never, this.motor);
      this.sons.set(nome, s);
      if (laco) {
        this.atualLaco.set(nome, 0);
      }
    } catch (e) {
      console.warn(`[audio] falha ao carregar ${nome}`, e);
    }
  }

  definirVolumeGeral(v: number): void {
    this.volumeGeral = v;
    if (this.motor) this.motor.volume = v;
  }

  tocar(nome: string, volume = 1, taxa = 1): void {
    const s = this.sons.get(nome);
    if (!s) return;
    s.playbackRate = taxa;
    s.play({ volume } as never);
  }

  /** Define o volume-alvo de um laço ambiente (0 desliga com fade). */
  laco(nome: string, volume: number): void {
    this.alvoLaco.set(nome, volume);
  }

  definirEmissores(lista: Emissor[]): void {
    this.emissores = lista;
  }

  atualizar(dt: number, x: number, y: number): void {
    const alvos = new Map(this.alvoLaco);
    for (const e of this.emissores) {
      const d = Math.hypot(e.x - x, (e.y - y) * 1.5);
      const v = e.volume * Math.max(0, 1 - d / e.raio) ** 1.5;
      alvos.set(e.som, Math.max(alvos.get(e.som) ?? 0, v));
    }
    for (const [nome, atual] of this.atualLaco) {
      const alvo = alvos.get(nome) ?? 0;
      const novo = atual + (alvo - atual) * Math.min(1, dt * 2.5);
      this.atualLaco.set(nome, novo);
      const s = this.sons.get(nome);
      if (!s) continue;
      const tocando = (s as unknown as { state: number }).state === 3 || (s as unknown as { _tocando?: boolean })._tocando;
      if (novo > 0.005 && !tocando) {
        s.play({ volume: novo } as never);
        (s as unknown as { _tocando?: boolean })._tocando = true;
      } else if (novo <= 0.005 && tocando && alvo === 0) {
        s.stop();
        (s as unknown as { _tocando?: boolean })._tocando = false;
      } else if (tocando) {
        s.volume = novo;
      }
    }
  }
}
