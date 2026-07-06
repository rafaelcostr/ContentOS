/** Token único — localStorage + fallback Zustand persist. */

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";
const ZUSTAND_KEY = "contentos-auth";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;

  const direct = localStorage.getItem(ACCESS_KEY);
  if (direct && direct !== "undefined" && direct !== "null") {
    return direct;
  }

  try {
    const raw = localStorage.getItem(ZUSTAND_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: { accessToken?: string | null } };
    const token = parsed.state?.accessToken;
    if (token && token !== "undefined") {
      localStorage.setItem(ACCESS_KEY, token);
      return token;
    }
  } catch {
    /* ignore */
  }

  return null;
}

export function setAccessTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearAccessTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
