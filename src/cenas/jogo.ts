import type { Scene } from "@babylonjs/core";
import { Jogo } from "../core/jogo";
import type { Motor } from "../core/motor";
import { carregarJogo } from "../save/save";
import { mostrarTitulo } from "../ui/titulo";

export async function cenaJogo(motor: Motor): Promise<Scene> {
  const params = new URLSearchParams(location.search);
  const jogo = new Jogo(motor);
  const areaParam = params.get("area");
  const cena = await jogo.iniciar(areaParam ?? "praca", params.get("entrada") ?? "inicio");
  if (areaParam) {
    // modo de teste/desenvolvimento: entra direto na área pedida
    if (params.get("novo") === "1") void jogo.novoJogo();
    return cena;
  }
  jogo.travarParaDialogo(true);
  const temSave = !!(await carregarJogo());
  void mostrarTitulo(temSave).then(async (escolha) => {
    jogo.travarParaDialogo(false);
    if (escolha === "continuar" && (await jogo.carregarSave())) return;
    await jogo.novoJogo();
  });
  return cena;
}
