import type { Scene } from "@babylonjs/core";
import type { Motor } from "../core/motor";
import { cenaTeste } from "./teste";

export async function cenaJogo(motor: Motor): Promise<Scene> {
  return cenaTeste(motor);
}
