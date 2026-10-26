import type { SseEvent, SseEventName } from "@/types/chat";

/**
 * Parseur SSE pur : découpe un flux de texte en événements.
 *
 * Sans dépendance au DOM ni à fetch, il est testable avec vitest. Les chunks
 * réseau peuvent être coupés en plein milieu d'un événement : un buffer
 * interne conserve le fragment en attendant la suite.
 */
export function createSseParser() {
  let buffer = "";

  return {
    /** Ajoute un chunk reçu et renvoie les événements complets qui en émergent. */
    push(chunk: string): SseEvent[] {
      buffer += chunk;
      const events: SseEvent[] = [];
      // Les événements SSE sont séparés par une ligne vide.
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const event = parseBlock(buffer.slice(0, separator));
        if (event !== null) {
          events.push(event);
        }
        buffer = buffer.slice(separator + 2);
        separator = buffer.indexOf("\n\n");
      }
      return events;
    },
  };
}

/** Analyse un bloc `event: ...\ndata: ...` complet ; null si incomplet. */
function parseBlock(block: string): SseEvent | null {
  let name: string | null = null;
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) {
      name = line.slice("event: ".length).trim();
    } else if (line.startsWith("data: ")) {
      dataLines.push(line.slice("data: ".length));
    }
  }
  if (name === null || dataLines.length === 0) {
    return null;
  }
  return { event: name as SseEventName, data: dataLines.join("\n") };
}
