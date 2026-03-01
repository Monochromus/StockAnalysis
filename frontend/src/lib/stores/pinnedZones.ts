import { writable, derived, get } from 'svelte/store';
import type { ProjectedZone } from '$lib/types';
import { waveOverlayData } from './analysis';

export interface PinnedZone extends ProjectedZone {
  id: string;           // Generated unique ID
  pinnedAt: string;     // Timestamp
  sourceSymbol: string; // Symbol for validation
  isPinned: true;       // Always true for pinned zones
}

interface PinnedZonesState {
  zones: PinnedZone[];
}

const initialState: PinnedZonesState = {
  zones: [],
};

function generateZoneId(): string {
  return `pin_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

function createPinnedZonesStore() {
  const { subscribe, set, update } = writable<PinnedZonesState>(initialState);

  return {
    subscribe,

    /**
     * Pin a zone, making it persistent across wave count changes.
     */
    pinZone(zone: ProjectedZone, symbol: string) {
      const pinnedZone: PinnedZone = {
        ...zone,
        id: generateZoneId(),
        pinnedAt: new Date().toISOString(),
        sourceSymbol: symbol,
        isPinned: true,
      };

      update((state) => ({
        ...state,
        zones: [...state.zones, pinnedZone],
      }));

      return pinnedZone.id;
    },

    /**
     * Unpin a zone by its ID.
     */
    unpinZone(zoneId: string) {
      update((state) => ({
        ...state,
        zones: state.zones.filter((z) => z.id !== zoneId),
      }));
    },

    /**
     * Clear all pinned zones (e.g., on symbol change).
     */
    clearAllPinned() {
      set(initialState);
    },

    /**
     * Check if a zone is pinned by comparing its properties.
     */
    isPinned(zone: ProjectedZone): boolean {
      const state = get({ subscribe });
      return state.zones.some(
        (pz) =>
          pz.label === zone.label &&
          pz.price_top === zone.price_top &&
          pz.price_bottom === zone.price_bottom &&
          pz.zone_type === zone.zone_type
      );
    },

    /**
     * Find a pinned zone matching the given zone.
     */
    findPinned(zone: ProjectedZone): PinnedZone | undefined {
      const state = get({ subscribe });
      return state.zones.find(
        (pz) =>
          pz.label === zone.label &&
          pz.price_top === zone.price_top &&
          pz.price_bottom === zone.price_bottom &&
          pz.zone_type === zone.zone_type
      );
    },
  };
}

export const pinnedZonesStore = createPinnedZonesStore();

/**
 * Derived store that merges current analysis zones with pinned zones.
 * Pinned zones are marked with isPinned=true, current zones with isPinned=false.
 * Duplicate zones (same label, prices, type) are deduplicated.
 */
export const combinedProjectedZones = derived(
  [waveOverlayData, pinnedZonesStore],
  ([$overlay, $pinned]) => {
    const currentZones = $overlay.projectedZones;
    const pinnedZones = $pinned.zones;

    // Build a map of pinned zones by their signature for deduplication
    const pinnedSignatures = new Set(
      pinnedZones.map(
        (z) => `${z.label}|${z.price_top}|${z.price_bottom}|${z.zone_type}`
      )
    );

    // Mark current zones: if they match a pinned zone, mark as pinned
    const result: (ProjectedZone & { id?: string; isPinned?: boolean })[] = [];

    for (const zone of currentZones) {
      const signature = `${zone.label}|${zone.price_top}|${zone.price_bottom}|${zone.zone_type}`;
      const matchingPinned = pinnedZones.find(
        (pz) =>
          pz.label === zone.label &&
          pz.price_top === zone.price_top &&
          pz.price_bottom === zone.price_bottom &&
          pz.zone_type === zone.zone_type
      );

      if (matchingPinned) {
        // Use the pinned version (has id)
        result.push({ ...zone, id: matchingPinned.id, isPinned: true });
      } else {
        result.push({ ...zone, isPinned: false });
      }
    }

    // Add pinned zones that are NOT in current zones (from different wave counts)
    for (const pinnedZone of pinnedZones) {
      const signature = `${pinnedZone.label}|${pinnedZone.price_top}|${pinnedZone.price_bottom}|${pinnedZone.zone_type}`;
      const existsInCurrent = currentZones.some(
        (z) =>
          z.label === pinnedZone.label &&
          z.price_top === pinnedZone.price_top &&
          z.price_bottom === pinnedZone.price_bottom &&
          z.zone_type === pinnedZone.zone_type
      );

      if (!existsInCurrent) {
        result.push(pinnedZone);
      }
    }

    return result;
  }
);
