<script setup lang="ts">
import { onMounted, ref, watch } from "vue";

import { setUnauthorizedHandler } from "@/api/client";
import { useAuth } from "@/composables/useAuth";
import { useChat } from "@/composables/useChat";
import { useConversations } from "@/composables/useConversations";
import type { ChatMessage, Conversation } from "@/types/chat";
import LoginForm from "@/components/auth/LoginForm.vue";
import Composer from "@/components/chat/Composer.vue";
import MessageList from "@/components/chat/MessageList.vue";
import ConfirmDeleteDialog from "@/components/conversations/ConfirmDeleteDialog.vue";
import ConversationList from "@/components/conversations/ConversationList.vue";

const { user, ready, init, logout, markUnauthenticated } = useAuth();
const { conversations, currentId, current, load, create, remove, select, fetchMessages } =
  useConversations();
const messages = ref<ChatMessage[]>([]);
const { isStreaming, error, send } = useChat(currentId, messages);
const pendingDeletion = ref<Conversation | null>(null);
const loadError = ref<string | null>(null);

// Session expirée en cours d'usage : réafficher le formulaire de connexion.
setUnauthorizedHandler(markUnauthenticated);

onMounted(init);

// Connexion réussie : charger la liste des conversations.
watch(user, (value) => {
  loadError.value = null;
  if (value !== null) {
    void load();
  } else {
    conversations.value = [];
    currentId.value = null;
    messages.value = [];
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

async function onCreate(): Promise<void> {
  try {
    await create();
  } catch {
    loadError.value = "Impossible de créer la conversation.";
  }
}

async function confirmDeletion(): Promise<void> {
  const conversation = pendingDeletion.value;
  if (conversation === null) {
    return;
  }
  pendingDeletion.value = null;
  try {
    await remove(conversation.id);
  } catch {
    loadError.value = "Impossible de supprimer la conversation.";
  }
}
</script>

<template>
  <div
    v-if="!ready"
    class="flex flex-1 items-center justify-center text-sm text-slate-500 dark:text-slate-400"
  >
    Chargement…
  </div>
  <LoginForm v-else-if="user === null" />
  <div v-else class="flex w-full flex-1 flex-col overflow-hidden p-4">
    <div class="mb-3 flex items-center justify-end gap-3 text-sm">
      <span class="text-slate-500 dark:text-slate-400">{{ user }}</span>
      <button
        type="button"
        class="cursor-pointer text-slate-500 underline-offset-4 hover:underline dark:text-slate-400"
        @click="logout"
      >
        Déconnexion
      </button>
    </div>
    <div class="flex flex-1 gap-4 overflow-hidden">
      <ConversationList
        :conversations="conversations"
        :current-id="currentId"
        @select="select"
        @create="onCreate"
        @remove="pendingDeletion = $event"
      />
      <section
        class="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
      >
        <MessageList
          :messages="messages"
          :error="loadError ?? error"
          :has-conversation="current !== null"
          :is-streaming="isStreaming"
        />
        <Composer :disabled="isStreaming || current === null" @send="send" />
      </section>
      <ConfirmDeleteDialog
        :conversation="pendingDeletion"
        @confirm="confirmDeletion"
        @close="pendingDeletion = null"
      />
    </div>
  </div>
</template>
