# Phase 5 Design Reference Mapping

Source assets live in the repo at:

`frontend references/stitch_groww_advisory_dashboard/`

| Asset | Path | Role |
|-------|------|------|
| Design system tokens | `executive_precision_dark/DESIGN.md` | Colors, typography, spacing, component rules |
| Executive Summary screen | `groww_review_advisory_summary_dark_mode/screen.png` | Route `/` (Summary) |
| Top Themes screen | `groww_review_advisory_themes_detail/screen.png` | Route `/themes` |
| Representative Quotes screen | `groww_review_advisory_quotes_detail/screen.png` | Route `/quotes` |

Stitch project name: **Groww Review Advisory** — dark executive dashboard branded as **Command Center / Advisory Portal** with **Executive Insights** section headers.

---

## Design system: Executive Precision Dark

Implement as **CSS custom properties** (and Tailwind theme extension) sourced from `DESIGN.md`.

### Core tokens (use verbatim)

| Token | Value | Usage |
|-------|-------|--------|
| `background` / `surface` | `#131313` | App shell |
| `surface-container-low` | `#1c1b1b` | Sidebar, sunken areas |
| `surface-container` | `#201f1f` | Cards |
| `surface-container-high` | `#2a2a2a` | Hover / elevated cards |
| `on-surface` | `#e5e2e1` | Primary text |
| `on-surface-variant` | `#c2c6d6` | Secondary text |
| `outline` / `outline-variant` | `#8c909f` / `#424754` | Borders |
| `primary` | `#adc6ff` | Links, focus, accents |
| `primary-container` | `#4d8eff` | Primary buttons |
| `tertiary` | `#ffb786` | Warning accents |
| `error` | `#ffb4ab` | Critical / negative sentiment |

### Typography

- Font: **Inter** (Google Fonts or self-hosted).
- Scales from `DESIGN.md`: `display-lg`, `headline-lg`, `headline-md`, `body-lg`, `body-md`, `label-md`, `label-sm`.
- Quotes: italic `body-md` or `body-lg`.
- Review IDs: monospace, `label-sm`.

### Layout

- **8px grid**; gutters 24px desktop, 16px mobile.
- Max content width: **1280px** (`container-max`).
- Border radius: **4px** default (`rounded` / `sm`); **8px** for large cards (`rounded-lg`).
- Depth via **tonal layering** and 1px outlines — avoid heavy shadows.

### Semantic severity chips (UI convention)

Mockups use three severity labels on themes. Map in the frontend (until Phase 2 exports them explicitly):

| Theme rank (top 3) | Chip label | Color role |
|--------------------|------------|------------|
| 1 | `CRITICAL` | `error` / salmon |
| 2 | `WARNING` | `tertiary` / orange |
| 3 | `CONCERN` | `outline-variant` / muted grey |

Quote cards use category tags aligned to the linked theme’s severity (e.g. `CRITICAL THEME`, `TECHNICAL ISSUE`, `FINANCIAL FRICTION`) — derive label from theme name keywords or the same rank mapping.

### Components (from design system)

- **Sidebar nav**: icon + label; active item uses `surface-container-high` + subtle primary tint.
- **Cards**: `surface-container` background, 1px `outline-variant` border.
- **Chips**: 10% opacity semantic background, solid text (WCAG AA on dark).
- **Buttons**: primary solid `primary-container`; secondary ghost with border; 4px radius.
- **Icons**: Lucide-style line icons (recommend `lucide-react`).

---

## Screen → route → data mapping

### 1. Summary (`/`)

**Reference:** `groww_review_advisory_summary_dark_mode/screen.png`

| UI block | Data source | Notes |
|----------|-------------|--------|
| Reporting period | `run_metadata.reporting_window` | Format: `March 16 - May 11, 2026` |
| Overall Sentiment | Derived | If all top themes `negative` → label **Negative** + short line from `opening_summary` first sentence |
| Top Themes (3) | `weekly_pulse.top_themes[]` + matching quote | Join first quote per theme by `theme_name` |
| Theme chips | Rank mapping | See severity table above |
| Actionable Insights (3) | `weekly_pulse.action_ideas[]` | Title = shorten `action`; body = full `action` or linked theme context |
| Coverage | `weekly_pulse.coverage_note` | Footer or banner below header |

### 2. Themes (`/themes`)

**Reference:** `groww_review_advisory_themes_detail/screen.png`

| UI block | Data source | Notes |
|----------|-------------|--------|
| Theme cards | `top_themes[]` | Full `summary` as body copy |
| Featured card | Theme rank 1 | Wider layout; text only |
| Prevalence % | **Excluded** | Do not build — ignore in Stitch reference |
| Impact Analysis card | **Excluded** | Do not build — ignore in Stitch reference |
| Icons per theme | Static map | e.g. support → headset, performance → gauge, fees → wallet |

### 3. Quotes (`/quotes`)

**Reference:** `groww_review_advisory_quotes_detail/screen.png`

| UI block | Data source | Notes |
|----------|-------------|--------|
| Quote list | `weekly_pulse.user_quotes[]` | Max 3 |
| Theme title | `theme_name` | Left column |
| Review ID | `review_id_hash` | Show first 16 chars + tooltip full hash |
| Quote text | `quote` | Italic, right column |
| Category tag | Derived | From theme severity mapping |

### 4. Operator views (not in Stitch mocks — extend nav)

| Route | Purpose |
|-------|---------|
| `/runs` | Run history table (Phase 1–3 metadata) |
| `/runs/:runId` | Ingestion stats, Groq budget, publication status |

Add a fourth sidebar item **Runs** (or footer link **Operations**) so stakeholder and operator flows share one shell.

---

## Schema gaps to close before / during implementation

| Mock element | Current `weekly_pulse.json` | Recommendation |
|--------------|----------------------------|----------------|
| Per-theme `sentiment` | Missing | Add `sentiment` on each `top_themes[]` item in Phase 2 export (data exists in consolidation) |
| Overall sentiment headline | Missing | Compute client-side from themes or add `overall_sentiment` field |
| Prevalence % | N/A | **Out of scope** — not in UI or pipeline |
| Impact Analysis | N/A | **Out of scope** — not in UI or pipeline |
| Short action titles | Long `action` strings | UI truncates for card title; full text on expand |

---

## Brand copy (from mocks)

- App chrome: **Command Center** / **Advisory Portal**
- Section label: **GROWW REVIEW ADVISORY** (small caps)
- Page family: **Executive Insights**
- Page titles: **Executive Summary**, **Top Themes**, **Representative Quotes**

Use internal advisory tone; do not surface “AI generated” language in the UI.
