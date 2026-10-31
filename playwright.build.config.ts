import base from "./playwright.config";
import { defineConfig } from "@playwright/test";

/** Mesmos testes de navegador, contra o build de produção (vite preview na porta 4173). */
export default defineConfig({
  ...base,
  testMatch: /fase7\.spec\.ts/,
  use: { ...base.use, baseURL: "http://localhost:4173" },
  webServer: { command: "npm run build && npx vite preview --port 4173 --strictPort", url: "http://localhost:4173", reuseExistingServer: false, timeout: 180_000 },
});
