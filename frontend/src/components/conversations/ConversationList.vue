<script setup lang="ts">
import type { Conversation } from "@/types/chat";
import ConversationMenu from "@/components/conversations/ConversationMenu.vue";

defineProps<{
  conversations: Conversation[];
  currentId: number | null;
}>();

defineEmits<{
  select: [id: number];
  create: [];
  remove: [conversation: Conversation];
}>();
</script>

<template>
  <aside class="flex w-64 shrink-0 flex-col gap-3">
    <button
      type="button"
      class="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
      @click="$emit('create')"
    >
      + Nouvelle conversation
    </button>
    <nav class="flex-1 space-y-1 overflow-y-auto">
      <p
        v-if="conversations.length === 0"
        class="px-2 text-sm text-slate-500 dark:text-slate-400"
      >
        Aucune conversation.
      </p>
      <div
        v-for="conversation in conversations"
        :key="conversation.id"
        class="group flex items-center justify-between rounded-lg px-2 py-1.5 text-sm"
        :class="
          conversation.id === currentId
            ? 'bg-slate-200 font-medium dark:bg-slate-800'
            : 'hover:bg-slate-100 dark:hover:bg-slate-800/50'
        "
      >
        <button
          type="button"
          class="min-w-0 flex-1 cursor-pointer truncate text-left"
          :title="conversation.title"
          @click="$emit('select', conversation.id)"
        >
          {{ conversation.title || "Nouvelle conversation" }}
        </button>
        <ConversationMenu @remove="$emit('remove', conversation)" />
      </div>
    </nav>
  </aside>
</template>
