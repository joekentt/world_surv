import { criarMotor } from "./core/motor";
import { cenaTeste } from "./cenas/teste";

declare global {
  interface Window {
    __vc: { pronto: boolean; renderizador: string; fps: number; erro?: string; [k: string]: unknown };
  }
}

async function iniciar(): Promise<void> {
  window.__vc = { pronto: false, renderizador: "", fps: 0 };
  const canvas = document.getElementById("jogo") as HTMLCanvasElement;
  const motor = await criarMotor(canvas);
  window.__vc.renderizador = motor.renderizador;
  if (motor.renderizador === "webgpu") {
    // Se o dispositivo WebGPU cair e não voltar, recarrega no fallback WebGL2.
    let perdido = 0;
    motor.engine.onContextLostObservable.add(() => { perdido = performance.now(); });
    motor.engine.onContextRestoredObservable.add(() => { perdido = 0; });
    setInterval(() => {
      if (perdido && performance.now() - perdido > 3000) {
        const u = new URL(location.href);
        u.searchParams.set("render", "webgl2");
        location.replace(u.toString());
      }
    }, 1000);
  }
  const selo = document.createElement("div");
  selo.id = "selo-render";
  document.body.appendChild(selo);
  const params = new URLSearchParams(location.search);
  const cena = params.get("cena") === "teste" ? await cenaTeste(motor) : await (await import("./cenas/jogo")).cenaJogo(motor);
  let acumulado = 0;
  motor.engine.runRenderLoop(() => {
    cena.render();
    acumulado += motor.engine.getDeltaTime();
    if (acumulado > 500) {
      acumulado = 0;
      window.__vc.fps = motor.engine.getFps();
      selo.textContent = `${motor.renderizador.toUpperCase()} · ${window.__vc.fps.toFixed(0)} fps`;
    }
  });
  window.addEventListener("resize", () => motor.engine.resize());
  window.__vc.pronto = true;
}

iniciar().catch((e) => {
  console.error(e);
  window.__vc.erro = String(e?.stack ?? e);
  document.body.insertAdjacentHTML("beforeend", `<pre class="erro-fatal">${String(e)}</pre>`);
});
