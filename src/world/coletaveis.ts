import { TransformNode, type InstancedMesh, type Scene } from "@babylonjs/core";
import type { Jogo } from "../core/jogo";
import { nomeItem, pesoItem } from "../economy/itens";
import { textos } from "../ui/textos";
import type { AreaCarregada } from "./construtor";
import { fontesDoKit } from "./construtor";

const MODELO: Record<string, string> = {
  sucata: "item_sucata", componente: "item_componente", vidro: "item_vidro",
};

interface Ativo { id: string; no: TransformNode; base: number; }

/**
 * Itens no chão. Na superfície, os recursos voltam a cada subida (a poeira descobre sucata
 * nova); fora dela e para itens de missão, o que foi pego some para sempre.
 */
export class Coletaveis {
  private ativos = new Map<string, Ativo>();
  nestaSubida = new Set<string>();

  constructor(private jogo: Jogo, private cena: Scene) {}

  novaSubida(): void {
    this.nestaSubida.clear();
  }

  async aoCarregar(a: AreaCarregada): Promise<void> {
    const fontes = await fontesDoKit(this.jogo.carregador, "comum");
    for (const c of a.def.coletaveis ?? []) {
      if (this.jaPego(c.id, a.def.superficie)) continue;
      const no = new TransformNode(`coletavel_${c.id}`, this.cena);
      no.parent = a.raiz;
      no.position.set(c.x, c.y + 0.05, 0.35);
      for (const fonte of fontes.get(MODELO[c.item] ?? "item_sucata") ?? []) {
        const inst: InstancedMesh = fonte.createInstance(`${c.id}_malha`);
        inst.parent = no;
        inst.scaling.setAll(1.6);
      }
      this.ativos.set(c.id, { id: c.id, no, base: c.y + 0.05 });
      const superficie = !!a.def.superficie;
      this.jogo.interacao.adicionar({
        id: `${a.def.id}:coleta:${c.id}`, x: c.x, y: c.y, raio: 1.2, prioridade: 2,
        rotulo: () => textos("coleta.rotulo", { item: nomeItem(c.item) }),
        ativo: () => this.ativos.has(c.id),
        acao: () => this.pegar(c.id, c.item, c.qtd ?? 1, superficie),
      });
    }
  }

  aoDescarregar(a: AreaCarregada): void {
    for (const c of a.def.coletaveis ?? []) this.ativos.delete(c.id);
  }

  private jaPego(id: string, superficie?: boolean): boolean {
    return superficie ? this.nestaSubida.has(id) : this.jogo.estado.d.coletados.includes(id);
  }

  pegar(id: string, item: string, qtd: number, superficie: boolean): void {
    const j = this.jogo;
    if (!j.estado.cabe(item, qtd)) {
      j.hud.mensagemCurta(textos("coleta.mochilaCheia"), 2.5);
      j.audio.tocar("alerta", 0.4);
      return;
    }
    j.estado.dar(item, qtd);
    if (superficie) this.nestaSubida.add(id);
    else j.estado.d.coletados.push(id);
    const a = this.ativos.get(id);
    a?.no.dispose();
    this.ativos.delete(id);
    j.audio.tocar("coleta", 0.6);
    j.jogador.personagem.tocar("interagir", { loop: false, transicao: 0.1 });
    j.hud.mensagemCurta(textos("coleta.pegou", { item: nomeItem(item, qtd), peso: (pesoItem(item) * qtd).toFixed(1) }), 1.6);
    j.estado.avisar(`coletou:${item}`);
  }

  atualizar(dt: number): void {
    const t = this.jogo.tempo;
    for (const a of this.ativos.values()) {
      if (a.no.isDisposed()) continue;
      a.no.rotation.y += dt * 1.2;
      a.no.position.y = a.base + 0.08 + Math.sin(t * 2.4 + a.no.uniqueId) * 0.06;
    }
  }
}
