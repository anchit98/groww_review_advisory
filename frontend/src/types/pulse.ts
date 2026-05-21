export type ReportingWindow = {
  start_date?: string;
  end_date?: string;
  lookback_weeks?: number;
};

export type ThemeIssueCount = {
  theme_name: string;
  linked_final_theme_id?: string;
  issue_count: number;
};

export type Theme = {
  theme_name: string;
  summary: string;
  bullet_points?: string[];
  linked_final_theme_id?: string;
};

export type UserQuote = {
  quote: string;
  review_id_hash: string;
  theme_name: string;
};

export type ActionIdea = {
  action: string;
  bullet_points?: string[];
  linked_theme: string;
};

export type WeeklyPulse = {
  opening_summary: string;
  top_themes: Theme[];
  user_quotes: UserQuote[];
  action_ideas: ActionIdea[];
  coverage_note?: string;
  theme_issue_counts?: ThemeIssueCount[];
};

export type StoreListingRatings = {
  fetched_at?: string;
  country?: string;
  disclaimer?: string;
  stores?: {
    play_store?: {
      source: string;
      label: string;
      average_rating: number;
      rating_count: number | null;
    };
    app_store?: {
      source: string;
      label: string;
      average_rating: number;
      rating_count: number | null;
    };
  };
};

export type RunSummary = {
  run_id: string;
  week_ending: string;
  phase2_run_id?: string;
  phase3_run_id?: string;
  status: string;
  phase1_status?: string;
  phase2_status?: string;
  phase3_status?: string;
  archived_at?: string;
  reporting_window?: ReportingWindow;
  reporting_label: string;
  source_mix?: Record<string, number>;
  publication?: { google_doc?: string; gmail_draft?: string };
  google_doc_url?: string;
  has_pulse?: boolean;
  store_listing_ratings?: StoreListingRatings | null;
};

export type RunDetail = RunSummary & {
  phase1?: {
    run_id?: string;
    status?: string;
    warnings?: string[];
    source_stats?: Record<string, unknown>;
    totals?: Record<string, unknown>;
  };
  phase2?: {
    run_id?: string;
    status?: string;
    run_started_at?: string;
    run_finished_at?: string;
    reporting_window?: ReportingWindow;
    source_mix?: Record<string, number>;
    review_counts?: Record<string, number>;
    coverage_notes?: string[];
    llm_provider?: { name?: string; model?: string; dry_run?: boolean };
    groq_limits?: Record<string, unknown>;
  };
  phase3?: {
    run_id?: string;
    status?: string;
    google_doc_url?: string;
    publication?: Record<string, string>;
    word_budget?: Record<string, unknown>;
  };
  links?: {
    google_doc?: string;
    weekly_note?: string;
  };
};
