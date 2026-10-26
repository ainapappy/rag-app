/** État réactif de la liste des conversations (aucune logique HTTP bas niveau). */

import { computed, ref } from "vue";

import type { ChatMessage, Conversation } from "@/types/chat";
import {
  createConversation,
  deleteConversation,
  fetchConversation,
  listConversations,
} from "@/api/conversations";

export function useConversations() {
  const conversations = ref<Conversation[]>([]);
  const currentId = ref<number | null>(null);
  const current = computed<Conversation | null>(
    () => conversations.value.find((conversation) => conversation.id === currentId.value) ?? null,
  );

  async function load(): Promise<void> {
    conversations.value = await listConversations();
  }

  async function create(): Promise<void> {
    const conversation = await createConversation();
    conversations.value = [conversation, ...conversations.value];
    currentId.value = conversation.id;
  }

  async function remove(id: number): Promise<void> {
    await deleteConversation(id);
    conversations.value = conversations.value.filter(
      (conversation) => conversation.id !== id,
    );
    if (currentId.value === id) {
      currentId.value = null;
    }
  }

  function select(id: number): void {
    currentId.value = id;
  }

  async function fetchMessages(id: number): Promise<ChatMessage[]> {
    const detail = await fetchConversation(id);
    return detail.messages;
  }

  return { conversations, currentId, current, load, create, remove, select, fetchMessages };
}
