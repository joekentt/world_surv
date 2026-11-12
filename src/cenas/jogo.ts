import type { Scene } from "@babylonjs/core";
import { INICIO_JOGO, Jogo } from "../core/jogo";
import type { Motor } from "../core/motor";
import { carregarJogo } from "../save/save";
import { mostrarTitulo } from "../ui/titulo";

export async function cenaJogo(motor: Motor): Promise<Scene> {
  const params = new URLSearchParams(location.search);
  const jogo = new Jogo(motor);
  const areaParam = params.get("area");
  // sem ?area: o menu abre sobre a praça da Vila Cisterna (mundo da revisão 2)
  const cena = await jogo.iniciar(areaParam ?? INICIO_JOGO.area, params.get("entrada") ?? INICIO_JOGO.entrada);
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
