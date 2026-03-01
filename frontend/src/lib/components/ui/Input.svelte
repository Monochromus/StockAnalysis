<script lang="ts">
  export let value: string = '';
  export let placeholder: string = '';
  export let type: 'text' | 'number' | 'search' = 'text';
  export let disabled: boolean = false;
  export let id: string = '';
</script>

<input
  {type}
  {id}
  {placeholder}
  {disabled}
  bind:value
  class="w-full px-4 py-2.5 liquid-glass rounded-xl text-stone-50 placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-600/50 focus:border-amber-500/40 transition-all"
  on:input
  on:focus
  on:blur
  on:keydown
/>
