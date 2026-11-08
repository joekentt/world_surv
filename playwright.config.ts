import { defineConfig } from "@playwright/test";

/** Porta do servidor de testes; mude com PORTA_TESTE para rodar duas cópias do projeto ao mesmo tempo. */
const porta = Number(process.env.PORTA_TESTE ?? 5173);

/**
 * Chromium sem GPU: o WebGPU roda pelo adaptador de software (SwiftShader/Vulkan) e o
 * WebGL2 pelo ANGLE + SwiftShader. Os fps medidos aqui servem para comparar versões, não
 * para validar os 60 fps em notebook, que exigem GPU real (ver docs/progresso.md).
 */
export default defineConfig({
  testDir: "tests",
  timeout: 180_000,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${porta}`,
    viewport: { width: 1280, height: 720 },
    launchOptions: {
      args: [
        "--enable-unsafe-webgpu",
        "--enable-features=Vulkan",
        "--use-vulkan=swiftshader",
        "--disable-vulkan-surface",
        "--use-angle=swiftshader",
        "--use-webgpu-adapter=swiftshader",
        "--ignore-gpu-blocklist",
        "--enable-gpu-rasterization",
      ],
    },
  },
  webServer: { command: `npx vite --port ${porta} --strictPort`, url: `http://localhost:${porta}`, reuseExistingServer: true, timeout: 60_000 },
});
