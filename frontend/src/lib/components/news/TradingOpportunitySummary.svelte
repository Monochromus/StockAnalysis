<script lang="ts">
  import type { CommodityNewsAnalysis, MarketSentiment } from '$lib/types';

  interface Props {
    analyses: CommodityNewsAnalysis[];
  }

  let { analyses }: Props = $props();

  // Sentiment score mapping: bullish = positive, bearish = negative
  function getSentimentScore(sentiment: MarketSentiment): number {
    switch (sentiment) {
      case 'bullish':
        return 1;
      case 'bearish':
        return -1;
      case 'neutral':
      default:
        return 0;
    }
  }

  // Find the best trading opportunity
  function getBestOpportunity(items: CommodityNewsAnalysis[]): {
    analysis: CommodityNewsAnalysis;
    direction: 'long' | 'short';
    score: number;
  } | null {
    if (items.length === 0) return null;

    let bestAnalysis: CommodityNewsAnalysis | null = null;
    let bestScore = 0;
    let bestDirection: 'long' | 'short' = 'long';

    for (const analysis of items) {
      const sentimentScore = getSentimentScore(analysis.market_assessment.sentiment);
      const confidence = analysis.market_assessment.confidence;
      // Score = |sentiment| * confidence (we want strong signals with high confidence)
      const absoluteScore = Math.abs(sentimentScore) * confidence;

      if (absoluteScore > bestScore) {
        bestScore = absoluteScore;
        bestAnalysis = analysis;
        bestDirection = sentimentScore > 0 ? 'long' : 'short';
      }
    }

    if (!bestAnalysis || bestScore === 0) return null;

    return {
      analysis: bestAnalysis,
      direction: bestDirection,
      score: bestScore,
    };
  }

  // Generate a synthesis summary
  function generateSynthesis(items: CommodityNewsAnalysis[]): string {
    if (items.length === 0) return '';

    const bullishCount = items.filter(a => a.market_assessment.sentiment === 'bullish').length;
    const bearishCount = items.filter(a => a.market_assessment.sentiment === 'bearish').length;
    const neutralCount = items.filter(a => a.market_assessment.sentiment === 'neutral').length;

    const parts: string[] = [];
    if (bullishCount > 0) parts.push(`${bullishCount} bullish`);
    if (bearishCount > 0) parts.push(`${bearishCount} bearish`);
    if (neutralCount > 0) parts.push(`${neutralCount} neutral`);

    return `Marktübersicht: ${parts.join(', ')} von ${items.length} analysierten Rohstoffen.`;
  }

  // Reactive computed values
  let bestOpportunity = $derived(getBestOpportunity(analyses));
  let synthesis = $derived(generateSynthesis(analyses));
</script>

