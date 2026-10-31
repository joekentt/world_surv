import { HavokPlugin, Vector3, type Scene } from "@babylonjs/core";
import HavokPhysics from "@babylonjs/havok";

let instancia: unknown = null;

/** Inicializa o Havok (WASM) uma única vez e liga a física na cena. */
export async function ligarFisica(cena: Scene, gravidade = -22): Promise<HavokPlugin> {
  if (!instancia) instancia = await HavokPhysics();
  const plugin = new HavokPlugin(true, instancia);
  cena.enablePhysics(new Vector3(0, gravidade, 0), plugin);
  return plugin;
}
