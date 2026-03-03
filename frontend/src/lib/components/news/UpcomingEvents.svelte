<script lang="ts">
  import type { UpcomingEvent } from '$lib/types';

  interface Props {
    events: UpcomingEvent[];
  }

  let { events }: Props = $props();

  const impactConfig = {
    high: {
      label: 'Hoch',
      color: 'bg-red-500/20 text-red-400 border-red-500/30',
    },
    medium: {
      label: 'Mittel',
      color: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    },
    low: {
      label: 'Niedrig',
      color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    },
  };

  // Sort events by date (chronologically)
  let sortedEvents = $derived(
    [...events].sort((a, b) => {
      // Try to parse dates for sorting
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      if (!isNaN(dateA.getTime()) && !isNaN(dateB.getTime())) {
        return dateA.getTime() - dateB.getTime();
      }
      return 0;
    })
  );
</script>

<div class="space-y-3">
  {#if sortedEvents.length === 0}
    <div class="text-stone-500 text-sm italic py-2">
      Keine anstehenden Termine gefunden.
    </div>
  {:else}
    {#each sortedEvents as event}
      <div class="bg-stone-800/30 rounded-lg p-3 border border-stone-700/50">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-stone-300 font-medium text-sm">
                {event.date}
              </span>
              <span
                class="text-xs px-1.5 py-0.5 rounded border {impactConfig[event.impact].color}"
              >
                {impactConfig[event.impact].label}
              </span>
            </div>
            <p class="text-stone-400 text-sm">{event.description}</p>
            {#if event.source}
              <p class="text-stone-600 text-xs mt-1">
                Quelle: {event.source}
              </p>
            {/if}
          </div>
          {#if event.grounding_score !== null}
            <div class="flex-shrink-0">
              <span class="text-xs text-stone-600" title="Grounding Score">
                {Math.round(event.grounding_score * 100)}%
              </span>
            </div>
          {/if}
        </div>
      </div>
    {/each}
  {/if}

  <!-- Disclaimer -->
  <div class="text-stone-600 text-xs mt-4 pt-3 border-t border-stone-700/50">
    Hinweis: Termine werden aus Google-Suchergebnissen extrahiert.
    Bitte vor Handelsentscheidungen unbedingt mit offiziellen Quellen abgleichen.
  </div>
</div>
