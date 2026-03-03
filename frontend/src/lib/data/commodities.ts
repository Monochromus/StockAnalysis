export interface Commodity {
  symbol: string;
  name: string;
  category: 'energy' | 'agriculture' | 'metals' | 'crypto' | 'other';
  seasonalityScore: number;
}

export const COMMODITY_WATCHLIST: Commodity[] = [
  // Energie (nach Score sortiert)
  { symbol: 'NG=F', name: 'Erdgas (Natural Gas)', category: 'energy', seasonalityScore: 95 },
  { symbol: 'CL=F', name: 'Rohöl WTI (Crude Oil)', category: 'energy', seasonalityScore: 75 },
  // Agrar
  { symbol: 'ZC=F', name: 'Mais (Corn)', category: 'agriculture', seasonalityScore: 88 },
  { symbol: 'ZS=F', name: 'Sojabohnen (Soybeans)', category: 'agriculture', seasonalityScore: 82 },
  { symbol: 'KC=F', name: 'Kaffee (Coffee)', category: 'agriculture', seasonalityScore: 80 },
  { symbol: 'ZW=F', name: 'Weizen (Wheat)', category: 'agriculture', seasonalityScore: 78 },
  { symbol: 'CC=F', name: 'Kakao (Cocoa)', category: 'agriculture', seasonalityScore: 76 },
  { symbol: 'SB=F', name: 'Zucker (Sugar)', category: 'agriculture', seasonalityScore: 68 },
  // Metalle
  { symbol: 'GC=F', name: 'Gold', category: 'metals', seasonalityScore: 72 },
  { symbol: 'SI=F', name: 'Silber (Silver)', category: 'metals', seasonalityScore: 71 },
  { symbol: 'HG=F', name: 'Kupfer (Copper)', category: 'metals', seasonalityScore: 70 },
  { symbol: 'PL=F', name: 'Platin (Platinum)', category: 'metals', seasonalityScore: 65 },
  // Crypto
  { symbol: 'BTC-USD', name: 'Bitcoin', category: 'crypto', seasonalityScore: 85 },
  { symbol: 'ETH-USD', name: 'Ethereum', category: 'crypto', seasonalityScore: 80 },
];

export const CATEGORY_CONFIG = {
  energy: { label: 'Energie', color: '#f97316' },
  agriculture: { label: 'Agrar', color: '#22c55e' },
  metals: { label: 'Metalle', color: '#eab308' },
  crypto: { label: 'Krypto', color: '#8b5cf6' },
  other: { label: 'Sonstige', color: '#a8a29e' },
} as const;

export type CategoryKey = keyof typeof CATEGORY_CONFIG;

// Helper to get commodities by category
export function getCommoditiesByCategory(category: CategoryKey): Commodity[] {
  return COMMODITY_WATCHLIST.filter(c => c.category === category)
    .sort((a, b) => b.seasonalityScore - a.seasonalityScore);
}

// Get all categories with their commodities
export function getGroupedCommodities(): { category: CategoryKey; config: typeof CATEGORY_CONFIG[CategoryKey]; commodities: Commodity[] }[] {
  const categories: CategoryKey[] = ['energy', 'agriculture', 'metals', 'crypto'];
  return categories.map(category => ({
    category,
    config: CATEGORY_CONFIG[category],
    commodities: getCommoditiesByCategory(category),
  }));
}
