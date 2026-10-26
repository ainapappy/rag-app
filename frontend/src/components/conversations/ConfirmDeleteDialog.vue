<script setup lang="ts">
import type { Conversation } from "@/types/chat";
import BaseDialog from "@/components/ui/BaseDialog.vue";

defineProps<{ conversation: Conversation | null }>();
defineEmits<{ confirm: []; close: [] }>();
</script>

<template>
  <BaseDialog
    :open="conversation !== null"
    title="Supprimer la conversation ?"
    @close="$emit('close')"
  >
    <p>
      « {{ conversation?.title || "Nouvelle conversation" }} » et ses messages seront
      définitivement supprimés.
    </p>
    <template #footer>
      <button
        type="button"
        class="cursor-pointer rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500"
        @click="$emit('confirm')"
      >
        Supprimer
      </button>
    </template>
  </BaseDialog>
</template>
