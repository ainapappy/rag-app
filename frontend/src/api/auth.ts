/** Authentification (session Django) : me / login / logout en JSON. */

import { requestJson } from "./client";

/** État de session renvoyé par le backend. */
export interface Me {
  authenticated: boolean;
  username: string | null;
}

export function fetchMe(): Promise<Me> {
  return requestJson<Me>("/chat/api/me/");
}

export function login(username: string, password: string): Promise<Me> {
  return requestJson<Me>("/accounts/api/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): Promise<void> {
  return requestJson<void>("/accounts/api/logout/", { method: "POST" });
}
