import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.XYFUSS_CONTROL_API_TARGET ?? "http://127.0.0.1:8765",
        changeOrigin: false,
      },
    },
  },
  preview: { host: "0.0.0.0", port: 4173, strictPort: true },
  build: { outDir: "dist", emptyOutDir: true },
});
