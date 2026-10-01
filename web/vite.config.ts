import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api is proxied to FastAPI so the browser only talks to one origin (same as the nginx image).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.API_URL ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        loadPaths: ["node_modules/@uswds/uswds/packages"],
        quietDeps: true,
        silenceDeprecations: ["import", "global-builtin", "mixed-decls", "if-function"],
      },
    },
  },
});
