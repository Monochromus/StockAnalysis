<script lang="ts">
  import type { SourceLink } from '$lib/types';

  interface Props {
    sources: SourceLink[];
  }

  let { sources }: Props = $props();
</script>

<div class="space-y-2">
  {#if sources.length === 0}
    <div class="text-stone-500 text-sm italic">
      Keine Quellen verfügbar.
    </div>
  {:else}
    <ul class="space-y-1.5">
      {#each sources as source, index}
        <li class="flex items-start gap-2 text-sm">
          <span class="text-stone-500 font-mono text-xs mt-0.5">
            [{index + 1}]
          </span>
          <div class="flex-1 min-w-0">
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              class="text-amber-400 hover:text-amber-300 hover:underline truncate block"
              title={source.url}
            >
              {source.title || source.url}
            </a>
            {#if source.grounding_score !== null}
              <span class="text-stone-600 text-xs">
                Vertrauen: {Math.round(source.grounding_score * 100)}%
              </span>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>
