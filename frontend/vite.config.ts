import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    // Sortie dans les statiques Django, résolues ensuite via le manifest
    // (chatbot/templatetags/vite.py) : jamais de nom de fichier en dur.
    outDir: "../static/chatbot/app",
    emptyOutDir: true,
    manifest: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    // Obligatoire : sans origin, Django bloquerait les assets du mode dev.
    origin: "http://localhost:5173",
  },
});
