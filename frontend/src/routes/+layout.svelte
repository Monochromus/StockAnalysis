<script lang="ts">
  import '../app.css';
  import DebugPanel from '$lib/components/debug/DebugPanel.svelte';

  let { children } = $props();
</script>

<div class="min-h-screen bg-bg-primary">
  {@render children()}
</div>

<DebugPanel />
