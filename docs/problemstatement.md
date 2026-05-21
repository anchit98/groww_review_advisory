# Problem Statement

Build a review advisory workflow that converts Groww's App Store and Play Store reviews into a concise weekly product signal for internal teams. The goal is to help Product, Growth, Support, and Leadership quickly understand what users are experiencing, what themes are trending, and what actions may be worth prioritizing next, without manually reading large volumes of reviews every week.

The solution should analyze recent public app reviews, summarize them into a one-page weekly pulse, save that summary in Google Docs, and prepare a draft email in Gmail for internal sharing. Google Docs and Gmail must be accessed through MCP server integrations, not through direct Google APIs or custom API/OAuth implementations.

## Who This Helps

- Product and Growth teams need a fast way to identify recurring friction points and improvement opportunities.
- Support teams need a clear view of what users are repeatedly reporting or appreciating.
- Leadership needs a lightweight weekly health snapshot that is easy to scan and act on.

## What Must Be Built

Fetch and store Groww reviews from the last 8 weeks using public store-accessible sources only. Each review record should include, where available, the rating, title, review text, and review date.

Process the imported reviews and group them into no more than 5 meaningful themes such as onboarding, KYC, payments, statements, withdrawals, bugs, performance, or support experience.

Before downstream analysis, normalize the dataset so that only English-language reviews are retained, emojis are removed, and reviews with 6 words or fewer are excluded from the working set.

Generate a weekly one-page note that includes:

- the top 3 themes for the week
- 3 representative user quotes
- 3 action ideas or recommendations for the internal team

Store the generated weekly note in Google Docs using an MCP server integration.

Create a draft email in Gmail using an MCP server integration. The email should contain the weekly note and be addressed to the user or a configured internal alias.

## Core Constraints

- Use only public store-accessible review sources. Do not scrape behind logins, use private sources, or depend on authenticated private APIs.
- Do not include personally identifiable information in any generated output. Usernames, email addresses, IDs, or any other sensitive identifiers must be excluded.
- Retain only English-language reviews in the normalized dataset.
- Remove emojis from normalized review text before later phases consume it.
- Exclude reviews with 6 words or fewer from the normalized dataset.
- Keep the summary scannable and concise, with a target length of 250 words or less.
- Limit thematic clustering to a maximum of 5 themes so the output remains focused and actionable.
- Google Docs and Gmail integration must happen through MCP servers rather than direct API calls.

## Expected Outcome

At the end of each weekly run, the user should have:

- a structured summary of recent app review sentiment and recurring issues
- a Google Doc containing the weekly pulse
- a ready-to-review Gmail draft for internal circulation

Recurring weekly execution is planned via **GitHub Actions** (scheduled cron plus manual re-run), as defined in Phase 4 of `docs/implementationplan.md` and `docs/architecture.md`.

## Success Criteria

The final output should help internal stakeholders understand what users are saying, what problems are most common, and what actions should be considered next, all in a format that can be reviewed in a few minutes.
