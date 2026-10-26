<script setup lang="ts">
import { ref } from "vue";

import { useAuth } from "@/composables/useAuth";

const { login } = useAuth();
const username = ref("");
const password = ref("");
const error = ref<string | null>(null);
const isSubmitting = ref(false);

async function submit(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }
  error.value = null;
  isSubmitting.value = true;
  try {
    await login(username.value.trim(), password.value);
  } catch {
    error.value = "Identifiants invalides.";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <section
    class="mx-auto mt-16 w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
  >
    <h1 class="text-xl font-semibold">Connexion</h1>
    <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
      Le chat est réservé aux utilisateurs connectés.
    </p>
    <form class="mt-4 space-y-3" @submit.prevent="submit">
      <div>
        <label for="auth-username" class="block text-sm font-medium">Nom d'utilisateur</label>
        <input
          id="auth-username"
          v-model="username"
          type="text"
          required
          autocomplete="username"
          class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <div>
        <label for="auth-password" class="block text-sm font-medium">Mot de passe</label>
        <input
          id="auth-password"
          v-model="password"
          type="password"
          required
          autocomplete="current-password"
          class="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <p v-if="error" class="text-sm text-red-600 dark:text-red-400" role="alert">
        {{ error }}
      </p>
      <button
        type="submit"
        :disabled="isSubmitting"
        class="w-full cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
      >
        Se connecter
      </button>
    </form>
  </section>
</template>
