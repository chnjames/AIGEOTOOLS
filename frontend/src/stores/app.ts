import { create } from 'zustand';
import { AppConfig } from '@/types';
import { configApi } from '@/api/config';

interface AppState {
  config: AppConfig | null;
  configLoading: boolean;
  sidebarCollapsed: boolean;
  darkMode: boolean;
  isStreaming: boolean;
  mobileDrawerOpen: boolean;

  // Actions
  fetchConfig: () => Promise<void>;
  updateConfig: (update: Partial<AppConfig> & { gen_api_key?: string; verify_keys?: Record<string, string>; tongyi_wanxiang_api_key?: string }) => Promise<void>;
  toggleSidebar: () => void;
  setDarkMode: (dark: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  setMobileDrawerOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  config: null,
  configLoading: false,
  sidebarCollapsed: localStorage.getItem('sidebar_collapsed') === 'true',
  darkMode: localStorage.getItem('dark_mode') === 'true',
  isStreaming: false,
  mobileDrawerOpen: false,

  fetchConfig: async () => {
    set({ configLoading: true });
    try {
      const cfg = await configApi.get();
      set({ config: cfg });
    } catch (err) {
      console.error('[AppStore] fetchConfig failed:', err);
      // Config not available yet - user needs to set up
    } finally {
      set({ configLoading: false });
    }
  },

  updateConfig: async (update) => {
    const cfg = await configApi.update(update);
    set({ config: cfg });
  },

  toggleSidebar: () => set(s => {
    const collapsed = !s.sidebarCollapsed;
    localStorage.setItem('sidebar_collapsed', String(collapsed));
    return { sidebarCollapsed: collapsed };
  }),
  setDarkMode: (dark) => {
    localStorage.setItem('dark_mode', String(dark));
    set({ darkMode: dark });
  },
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
}));
