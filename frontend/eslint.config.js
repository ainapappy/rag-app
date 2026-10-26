import js from "@eslint/js";
import prettierConfig from "eslint-config-prettier";
import pluginVue from "eslint-plugin-vue";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["node_modules/", "dist/"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  prettierConfig,
  {
    files: ["**/*.vue"],
    languageOptions: {
      parserOptions: { parser: tseslint.parser },
    },
  },
  {
    rules: {
      // « Composer » est un nom de composant voulu (champ de saisie du chat).
      "vue/multi-word-component-names": ["error", { ignores: ["Composer"] }],
    },
  },
);