{#if bestOpportunity}
  <div class="liquid-glass rounded-xl overflow-hidden mb-4">
    <!-- Header with trading signal -->
    <div class="px-5 py-4 border-b border-stone-700/50 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg flex items-center justify-center {
          bestOpportunity.direction === 'long'
            ? 'bg-emerald-500/20 border border-emerald-500/40'
            : 'bg-red-500/20 border border-red-500/40'
        }">
          {#if bestOpportunity.direction === 'long'}
            <svg class="w-5 h-5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M7 17l5-5 5 5M7 7l5 5 5-5" />
            </svg>
          {:else}
            <svg class="w-5 h-5 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M7 7l5 5 5-5M7 17l5-5 5-5" />
            </svg>
          {/if}
        </div>
        <div>
          <h2 class="text-lg font-semibold text-stone-100 flex items-center gap-2">
            Beste Trading-Chance
            <span class="text-sm font-normal px-2 py-0.5 rounded {
              bestOpportunity.direction === 'long'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }">
              {bestOpportunity.direction.toUpperCase()}
            </span>
          </h2>
          <p class="text-stone-500 text-sm">{synthesis}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm text-stone-400">Konfidenz:</span>
        <div class="flex items-center gap-1.5">
          <div class="w-24 h-2 bg-stone-700 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full {
                bestOpportunity.analysis.market_assessment.confidence >= 0.7
                  ? 'bg-emerald-500'
                  : bestOpportunity.analysis.market_assessment.confidence >= 0.4
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              }"
              style="width: {bestOpportunity.analysis.market_assessment.confidence * 100}%"
            ></div>
          </div>
          <span class="text-sm font-medium {
            bestOpportunity.analysis.market_assessment.confidence >= 0.7
              ? 'text-emerald-400'
              : bestOpportunity.analysis.market_assessment.confidence >= 0.4
                ? 'text-amber-400'
                : 'text-red-400'
          }">
            {Math.round(bestOpportunity.analysis.market_assessment.confidence * 100)}%
          </span>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="p-5">
      <div class="flex items-start gap-4">
        <!-- Commodity Info -->
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xl font-bold text-stone-100">
              {bestOpportunity.analysis.commodity_name}
            </span>
            <span class="text-stone-500 font-mono text-sm">
              {bestOpportunity.analysis.symbol}
            </span>
          </div>

          <!-- Assessment Summary -->
          <p class="text-stone-300 leading-relaxed mb-3">
            {bestOpportunity.analysis.market_assessment.summary}
          </p>

          <!-- Key Factors -->
          {#if bestOpportunity.analysis.market_assessment.key_factors.length > 0}
            <div class="mb-3">
              <span class="text-sm font-medium text-stone-400 mb-1.5 block">Schlüsselfaktoren:</span>
              <div class="flex flex-wrap gap-2">
                {#each bestOpportunity.analysis.market_assessment.key_factors as factor}
                  <span class="text-sm bg-stone-700/50 text-stone-300 px-2.5 py-1 rounded-lg border border-stone-600/50">
                    {factor}
                  </span>
                {/each}
              </div>
            </div>
          {/if}

          <!-- News Highlights -->
          {#if bestOpportunity.analysis.news_highlights.length > 0}
            <div>
              <span class="text-sm font-medium text-stone-400 mb-1.5 block">Aktuelle Highlights:</span>
              <ul class="space-y-1">
                {#each bestOpportunity.analysis.news_highlights.slice(0, 3) as highlight}
                  <li class="text-stone-400 text-sm pl-3 border-l-2 {
                    bestOpportunity.direction === 'long'
                      ? 'border-emerald-500/50'
                      : 'border-red-500/50'
                  }">
                    {highlight}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>

        <!-- Direction Indicator -->
        <div class="flex-shrink-0 text-center px-4">
          <div class="w-20 h-20 rounded-xl flex items-center justify-center {
            bestOpportunity.direction === 'long'
              ? 'bg-gradient-to-br from-emerald-500/30 to-emerald-600/10 border border-emerald-500/40'
              : 'bg-gradient-to-br from-red-500/30 to-red-600/10 border border-red-500/40'
          }">
            {#if bestOpportunity.direction === 'long'}
              <svg class="w-10 h-10 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            {:else}
              <svg class="w-10 h-10 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12l7 7 7-7" />
              </svg>
            {/if}
          </div>
          <span class="block mt-2 text-sm font-semibold {
            bestOpportunity.direction === 'long' ? 'text-emerald-400' : 'text-red-400'
          }">
            {bestOpportunity.direction === 'long' ? 'KAUFEN' : 'VERKAUFEN'}
          </span>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="px-5 py-2 bg-stone-800/30 border-t border-stone-700/50">
      <p class="text-stone-600 text-xs">
        Diese Empfehlung basiert auf der KI-Analyse aller Watchlist-Rohstoffe. Keine Anlageberatung - immer eigene Recherche durchführen.
      </p>
    </div>
  </div>
{:else if analyses.length > 0}
  <div class="liquid-glass rounded-xl overflow-hidden mb-4 px-5 py-4">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-lg bg-stone-700/50 border border-stone-600/50 flex items-center justify-center">
        <svg class="w-5 h-5 text-stone-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
      </div>
      <div>
        <h2 class="text-lg font-semibold text-stone-100">Keine klare Trading-Chance</h2>
        <p class="text-stone-500 text-sm">
          Alle {analyses.length} analysierten Rohstoffe zeigen neutrale Signale. Abwarten empfohlen.
        </p>
      </div>
    </div>
  </div>
{/if}
