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
  if (!response.ok) {
    throw new ApiError(`Requête échouée (${response.status}).`, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
