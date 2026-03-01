<script lang="ts">
  import { Badge } from '$lib/components/ui';
  import type { ValidationResult } from '$lib/types';

  export let result: ValidationResult;
</script>

<div class="flex items-start gap-3 p-3 rounded-xl bg-stone-800/30 border border-stone-700/20">
  <div class="flex-shrink-0 mt-0.5">
    {#if result.passed}
      <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
    {:else}
      <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    {/if}
  </div>

  <div class="flex-1 min-w-0">
    <div class="flex items-center gap-2 mb-1">
      <span class="font-medium text-stone-50 text-sm">{result.rule_name}</span>
      <Badge variant={result.passed ? 'success' : 'error'}>
        {result.passed ? 'Pass' : 'Fail'}
      </Badge>
    </div>
    <p class="text-xs text-stone-400">{result.rule_description}</p>
    {#if result.details}
      <p class="text-xs text-stone-500 mt-1">{result.details}</p>
    {/if}
  </div>
</div>
