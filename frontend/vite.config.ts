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
    // En dev, l'app tourne sur :5173 mais le backend est Django (:8000) :
    // les fetch relatifs (/chat/..., /accounts/...) sont transmis à Django
    // (session et CSRF conservés). Nécessite dans .env côté Django :
    // DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173
    proxy: {
      "/chat": "http://127.0.0.1:8000",
      "/accounts": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
    },
  },
});
