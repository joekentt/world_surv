import { Vector3, type AbstractMesh, type Mesh } from "@babylonjs/core";
import conversasJson from "../../content/dialogos/conversas_fundo.json";
import { CFG } from "../config";
import type { Jogo } from "../core/jogo";
import { Personagem } from "../core/personagem";
import { avaliar, type Condicao } from "../quests/condicoes";
import type { Baloes } from "../ui/baloes";
import { AREAS } from "../world/areas";
import type { Turno, TurnosDeLuz } from "../world/turnos";
import type { Navegacao } from "./navegacao";

export interface PassoRotina {
  atividade: "trabalho" | "fila" | "culto" | "descanso";
  area: string;
  x: number;
  z?: number;
  acao: string;
  olhar?: "camera" | "fundo" | "esquerda" | "direita";
  entrarEmCasa?: boolean;
}

export interface NpcDef {
  id: string;
  nome: string;
  titulo?: string;
  nomeado: boolean;
  faccao: string;
  aparencia: { idade_anos: number };
  rotina: Record<Turno, PassoRotina>;
}

const arquivos = import.meta.glob("../../content/npcs/*.json", { eager: true, import: "default" }) as Record<string, NpcDef>;
export const NPCS: NpcDef[] = Object.values(arquivos).filter((n) => n.id !== "protagonista" && n.rotina);

type Conversa = { id: string; falas: [string, string][]; se?: Condicao };
type Reacao = { texto: string; se?: Condicao };
const CONVERSAS = (conversasJson as unknown as { conversas: Conversa[] }).conversas;
const REACOES = (conversasJson as unknown as { reacoes: Reacao[] }).reacoes;

const ANGULOS: Record<string, number> = {
  camera: Math.PI, fundo: 0, esquerda: -Math.PI / 2 - 0.45, direita: Math.PI / 2 + 0.45,
};
const FIGURANTES = ["moradora_galerias", "varredor", "idoso_banco", "contrabandista", "fiel_vigilia_2", "cozinheira"];
const FILA_X = -59.4;
const FILA_PASSO = 0.85;

function mundoDe(area: string): string {
  return AREAS[area]?.mundo ?? "vila";
}

export class Npc {
  x: number;
  z: number;
  mundo: string;
  caminho: Vector3[] = [];
  passo: PassoRotina;
  emCasa = false;
  personagem: Personagem | null = null;
  carregando = false;
  proximaReacao = 0;
  reagindoAte = 0;
  ocupadoAte = 0;
  vagaFila = -1;
  readonly crianca: boolean;

  constructor(readonly def: NpcDef, turno: Turno) {
    this.passo = def.rotina[turno];
    this.mundo = mundoDe(this.passo.area);
    this.x = this.passo.x;
    this.z = this.passo.z ?? 1.5;
    this.emCasa = !!this.passo.entrarEmCasa;
    this.crianca = def.aparencia.idade_anos < 14;
  }

  get andando(): boolean {
    return this.caminho.length > 0;
  }

  get velocidade(): number {
    return CFG.npc.velocidadeAndar * (this.crianca ? 1.3 : 1) * (this.def.aparencia.idade_anos > 65 ? 0.8 : 1);
  }

  cabeca(): Vector3 {
    return new Vector3(this.x, this.crianca ? 1.45 : 1.95, this.z);
  }
}

/**
 * Moradores da vila: rotina por turno de luz, caminho pela malha do Recast, ação no posto,
 * reação ao jogador e conversas de fundo. A simulação roda para todos; o modelo 3D só existe
 * perto do jogador, com animação pausada longe da câmera e nível de detalhe por distância.
 */
export class GerenciadorNpcs {
  npcs: Npc[];
  private relogioConversa = 4;
  private usadas = new Map<string, number>();
  private figurantes: Personagem[] = [];
  private carregandoFigurantes = false;
  /** Chamado ao interagir com um NPC nomeado. */
  aoFalar: ((npc: Npc) => void) | null = null;

  constructor(private jogo: Jogo, private turnos: TurnosDeLuz, private nav: Navegacao, private baloes: Baloes) {
    this.npcs = NPCS.map((d) => new Npc(d, turnos.turno));
    turnos.aoMudar = (t) => this.mudarTurno(t);
    this.distribuirFila();
    for (const n of this.npcs) if (n.passo.atividade === "fila") this.posicionarNaFila(n, true);
    for (const n of this.npcs.filter((n) => n.def.nomeado)) {
      const ref = n;
      const inter = {
        id: `npc:${n.def.id}`, x: n.x, y: 0, raio: 1.6, prioridade: 3,
        rotulo: () => `Falar com ${ref.def.titulo ? ref.def.nome : ref.def.nome}`,
        ativo: () => !ref.emCasa && ref.mundo === this.jogo.areas.mundo && !!ref.personagem,
        acao: () => this.aoFalar?.(ref),
      };
      (n as unknown as { _inter: typeof inter })._inter = inter;
      jogo.interacao.adicionar(inter);
    }
  }

