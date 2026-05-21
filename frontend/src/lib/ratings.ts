export type StoreListingRating = {
  source: string;
  label: string;
  average_rating: number;
  rating_count: number | null;
  fetched_at?: string;
};

export type StoreListingRatings = {
  fetched_at?: string;
  country?: string;
  disclaimer?: string;
  stores?: {
    play_store?: StoreListingRating;
    app_store?: StoreListingRating;
  };
};

export function formatRatingCount(count: number | null | undefined): string {
  if (count == null) return "—";
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return count.toLocaleString();
}

export function starFillPercent(rating: number): number {
  return Math.max(0, Math.min(100, (rating / 5) * 100));
}
