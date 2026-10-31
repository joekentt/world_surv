import { Engine, WebGPUEngine, type AbstractEngine } from "@babylonjs/core";

export type Renderizador = "webgpu" | "webgl2" | "webgl1";

export interface Motor {
  engine: AbstractEngine;
  renderizador: Renderizador;
  /** Perfil de qualidade: WebGPU recebe os efeitos completos, WebGL2 a versão simplificada. */
  qualidade: "alta" | "media";
}

/**
 * Cria o motor com WebGPU quando o navegador suporta e cai para WebGL2 caso contrário.
 * `?render=webgl2` força o fallback (usado nos testes).
 */
export async function criarMotor(canvas: HTMLCanvasElement): Promise<Motor> {
  const pedido = new URLSearchParams(location.search).get("render");
  if (pedido !== "webgl2" && pedido !== "webgl") {
    try {
      // Não usa WebGPUEngine.IsSupportedAsync: no Chromium com adaptador de software, pedir um
      // segundo adaptador invalida o primeiro. Basta tentar criar o motor e cair para WebGL2.
      if ("gpu" in navigator && navigator.gpu) {
        const engine = new WebGPUEngine(canvas, { antialias: true, stencil: true, adaptToDeviceRatio: false });
        await engine.initAsync();
        return { engine, renderizador: "webgpu", qualidade: "alta" };
      }
    } catch (erro) {
      console.warn("[motor] WebGPU indisponível, usando WebGL2", erro);
    }
  }
  const engine = new Engine(canvas, true, { stencil: true, preserveDrawingBuffer: true, powerPreference: "high-performance" }, false);
  const renderizador: Renderizador = engine.webGLVersion >= 2 ? "webgl2" : "webgl1";
  return { engine, renderizador, qualidade: "media" };
}
