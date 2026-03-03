<script lang="ts">
  import type { DailySeasonality } from '$lib/types';
  import { MONTH_NAMES_FULL } from '$lib/stores/seasonality';

  interface Props {
    dailySeasonality: DailySeasonality[];
  }

  let { dailySeasonality }: Props = $props();

  // Group data by month
  const groupedByMonth = $derived(() => {
    const groups: Map<number, DailySeasonality[]> = new Map();

    for (let month = 1; month <= 12; month++) {
      groups.set(month, []);
    }

    for (const day of dailySeasonality) {
      const monthDays = groups.get(day.month) || [];
      monthDays.push(day);
      groups.set(day.month, monthDays);
    }

    // Sort days within each month
    for (const [month, days] of groups) {
      days.sort((a, b) => a.day - b.day);
    }

    return groups;
  });

  // Get color based on value
  function getColor(value: number, maxValue: number): string {
    const intensity = Math.min(Math.abs(value) / maxValue, 1);

    if (value > 0) {
      // Bullish - green
      const alpha = 0.2 + intensity * 0.6;
      return `rgba(34, 197, 94, ${alpha})`; // green-500
    } else {
      // Bearish - red
      const alpha = 0.2 + intensity * 0.6;
      return `rgba(239, 68, 68, ${alpha})`; // red-500
    }
  }

  // Calculate max absolute value for color scaling
  const maxValue = $derived(() => {
    if (dailySeasonality.length === 0) return 1;
    return Math.max(...dailySeasonality.map((d) => Math.abs(d.value)));
  });
</script>

<div class="overflow-x-auto">
  <div class="min-w-[700px]">
    <!-- Header row with day numbers -->
    <div class="flex">
      <div class="w-24 flex-shrink-0"></div>
      <div class="flex-1 flex">
        {#each Array.from({ length: 31 }, (_, i) => i + 1) as day}
          <div class="w-6 h-6 flex items-center justify-center text-xs text-stone-500">{day}</div>
        {/each}
      </div>
    </div>

    <!-- Month rows -->
    {#each Array.from({ length: 12 }, (_, i) => i + 1) as month}
      {@const monthData = groupedByMonth().get(month) || []}
      {@const daysInMonth = new Date(2023, month, 0).getDate()}

      <div class="flex items-center">
        <!-- Month label -->
        <div class="w-24 flex-shrink-0 text-sm text-stone-400 font-medium pr-2 text-right">
          {MONTH_NAMES_FULL[month - 1]}
        </div>

        <!-- Day cells -->
        <div class="flex-1 flex">
          {#each Array.from({ length: 31 }, (_, i) => i + 1) as day}
            {@const dayData = monthData.find((d) => d.day === day)}

            {#if day <= daysInMonth && dayData}
              <div
                class="w-6 h-6 m-0.5 rounded-sm cursor-pointer transition-transform hover:scale-125 hover:z-10"
                style="background-color: {getColor(dayData.value, maxValue())}"
                title="{day}. {MONTH_NAMES_FULL[month - 1]}: {dayData.value > 0 ? '+' : ''}{dayData.value.toFixed(2)}% ({dayData.is_bullish ? 'Bullisch' : 'Baerisch'})"
              ></div>
            {:else if day <= daysInMonth}
              <div class="w-6 h-6 m-0.5 rounded-sm bg-stone-800/30"></div>
            {:else}
              <div class="w-6 h-6 m-0.5"></div>
            {/if}
          {/each}
        </div>
      </div>
    {/each}
  </div>

  <!-- Legend -->
  <div class="flex items-center justify-center gap-6 mt-4 text-xs text-stone-400">
    <div class="flex items-center gap-2">
      <div class="w-4 h-4 rounded-sm" style="background-color: rgba(239, 68, 68, 0.6)"></div>
      <span>Baerisch (stark)</span>
    </div>
    <div class="flex items-center gap-2">
      <div class="w-4 h-4 rounded-sm" style="background-color: rgba(239, 68, 68, 0.3)"></div>
      <span>Baerisch (schwach)</span>
    </div>
    <div class="flex items-center gap-2">
      <div class="w-4 h-4 rounded-sm" style="background-color: rgba(34, 197, 94, 0.3)"></div>
      <span>Bullisch (schwach)</span>
    </div>
    <div class="flex items-center gap-2">
      <div class="w-4 h-4 rounded-sm" style="background-color: rgba(34, 197, 94, 0.6)"></div>
      <span>Bullisch (stark)</span>
    </div>
  </div>
</div>
