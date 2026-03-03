import { writable, derived } from 'svelte/store';
import type { ModuleId } from './modules';
import type { ViewMode } from '$lib/types';

interface UIState {
  headerVisible: boolean;
  toolbarVisible: boolean;
  sidebarVisible: boolean;
  footerVisible: boolean;
  activeSidebar: ModuleId | null;
  viewMode: ViewMode;
}

const defaultState: UIState = {
  headerVisible: true,
  toolbarVisible: true,
  sidebarVisible: true,
  footerVisible: false,
  activeSidebar: null,
  viewMode: 'chart',
};

function createUIStore() {
  const { subscribe, set, update } = writable<UIState>(defaultState);

  return {
    subscribe,

    toggleHeader: () => update((state) => ({ ...state, headerVisible: !state.headerVisible })),
    toggleToolbar: () => update((state) => ({ ...state, toolbarVisible: !state.toolbarVisible })),
    toggleSidebar: () => update((state) => ({ ...state, sidebarVisible: !state.sidebarVisible })),
    toggleFooter: () => update((state) => ({ ...state, footerVisible: !state.footerVisible })),

    showHeader: () => update((state) => ({ ...state, headerVisible: true })),
    showToolbar: () => update((state) => ({ ...state, toolbarVisible: true })),
    showSidebar: () => update((state) => ({ ...state, sidebarVisible: true })),
    showFooter: () => update((state) => ({ ...state, footerVisible: true })),

    hideHeader: () => update((state) => ({ ...state, headerVisible: false })),
    hideToolbar: () => update((state) => ({ ...state, toolbarVisible: false })),
    hideSidebar: () => update((state) => ({ ...state, sidebarVisible: false })),
    hideFooter: () => update((state) => ({ ...state, footerVisible: false })),

    hideAllOverlays: () =>
      update((state) => ({
        ...state,
        headerVisible: false,
        toolbarVisible: false,
        sidebarVisible: false,
        footerVisible: false,
        activeSidebar: null,
      })),

    showAllOverlays: () =>
      update((state) => ({
        ...state,
        headerVisible: true,
        toolbarVisible: true,
        sidebarVisible: true,
        footerVisible: false, // Footer remains hidden by default
        activeSidebar: null,
      })),

    resetToDefaults: () => set(defaultState),

    // Active sidebar management
    setActiveSidebar: (sidebar: ModuleId | null) =>
      update((state) => ({ ...state, activeSidebar: sidebar })),

    toggleActiveSidebar: (sidebar: ModuleId) =>
      update((state) => ({
        ...state,
        activeSidebar: state.activeSidebar === sidebar ? null : sidebar,
      })),

    // View mode management
    setViewMode: (mode: ViewMode) =>
      update((state) => ({ ...state, viewMode: mode })),

    toggleViewMode: () =>
      update((state) => {
        const modes: ViewMode[] = ['chart', 'calendar', 'news'];
        const currentIndex = modes.indexOf(state.viewMode);
        const nextIndex = (currentIndex + 1) % modes.length;
        return { ...state, viewMode: modes[nextIndex] };
      }),
  };
}

export const uiStore = createUIStore();

// Derived store to check if any overlay is visible
export const hasVisibleOverlays = derived(uiStore, ($ui) => {
  return $ui.headerVisible || $ui.toolbarVisible || $ui.sidebarVisible || $ui.footerVisible;
});

// Derived store to check if in fullscreen mode (no overlays)
export const isFullscreenMode = derived(uiStore, ($ui) => {
  return !$ui.headerVisible && !$ui.toolbarVisible && !$ui.sidebarVisible && !$ui.footerVisible;
});
