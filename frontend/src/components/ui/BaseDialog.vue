<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";

/**
 * Fin wrapper Reka UI : apporte le style Tailwind, Reka fournit le
 * comportement (focus, Échap, clic sur l'arrière-plan) et l'accessibilité.
 */
defineProps<{ open: boolean; title: string }>();
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <DialogRoot
    :open="open"
    @update:open="
      (value: boolean) => {
        if (!value) emit('close');
      }
    "
  >
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-black/50" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900"
      >
        <DialogTitle class="text-lg font-semibold">{{ title }}</DialogTitle>
        <div class="mt-2 text-sm text-slate-600 dark:text-slate-400"><slot /></div>
        <div class="mt-6 flex justify-end gap-2">
          <DialogClose as-child>
            <button
              type="button"
              class="cursor-pointer rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Annuler
            </button>
          </DialogClose>
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