  porId(id: string): Npc | undefined {
    return this.npcs.find((n) => n.def.id === id);
  }

  private distribuirFila(): void {
    let vaga = 0;
    for (const n of this.npcs) n.vagaFila = n.passo.atividade === "fila" ? vaga++ : -1;
  }

  private posicionarNaFila(n: Npc, imediato = false): void {
    const x = FILA_X + n.vagaFila * FILA_PASSO;
    if (imediato) {
      n.x = x;
      n.z = 1.0;
    }
    n.passo = { ...n.passo, x, z: 1.0, olhar: "esquerda" };
  }

  mudarTurno(t: Turno): void {
    for (const n of this.npcs) {
      n.passo = n.def.rotina[t];
      const novoMundo = mundoDe(n.passo.area);
      if (novoMundo !== n.mundo) {
        n.mundo = novoMundo;
        n.x = n.passo.x;
        n.z = n.passo.z ?? 1.5;
      }
    }
    this.distribuirFila();
    for (const n of this.npcs) {
      if (n.passo.atividade === "fila") this.posicionarNaFila(n);
      const destZ = n.passo.z ?? 1.5;
      if (n.emCasa) {
        n.emCasa = false;
        n.z = Math.min(n.z, 4.0);
      }
      const nav = n.mundo === "vila" ? this.nav : null;
      n.caminho = nav ? nav.caminho(n.x, n.z, n.passo.x, destZ) : [new Vector3(n.passo.x, 0, destZ)];
    }
  }

  /** Força o turno seguinte (testes). */
  pularTurno(): void {
    this.turnos.avancar();
  }

  private async garantirModelo(n: Npc): Promise<void> {
    if (n.personagem || n.carregando) return;
    n.carregando = true;
    try {
      const p = await Personagem.criar(this.jogo.cena, this.jogo.carregador, this.jogo.biblioteca, n.def.id, `npc_${n.def.id}`);
      const malha = p.malhas.find((m) => m.name.endsWith("_malha")) as Mesh | undefined;
      const lod = p.malhas.find((m) => m.name.endsWith("_malha_lod1")) as Mesh | undefined;
      if (malha && lod) {
        malha.addLODLevel(CFG.npc.distanciaLod, lod);
      }
      p.malhas.forEach((m: AbstractMesh) => { m.receiveShadows = true; });
      n.personagem = p;
    } finally {
      n.carregando = false;
    }
  }

  atualizar(dt: number): void {
    const j = this.jogo;
    const jp = j.jogador.pes;
    const mundoAtual = j.areas.mundo;
    for (const n of this.npcs) {
      this.mover(n, dt);
      const inter = (n as unknown as { _inter?: { x: number } })._inter;
      if (inter) inter.x = n.x;
      const perto = n.mundo === mundoAtual && Math.abs(n.x - jp.x) < 48;
      if (perto && !n.personagem) void this.garantirModelo(n);
      if (!n.personagem) continue;
      const p = n.personagem;
      const visivel = perto && !n.emCasa;
      p.definirVisivel(visivel);
      if (!visivel) {
        p.definirPausa(true);
        continue;
      }
      p.raiz.position.set(n.x, 0, n.z);
      const longe = Math.abs(n.x - jp.x) > CFG.npc.distanciaAnimacaoReduzida;
      p.definirPausa(longe);
      if (longe) continue;
      this.reagir(n, jp.x, jp.y);
      this.animar(n, dt);
    }
    this.conversasDeFundo(dt, jp.x);
    this.atualizarFigurantes();
  }

  private mover(n: Npc, dt: number): void {
    if (!n.caminho.length) return;
    let resto = n.velocidade * dt;
    while (resto > 0 && n.caminho.length) {
      const alvo = n.caminho[0];
      const dx = alvo.x - n.x;
      const dz = alvo.z - n.z;
      const d = Math.hypot(dx, dz);
      if (d <= resto) {
        n.x = alvo.x;
        n.z = alvo.z;
        n.caminho.shift();
        resto -= d;
      } else {
        n.x += (dx / d) * resto;
        n.z += (dz / d) * resto;
        resto = 0;
      }
      if (Math.abs(dx) > 0.05) n.personagem?.virar(dx);
    }
    if (!n.caminho.length && n.passo.entrarEmCasa) n.emCasa = true;
  }

  private animar(n: Npc, dt: number): void {
    const p = n.personagem!;
    const agora = this.jogo.tempo;
    if (n.andando) {
      p.anguloForcado = null;
      p.tocar("andar", { velocidade: n.velocidade / 1.35, transicao: 0.3 });
    } else if (agora < n.reagindoAte) {
      // mantém a reação (aceno) até acabar
    } else {
      p.anguloForcado = ANGULOS[n.passo.olhar ?? "camera"] ?? Math.PI;
      const acao = p.tem(n.passo.acao) ? n.passo.acao : "parado";
      p.tocar(n.passo.atividade === "fila" && Math.sin(agora * 0.3 + n.x) > 0.97 ? "tossir" : acao, { transicao: 0.4 });
    }
    p.atualizar(dt);
  }

