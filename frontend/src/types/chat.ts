/** Types partagés du chat (miroir des dataclasses rag_core / modèles Django). */

/** Source citée par une réponse (cf. `rag_core.models.Source`). */
export interface Source {
  source: string;
  page: number | null;
  score: number;
  excerpt: string;
}

/** Message tel qu'affiché côté client. */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources: Source[];
}

/** Message tel que renvoyé par l'API JSON (avec id et date). */
export interface StoredMessage extends ChatMessage {
  id: number;
  created_at: string;
}

/** Conversation (cf. modèle Django `Conversation`). */
export interface Conversation {
  id: number;
  title: string;
  created_at: string;
}

/** Nom des événements SSE du protocole (cf. `ChatService.stream`). */
export type SseEventName = "sources" | "token" | "done" | "error";

/** Événement SSE brut : nom + charge utile (chaîne JSON, non analysée ici). */
export interface SseEvent {
  event: SseEventName;
  data: string;
}
