<script setup lang="ts">
import { computed } from "vue";

import type { ChatMessage } from "@/types/chat";
import SourcesPanel from "@/components/chat/SourcesPanel.vue";

const props = defineProps<{ message: ChatMessage }>();
const isUser = computed(() => props.message.role === "user");
</script>

<template>
  <div class="flex" :class="isUser ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap"
      :class="
        isUser
          ? 'rounded-br-sm bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
          : 'rounded-bl-sm border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/50'
      "
    >
      {{ message.content }}
      <SourcesPanel v-if="!isUser && message.sources.length > 0" :sources="message.sources" />
    </div>
  </div>
</template>
