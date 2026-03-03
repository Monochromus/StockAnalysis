<script lang="ts">
  import type { DailySeasonality } from '$lib/types';
  import { MONTH_NAMES } from '$lib/stores/seasonality';

  interface Props {
    dailySeasonality: DailySeasonality[];
  }

  let { dailySeasonality }: Props = $props();

  const WEEKDAY_LABELS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

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

    return groups;
  });

  // Calculate max absolute value for color scaling
  const maxValue = $derived(() => {
    if (dailySeasonality.length === 0) return 1;
    return Math.max(...dailySeasonality.map((d) => Math.abs(d.value)));
  });

  // Get color based on value
  function getColor(value: number, maxVal: number): string {
    const intensity = Math.min(Math.abs(value) / maxVal, 1);

    if (value > 0) {
      const alpha = 0.2 + intensity * 0.6;
      return `rgba(34, 197, 94, ${alpha})`;
    } else {
      const alpha = 0.2 + intensity * 0.6;
      return `rgba(239, 68, 68, ${alpha})`;
    }
  }

  // Get the first day of month (0 = Sunday, adjusted for Monday start)
  function getFirstDayOfMonth(month: number): number {
    const date = new Date(2023, month - 1, 1);
    const day = date.getDay();
    return day === 0 ? 6 : day - 1; // Convert to Monday = 0
  }

  // Get number of days in month
  function getDaysInMonth(month: number): number {
    return new Date(2023, month, 0).getDate();
  }
</script>

<div class="grid grid-cols-4 gap-4">
  {#each Array.from({ length: 12 }, (_, i) => i + 1) as month}
    {@const monthData = groupedByMonth().get(month) || []}
    {@const firstDay = getFirstDayOfMonth(month)}
    {@const daysInMonth = getDaysInMonth(month)}

    <div class="bg-stone-800/30 rounded-lg p-3">
      <!-- Month name -->
      <div class="text-sm font-medium text-stone-300 text-center mb-2">
        {MONTH_NAMES[month - 1]}
      </div>

      <!-- Weekday headers -->
      <div class="grid grid-cols-7 gap-0.5 mb-1">
        {#each WEEKDAY_LABELS as day}
          <div class="text-[10px] text-stone-500 text-center">{day}</div>
        {/each}
      </div>

      <!-- Calendar days -->
      <div class="grid grid-cols-7 gap-0.5">
        <!-- Empty cells for days before month starts -->
        {#each Array.from({ length: firstDay }) as _}
          <div class="w-5 h-5"></div>
        {/each}

        <!-- Day cells -->
        {#each Array.from({ length: daysInMonth }, (_, i) => i + 1) as day}
          {@const dayData = monthData.find((d) => d.day === day)}

          {#if dayData}
            <div
              class="w-5 h-5 rounded-sm flex items-center justify-center text-[9px] text-stone-300 cursor-pointer transition-transform hover:scale-110 hover:z-10"
              style="background-color: {getColor(dayData.value, maxValue())}"
              title="{day}. {MONTH_NAMES[month - 1]}: {dayData.value > 0 ? '+' : ''}{dayData.value.toFixed(2)}%"
            >
              {day}
            </div>
          {:else}
            <div class="w-5 h-5 rounded-sm bg-stone-800/50 flex items-center justify-center text-[9px] text-stone-500">
              {day}
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/each}
</div>
