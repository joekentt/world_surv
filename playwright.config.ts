import { defineConfig } from "@playwright/test";

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
    baseURL: "http://localhost:5173",
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
  webServer: { command: "npx vite --port 5173 --strictPort", url: "http://localhost:5173", reuseExistingServer: true, timeout: 60_000 },
});
