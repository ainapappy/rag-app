/** État réactif de l'envoi : streaming SSE, mode non streamé, erreurs. */

import { ref, type Ref } from "vue";

import { ApiError } from "@/api/client";
import { sendMessage } from "@/api/conversations";
import type { ChatMessage } from "@/types/chat";

export function useChat(conversationId: Ref<number | null>, messages: Ref<ChatMessage[]>) {
  const isStreaming = ref(false);
  const error = ref<string | null>(null);

  /**
   * Envoie la question, affiche la réponse progressivement.
   *
   * Le message assistant est poussé vide puis enrichi au fil des tokens :
   * la réactivité Vue met le DOM à jour à chaque mutation.
   */
  async function send(question: string): Promise<void> {
    const id = conversationId.value;
    const trimmed = question.trim();
    if (id === null || isStreaming.value || trimmed === "") {
      return;
    }
    error.value = null;
    isStreaming.value = true;
    messages.value.push({ role: "user", content: trimmed, sources: [] });
    messages.value.push({ role: "assistant", content: "", sources: [] });
    const assistant = messages.value[messages.value.length - 1];

    try {
      await sendMessage(id, trimmed, (event) => {
        if (event.event === "sources") {
          assistant.sources = JSON.parse(event.data);
        } else if (event.event === "token") {
          assistant.content += JSON.parse(event.data).t;
        } else if (event.event === "error") {
          error.value = JSON.parse(event.data).message;
        }
        // « done » : rien à faire, le message est déjà à l'écran.
      });
    } catch (cause) {
      error.value = cause instanceof ApiError ? cause.message : "Erreur réseau.";
    } finally {
      isStreaming.value = false;
    }
  }

  return { isStreaming, error, send };
}
