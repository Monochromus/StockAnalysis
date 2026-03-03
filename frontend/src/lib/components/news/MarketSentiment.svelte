<script lang="ts">
  import type { MarketSentiment } from '$lib/types';

  interface Props {
    sentiment: MarketSentiment;
    confidence: number;
    size?: 'sm' | 'md' | 'lg';
  }

  let { sentiment, confidence, size = 'md' }: Props = $props();

  const sentimentConfig = {
    bullish: {
      label: 'Bullisch',
      bgColor: 'bg-emerald-500/20',
      textColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/40',
      icon: '↗',
    },
    bearish: {
      label: 'Bärisch',
      bgColor: 'bg-red-500/20',
      textColor: 'text-red-400',
      borderColor: 'border-red-500/40',
      icon: '↘',
    },
    neutral: {
      label: 'Neutral',
      bgColor: 'bg-amber-500/20',
      textColor: 'text-amber-400',
      borderColor: 'border-amber-500/40',
      icon: '→',
    },
  };

  const sizeConfig = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  let config = $derived(sentimentConfig[sentiment]);
  let sizeClass = $derived(sizeConfig[size]);
</script>

<div class="inline-flex items-center gap-2">
  <span
    class="inline-flex items-center gap-1.5 rounded-full border font-medium
      {config.bgColor} {config.textColor} {config.borderColor} {sizeClass}"
  >
    <span class="font-bold">{config.icon}</span>
    {config.label}
  </span>

  {#if confidence > 0}
    <span class="text-stone-500 text-xs">
      {Math.round(confidence * 100)}% Konfidenz
    </span>
  {/if}
</div>
