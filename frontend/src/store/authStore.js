/**
 * Auth Store (Zustand) — global authentication state.
 * Persists tokens in localStorage. User object in memory.
 */
import { create } from "zustand";
import { authApi } from "../api/auth";

const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem("access_token"),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authApi.login({ email, password });
      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);
      set({ user: data.user, isAuthenticated: true, isLoading: false });
      return { success: true };
    } catch (err) {
      const message = err.response?.data?.error?.message || "Login failed.";
      set({ error: message, isLoading: false });
      return { success: false, error: message };
    }
  },

  register: async (payload) => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await authApi.register(payload);
      localStorage.setItem("access_token", data.tokens.access);
      localStorage.setItem("refresh_token", data.tokens.refresh);
      set({ user: data.user, isAuthenticated: true, isLoading: false });
      return { success: true };
    } catch (err) {
      const message = err.response?.data?.error?.message || "Registration failed.";
      set({ error: message, isLoading: false });
      return { success: false, error: message };
    }
  },

  loadUser: async () => {
    if (!localStorage.getItem("access_token")) return;
    try {
      const { data } = await authApi.me();
      set({ user: data, isAuthenticated: true });
    } catch {
      set({ isAuthenticated: false, user: null });
    }
  },

  logout: async () => {
    try {
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) await authApi.logout({ refresh });
    } catch {}
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, isAuthenticated: false });
  },

  clearError: () => set({ error: null }),
}));

export default useAuthStore;
