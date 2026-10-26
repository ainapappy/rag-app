<script setup lang="ts">
// Indicateur « occupé » affiché pendant l'attente de la réponse (streaming).
// role="status" + aria-live : les lecteurs d'écran annoncent l'attente.
</script>

<template>
  <div class="flex justify-start" role="status" aria-live="polite">
    <div
      class="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400"
    >
      <span class="flex gap-1" aria-hidden="true">
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]"></span>
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]"></span>
        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"></span>
      </span>
      Chargement…
    </div>
  </div>
</template>
