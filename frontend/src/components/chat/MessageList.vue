<script setup lang="ts">
import { computed } from "vue";

import type { ChatMessage } from "@/types/chat";
import MessageBubble from "@/components/chat/MessageBubble.vue";
import TypingIndicator from "@/components/chat/TypingIndicator.vue";

const props = defineProps<{
  messages: ChatMessage[];
  error: string | null;
  hasConversation: boolean;
  isStreaming?: boolean;
}>();

// Occupé seulement en attendant le premier token : ensuite la réponse
// s'affiche elle-même, l'indicateur ferait doublon.
const busy = computed(() => {
  const last = props.messages[props.messages.length - 1];
  return props.isStreaming === true && (last?.content ?? "") === "";
});
</script>

<template>
  <div class="flex-1 space-y-4 overflow-y-auto p-4">
    <p v-if="!hasConversation" class="text-sm text-slate-500 dark:text-slate-400">
      Créez une conversation pour commencer.
    </p>
    <p
      v-else-if="messages.length === 0"
      class="text-sm text-slate-500 dark:text-slate-400"
    >
      Posez une question sur les documents indexés.
    </p>
    <MessageBubble v-for="(message, index) in messages" :key="index" :message="message" />
    <TypingIndicator v-if="busy" />
    <p
      v-if="error"
      class="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      role="alert"
    >
      {{ error }}
    </p>
  </div>
</template>
