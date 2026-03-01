<script lang="ts">
  import { Card, Badge } from '$lib/components/ui';
  import type { WaveCount } from '$lib/types';

  export let waveCount: WaveCount;
  export let isPrimary: boolean = false;

  $: waveLabels = waveCount.waves.map((w) => w.label).join(' → ');
  $: validRules = waveCount.validation_results.filter((r) => r.passed).length;
  $: totalRules = waveCount.validation_results.length;
</script>

<Card padding="md">
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="font-semibold text-stone-50">
          {isPrimary ? 'Primary Count' : 'Alternative'}
        </span>
        {#if isPrimary}
          <Badge variant="info">Primary</Badge>
        {/if}
      </div>
      <Badge variant={waveCount.is_complete ? 'success' : 'warning'}>
        {waveCount.is_complete ? 'Complete' : 'Incomplete'}
      </Badge>
    </div>

    <div class="flex items-center gap-2 flex-wrap">
      {#each waveCount.waves as wave}
        <span
          class="px-2 py-1 rounded text-xs font-medium border {wave.type === 'impulse'
            ? 'bg-emerald-400/15 text-emerald-400 border-emerald-400/20'
            : 'bg-amber-400/15 text-amber-400 border-amber-400/20'}"
        >
          {wave.label}
        </span>
      {/each}
    </div>

    <div class="grid grid-cols-2 gap-4 pt-2 border-t border-stone-700/30">
      <div>
        <p class="text-xs text-stone-500">Confidence</p>
        <p class="text-lg font-semibold text-amber-500">{waveCount.overall_confidence.toFixed(1)}%</p>
      </div>
      <div>
        <p class="text-xs text-stone-500">Rules Passed</p>
        <p class="text-lg font-semibold {validRules === totalRules ? 'text-emerald-400' : 'text-amber-400'}">
          {validRules}/{totalRules}
        </p>
      </div>
    </div>
  </div>
</Card>
