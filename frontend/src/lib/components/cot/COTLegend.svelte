<script lang="ts">
  /**
   * COT Legend Component
   * Explains trader types and COT Index interpretation
   */

  export let expanded: boolean = false;

  function toggle() {
    expanded = !expanded;
  }
</script>

<div class="cot-legend">
  <button class="legend-toggle" on:click={toggle}>
    <svg
      class="info-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
    <span>COT-Daten Erklärung</span>
    <svg
      class="chevron"
      class:expanded
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <polyline points="6,9 12,15 18,9" />
    </svg>
  </button>

  {#if expanded}
    <div class="legend-content">
      <div class="legend-section">
        <h4>Trader-Typen</h4>

        <div class="trader-type">
          <div class="type-header commercial">
            <span class="type-dot"></span>
            <span class="type-name">Commercials (Hedgers)</span>
          </div>
          <p class="type-description">
            Produzenten und Verbraucher, die sich gegen Preisrisiken absichern.
            Oft als "Smart Money" bezeichnet - ihre Positionierung zeigt reale
            Markteinschätzung basierend auf Fundamentaldaten.
          </p>
        </div>

        <div class="trader-type">
          <div class="type-header noncommercial">
            <span class="type-dot"></span>
            <span class="type-name">Non-Commercials (Spekulanten)</span>
          </div>
          <p class="type-description">
            Hedge Funds und große Trader, die auf Preisbewegungen spekulieren.
            Extreme Positionen können auf überkaufte/überverkaufte Märkte hindeuten.
          </p>
        </div>

        <div class="trader-type">
          <div class="type-header nonreportable">
            <span class="type-dot"></span>
            <span class="type-name">Non-Reportable (Kleine Trader)</span>
          </div>
          <p class="type-description">
            Kleine Positionen, die nicht einzeln gemeldet werden müssen.
            Oft als Kontraindikator verwendet.
          </p>
        </div>
      </div>

      <div class="legend-section">
        <h4>COT-Index Interpretation</h4>

        <div class="index-scale">
          <div class="scale-bar">
            <div class="scale-zone bearish">0-20</div>
            <div class="scale-zone neutral-low">20-40</div>
            <div class="scale-zone neutral">40-60</div>
            <div class="scale-zone neutral-high">60-80</div>
            <div class="scale-zone bullish">80-100</div>
          </div>
        </div>

        <div class="interpretation-list">
          <div class="interpretation">
            <span class="index-range bullish">80-100</span>
            <span class="index-meaning">
              Commercial extrem long → oft bullisch für Preis
            </span>
          </div>
          <div class="interpretation">
            <span class="index-range bearish">0-20</span>
            <span class="index-meaning">
              Commercial extrem short → oft bearisch für Preis
            </span>
          </div>
          <div class="interpretation">
            <span class="index-range neutral">40-60</span>
            <span class="index-meaning">
              Neutral Zone → kein klares Signal
            </span>
          </div>
        </div>
      </div>

      <div class="legend-section">
        <h4>Daten-Update</h4>
        <p class="update-info">
          CFTC veröffentlicht COT-Daten jeden Freitag um 15:30 EST.
          Die Daten zeigen Positionen vom vorherigen Dienstag.
        </p>
      </div>
    </div>
  {/if}
</div>

<style>
  .cot-legend {
    border: 1px solid #374151;
    border-radius: 0.5rem;
    background: #1F2937;
    overflow: hidden;
  }

  .legend-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    color: #9CA3AF;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.2s;
  }

  .legend-toggle:hover {
    background: #374151;
    color: #E5E7EB;
  }

  .info-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  .chevron {
    width: 16px;
    height: 16px;
    margin-left: auto;
    transition: transform 0.2s;
  }

  .chevron.expanded {
    transform: rotate(180deg);
  }

  .legend-content {
    padding: 0 1rem 1rem;
    border-top: 1px solid #374151;
  }

  .legend-section {
    margin-top: 1rem;
  }

  .legend-section h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #E5E7EB;
    margin-bottom: 0.5rem;
  }

  .trader-type {
    margin-bottom: 0.75rem;
  }

  .type-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .type-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .type-header.commercial .type-dot {
    background: #3B82F6;
  }

  .type-header.noncommercial .type-dot {
    background: #F59E0B;
  }

  .type-header.nonreportable .type-dot {
    background: #6B7280;
  }

  .type-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: #E5E7EB;
  }

  .type-description {
    font-size: 0.75rem;
    color: #9CA3AF;
    line-height: 1.4;
    margin: 0;
    padding-left: 1rem;
  }

  .scale-bar {
    display: flex;
    height: 24px;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }

  .scale-zone {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.625rem;
    font-weight: 500;
    color: white;
  }

  .scale-zone.bearish {
    background: #EF4444;
  }

  .scale-zone.neutral-low {
    background: #F87171;
  }

  .scale-zone.neutral {
    background: #6B7280;
  }

  .scale-zone.neutral-high {
    background: #34D399;
  }

  .scale-zone.bullish {
    background: #10B981;
  }

  .interpretation-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .interpretation {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
  }

  .index-range {
    padding: 0.125rem 0.375rem;
    border-radius: 4px;
    font-weight: 500;
  }

  .index-range.bullish {
    background: #10B981;
    color: white;
  }

  .index-range.bearish {
    background: #EF4444;
    color: white;
  }

  .index-range.neutral {
    background: #6B7280;
    color: white;
  }

  .index-meaning {
    color: #9CA3AF;
  }

  .update-info {
    font-size: 0.75rem;
    color: #9CA3AF;
    line-height: 1.4;
    margin: 0;
  }
</style>
