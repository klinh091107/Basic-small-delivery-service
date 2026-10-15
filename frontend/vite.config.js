import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks: { phone: ["libphonenumber-js/max"] } } } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: { port: 4173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
