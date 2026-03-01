<script lang="ts">
  import { Card } from '$lib/components/ui';
  import type { RiskReward } from '$lib/types';

  export let riskReward: RiskReward;

  function formatPrice(price: number): string {
    return price.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  }
</script>

<Card padding="md">
  <h3 class="font-semibold text-stone-50 mb-4">Risk/Reward Levels</h3>

  <div class="space-y-3">
    <div class="flex justify-between items-center py-2 border-b border-stone-700/30">
      <span class="text-stone-400">Entry</span>
      <span class="font-medium text-stone-50">{formatPrice(riskReward.entry_price)}</span>
    </div>

    <div class="flex justify-between items-center py-2 border-b border-stone-700/30">
      <span class="text-red-400">Stop Loss</span>
      <span class="font-medium text-red-400">{formatPrice(riskReward.stop_loss)}</span>
    </div>

    <div class="flex justify-between items-center pt-2">
      <span class="text-stone-400 font-medium">Risk/Reward Ratio</span>
      <span class="font-bold text-amber-500 text-lg">1:{riskReward.risk_reward_ratio.toFixed(2)}</span>
    </div>
  </div>
</Card>
