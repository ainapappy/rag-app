/** État de session partagé (composable singleton) : me / login / logout. */

import { ref } from "vue";

import { fetchMe, login as loginApi, logout as logoutApi } from "@/api/auth";

// Déclarés au niveau module : toutes les composantes partagent le même état.
const user = ref<string | null>(null);
const ready = ref(false);

export function useAuth() {
  /** Premier appel de l'app : interroge la session et pose le cookie CSRF. */
  async function init(): Promise<void> {
    try {
      const me = await fetchMe();
      user.value = me.authenticated ? me.username : null;
    } catch {
      user.value = null;
    } finally {
      ready.value = true;
    }
  }

  async function login(username: string, password: string): Promise<void> {
    const me = await loginApi(username, password);
    user.value = me.username;
  }

  async function logout(): Promise<void> {
    try {
      await logoutApi();
    } finally {
      user.value = null;
    }
  }

  /** Appelé par le handler 401 global (session expirée en cours d'usage). */
  function markUnauthenticated(): void {
    user.value = null;
  }

  return { user, ready, init, login, logout, markUnauthenticated };
}
