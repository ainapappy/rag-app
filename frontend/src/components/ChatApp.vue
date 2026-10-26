<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import { useChat } from "@/composables/useChat";
import { useConversations } from "@/composables/useConversations";
import type { ChatMessage, Conversation } from "@/types/chat";
import Composer from "@/components/chat/Composer.vue";
import MessageList from "@/components/chat/MessageList.vue";
import ConfirmDeleteDialog from "@/components/conversations/ConfirmDeleteDialog.vue";
import ConversationList from "@/components/conversations/ConversationList.vue";

const { conversations, currentId, current, load, create, remove, select, fetchMessages } =
  useConversations();
const messages = ref<ChatMessage[]>([]);
const { isStreaming, error, send } = useChat(currentId, messages);
const pendingDeletion = ref<Conversation | null>(null);
const loadError = ref<string | null>(null);

onMounted(async () => {
  try {
    await load();
  } catch {
    loadError.value = "Impossible de charger les conversations.";
  }
});

// Changement de conversation : on recharge son historique.
watch(currentId, async (id) => {
  if (id === null) {
    messages.value = [];
    return;
  }
  try {
    messages.value = await fetchMessages(id);
  } catch {
    loadError.value = "Impossible de charger la conversation.";
  }
});

async function confirmDeletion(): Promise<void> {
  const conversation = pendingDeletion.value;
  if (conversation === null) {
    return;
  }
  pendingDeletion.value = null;
  await remove(conversation.id);
}
</script>

<template>
  <div class="flex w-full flex-1 gap-4 overflow-hidden p-4">
    <ConversationList
      :conversations="conversations"
      :current-id="currentId"
      @select="select"
      @create="create"
      @remove="pendingDeletion = $event"
    />
    <section
      class="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
    >
      <MessageList
        :messages="messages"
        :error="loadError ?? error"
        :has-conversation="current !== null"
      />
      <Composer :disabled="isStreaming || current === null" @send="send" />
    </section>
    <ConfirmDeleteDialog
      :conversation="pendingDeletion"
      @confirm="confirmDeletion"
      @close="pendingDeletion = null"
    />
  </div>
</template>
