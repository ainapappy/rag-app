/** Accès HTTP bas niveau : fetch, CSRF, erreurs typées. Aucun état réactif ici. */

/** Erreur d'API : message lisible + code HTTP (pour les choix d'affichage). */
export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

/** Jeton CSRF : cookie `csrftoken` (session Django), sinon balise meta. */
export function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  if (match) {
    return decodeURIComponent(match[1]);
  }
  const meta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]');
  return meta?.content ?? "";
}

let unauthorizedHandler: (() => void) | null = null;

/**
 * Enregistré par l'app au démarrage : appelé si une requête reçoit un 401
 * (session absente ou expirée) pour afficher à nouveau le formulaire.
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

/** Notifie la perte de session (utilisé aussi hors `requestJson`, ex. SSE). */
export function notifyUnauthorized(): void {
  unauthorizedHandler?.();
}

/**
 * Requête JSON avec session et CSRF ; renvoie le corps décodé.
 * `undefined` en cas de 204 (suppression).
 */
export async function requestJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const { method = "GET", body, ...rest } = options;
  const response = await fetch(url, {
    ...rest,
    method,
    body,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      ...rest.headers,
    },
  });
  if (response.status === 401) {
    unauthorizedHandler?.();
    throw new ApiError("Session expirée.", 401);
  }
  if (!response.ok) {
    throw new ApiError(`Requête échouée (${response.status}).`, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
