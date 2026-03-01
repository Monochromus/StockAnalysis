<script lang="ts">
  export let title: string;
  export let defaultOpen: boolean = false;

  let isOpen = defaultOpen;

  function toggle() {
    isOpen = !isOpen;
  }
</script>

<div class="settings-section">
  <button class="header" on:click={toggle} type="button">
    <span class="title">{title}</span>
    <svg
      class="chevron"
      class:open={isOpen}
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  </button>

  {#if isOpen}
    <div class="content">
      <slot />
    </div>
  {/if}
</div>

<style>
  .settings-section {
    border-bottom: 1px solid var(--glass-border-subtle);
  }

  .settings-section:last-child {
    border-bottom: none;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.75rem 0;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-primary);
    text-align: left;
    transition: color var(--liquid-duration) var(--liquid-easing);
  }

  .header:hover {
    color: var(--color-accent);
  }

  .title {
    font-size: 0.875rem;
    font-weight: 600;
  }

  .chevron {
    transition: transform var(--liquid-duration) var(--liquid-spring);
    color: var(--color-text-muted);
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .content {
    padding: 0.5rem 0 1rem;
    animation: liquid-slide-top var(--liquid-duration) var(--liquid-spring);
  }
</style>
