import { create } from "zustand";
import { persist } from "zustand/middleware";
import { clearAccessTokens, setAccessTokens } from "@/lib/auth-token";

interface AuthState {
  accessToken: string | null;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      setTokens: (access, refresh) => {
        setAccessTokens(access, refresh);
        set({ accessToken: access });
      },
      logout: () => {
        clearAccessTokens();
        set({ accessToken: null });
      },
    }),
    {
      name: "contentos-auth",
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken) {
          setAccessTokens(state.accessToken, localStorage.getItem("refresh_token") ?? "");
        }
      },
    }
  )
);
