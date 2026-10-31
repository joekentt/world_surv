import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  optimizeDeps: { exclude: ["@babylonjs/havok"] },
  server: { port: 5173, strictPort: true },
  build: { target: "es2022", chunkSizeWarningLimit: 6000, assetsInlineLimit: 0 },
});
