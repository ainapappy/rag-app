/** Accès aux conversations : endpoints JSON de session + flux SSE d'envoi. */

import type { ChatMessage, Conversation, SseEvent, StoredMessage } from "@/types/chat";
import { ApiError, csrfToken, notifyUnauthorized, requestJson } from "./client";
import { createSseParser } from "@/lib/sse";

interface ConversationDetailPayload {
  conversation: Conversation;
  messages: StoredMessage[];
}

export async function listConversations(): Promise<Conversation[]> {
  const payload = await requestJson<{ conversations: Conversation[] }>(
    "/chat/api/conversations/",
  );
  return payload.conversations;
}

export function createConversation(title = ""): Promise<Conversation> {
  return requestJson<Conversation>("/chat/api/conversations/", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function fetchConversation(id: number): Promise<ConversationDetailPayload> {
  return requestJson<ConversationDetailPayload>(`/chat/api/conversations/${id}/`);
}

export function deleteConversation(id: number): Promise<void> {
  return requestJson<void>(`/chat/api/conversations/${id}/`, { method: "DELETE" });
}

/**
 * Envoie une question au backend.
 *
 * Mode streamé : répond en SSE (`sources` / `token` / `done` / `error`),
 * chaque événement complet est passé à `onEvent`. Mode non streamé
 * (STREAMING_ENABLED=False) : le JSON unique est normalisé en événements,
 * de sorte que l'appelant n'ait pas à connaître le mode.
 */
export async function sendMessage(
  conversationId: number,
  question: string,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const response = await fetch(`/chat/${conversationId}/send/`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRFToken": csrfToken(),
    },
    body: new URLSearchParams({ question }),
  });
  if (response.status === 401) {
    notifyUnauthorized();
    throw new ApiError("Session expirée.", 401);
  }
  if (!response.ok) {
    throw new ApiError(`Envoi refusé (${response.status}).`, response.status);
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    const message = (await response.json()) as ChatMessage;
    onEvent({ event: "sources", data: JSON.stringify(message.sources ?? []) });
    onEvent({ event: "token", data: JSON.stringify({ t: message.content }) });
    return;
  }

  if (response.body === null) {
    throw new ApiError("Flux SSE indisponible.", response.status);
  }
  const parser = createSseParser();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    for (const event of parser.push(decoder.decode(value, { stream: true }))) {
      onEvent(event);
    }
  }
}