  private reagir(n: Npc, px: number, py: number): void {
    const j = this.jogo;
    const agora = j.tempo;
    const dx = px - n.x;
    if (n.andando || n.emCasa || agora < n.proximaReacao || Math.abs(dx) > CFG.npc.raioReacao || Math.abs(py) > 1.5) return;
    if (j.interacao.bloqueado) return;
    n.proximaReacao = agora + 45 + Math.random() * 30;
    n.reagindoAte = agora + 2.4;
    const p = n.personagem!;
    p.anguloForcado = dx > 0 ? Math.PI / 2 + 0.6 : -Math.PI / 2 - 0.6;
    p.tocar("acenar", { transicao: 0.25 });
    const opcoes = REACOES.filter((r) => avaliar(r.se, j.estado, { crianca: n.crianca }) && (r.se?.criancas === undefined || n.crianca));
    const especificas = opcoes.filter((r) => r.se && Object.keys(r.se).length > 0);
    const lista = especificas.length && Math.random() < 0.7 ? especificas : opcoes;
    const r = lista[Math.floor(Math.random() * lista.length)];
    if (r) this.baloes.mostrar(() => n.cabeca(), r.texto, 2.6, "reacao");
  }

  private conversasDeFundo(dt: number, px: number): void {
    this.relogioConversa -= dt;
    if (this.relogioConversa > 0) return;
    this.relogioConversa = CFG.npc.intervaloConversa * (0.7 + Math.random() * 0.6);
    const livres = this.npcs.filter((n) => n.personagem && !n.emCasa && !n.andando && n.mundo === this.jogo.areas.mundo
      && Math.abs(n.x - px) < CFG.npc.raioConversaFundo + 4 && this.jogo.tempo > n.ocupadoAte);
    for (let i = 0; i < livres.length; i++) {
      for (let k = i + 1; k < livres.length; k++) {
        const a = livres[i], b = livres[k];
        if (Math.abs(a.x - b.x) > 4.5 || Math.abs(a.z - b.z) > 3) continue;
        const possiveis = CONVERSAS.filter((c) => avaliar(c.se, this.jogo.estado) && (this.usadas.get(c.id) ?? -999) < this.jogo.tempo - 240);
        if (!possiveis.length) return;
        const c = possiveis[Math.floor(Math.random() * possiveis.length)];
        this.usadas.set(c.id, this.jogo.tempo);
        c.falas.forEach(([quem, texto], idx) => {
          setTimeout(() => this.baloes.mostrar(() => (quem === "a" ? a : b).cabeca(), texto, 3.0), idx * 3200);
        });
        a.ocupadoAte = b.ocupadoAte = this.jogo.tempo + c.falas.length * 3.2;
        return;
      }
    }
  }

  /** A fila das cotas cresce conforme o roteiro avança: figurantes extras no fim da fila. */
  quantidadeFigurantes(): number {
    const e = this.jogo.estado;
    const concluidas = Object.values(e.d.missoes).filter((m) => m.estado === "concluida").length;
    return Math.min(FIGURANTES.length, 1 + concluidas + Math.floor(e.d.subidas / 2));
  }

  private atualizarFigurantes(): void {
    const j = this.jogo;
    const naVila = j.areas.mundo === "vila" && Math.abs(j.jogador.pes.x - FILA_X) < 50;
    const alvo = naVila ? this.quantidadeFigurantes() : 0;
    while (this.figurantes.length > alvo) this.figurantes.pop()!.dispose();
    if (this.figurantes.length < alvo && !this.carregandoFigurantes) {
      this.carregandoFigurantes = true;
      const i = this.figurantes.length;
      void Personagem.criar(j.cena, j.carregador, j.biblioteca, FIGURANTES[i], `figurante_${i}`).then((p) => {
        this.figurantes.push(p);
        this.carregandoFigurantes = false;
      }).catch(() => { this.carregandoFigurantes = false; });
    }
    const naFila = this.npcs.filter((n) => n.passo.atividade === "fila").length;
    this.figurantes.forEach((p, i) => {
      p.raiz.position.set(FILA_X + (naFila + i) * FILA_PASSO, 0, 1.0 + (i % 2) * 0.25);
      p.anguloForcado = ANGULOS.esquerda;
      p.tocar(Math.sin(j.tempo * 0.4 + i * 2) > 0.95 ? "tossir" : "parado", { transicao: 0.4 });
      p.atualizar(1 / 60);
    });
  }

  contagem(): { simulados: number; visiveis: number; modelos: number } {
    return {
      simulados: this.npcs.length,
      visiveis: this.npcs.filter((n) => n.personagem?.raiz.isEnabled()).length + this.figurantes.length,
      modelos: this.npcs.filter((n) => n.personagem).length,
    };
  }
}
