<script setup lang="ts">
import { ref } from "vue";

defineProps<{ disabled: boolean }>();
const emit = defineEmits<{ send: [question: string] }>();
const question = ref("");

function submit(): void {
  const trimmed = question.value.trim();
  if (trimmed === "") {
    return;
  }
  emit("send", trimmed);
  question.value = "";
}
</script>

<template>
  <form
    class="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800"
    @submit.prevent="submit"
  >
    <input
      v-model="question"
      type="text"
      :disabled="disabled"
      placeholder="Votre question…"
      aria-label="Votre question"
      autocomplete="off"
      class="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
    />
    <button
      type="submit"
      :disabled="disabled || question.trim() === ''"
      class="cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
    >
      Envoyer
    </button>
  </form>
</template>
