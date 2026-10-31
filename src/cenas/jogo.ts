import type { Scene } from "@babylonjs/core";
import { Jogo } from "../core/jogo";
import type { Motor } from "../core/motor";

export async function cenaJogo(motor: Motor): Promise<Scene> {
  const params = new URLSearchParams(location.search);
  const jogo = new Jogo(motor);
  return jogo.iniciar(params.get("area") ?? "sala_teste", params.get("entrada") ?? "inicio");
}
