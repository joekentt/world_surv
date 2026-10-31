import {
  ArcRotateCamera, Color3, Color4, DirectionalLight, HemisphericLight, MeshBuilder, PhysicsAggregate,
  PhysicsShapeType, Scene, ShadowGenerator, StandardMaterial, Vector3,
} from "@babylonjs/core";
import { BibliotecaAnimacoes, Carregador } from "../core/carregador";
import { ligarFisica } from "../core/fisica";
import type { Motor } from "../core/motor";
import { Personagem } from "../core/personagem";

/** Cena de validação da fase 0: renderizador, Havok, GLB do Blender e personagem animado. */
export async function cenaTeste(motor: Motor): Promise<Scene> {
  const cena = new Scene(motor.engine);
  cena.clearColor = new Color4(0.12, 0.11, 0.1, 1);
  const cam = new ArcRotateCamera("cam", -Math.PI / 2, Math.PI / 2.3, 7, new Vector3(0, 1.1, 0), cena);
  cam.attachControl(true);
  new HemisphericLight("ceu", new Vector3(0, 1, -0.3), cena).intensity = 0.5;
  const sol = new DirectionalLight("sol", new Vector3(-0.5, -1, 0.6), cena);
  sol.position = new Vector3(5, 10, -6);
  sol.intensity = 2.2;
  const sombras = new ShadowGenerator(motor.qualidade === "alta" ? 2048 : 1024, sol);
  sombras.useBlurExponentialShadowMap = true;

  await ligarFisica(cena);
  const chao = MeshBuilder.CreateBox("chao", { width: 20, height: 0.5, depth: 8 }, cena);
  chao.position.y = -0.25;
  chao.receiveShadows = true;
  const mat = new StandardMaterial("chao", cena);
  mat.diffuseColor = new Color3(0.35, 0.33, 0.3);
  chao.material = mat;
  new PhysicsAggregate(chao, PhysicsShapeType.BOX, { mass: 0 }, cena);
  for (let i = 0; i < 6; i++) {
    const caixa = MeshBuilder.CreateBox(`caixa${i}`, { size: 0.4 }, cena);
    caixa.position = new Vector3(-3 + i * 0.3, 3 + i * 0.8, 1.5);
    sombras.addShadowCaster(caixa);
    new PhysicsAggregate(caixa, PhysicsShapeType.BOX, { mass: 1, restitution: 0.3 }, cena);
  }

  const carregador = new Carregador(cena);
  const parede = await carregador.carregar("teste/parede.glb");
  const inst = parede.instantiateModelsToScene((n) => n);
  inst.rootNodes[0].getChildMeshes().forEach((m) => { m.receiveShadows = true; });
  (inst.rootNodes[0] as unknown as { position: Vector3 }).position.z = 2.5;

  const bib = await BibliotecaAnimacoes.carregar(carregador);
  const ids: [string, string, number][] = [["protagonista", "andar", 0], ["mirela", "parado", -1.6], ["samira", "conversar", 1.6]];
  const pers: Personagem[] = [];
  for (const [id, acao, x] of ids) {
    const p = await Personagem.criar(cena, carregador, bib, id);
    p.raiz.position.x = x;
    p.tocar(acao);
    p.malhas.forEach((m) => sombras.addShadowCaster(m));
    pers.push(p);
  }
  pers[0].mostrar("_epi", false);
  cena.onBeforeRenderObservable.add(() => {
    const dt = cena.getEngine().getDeltaTime() / 1000;
    pers.forEach((p) => p.atualizar(dt));
  });
  return cena;
}
