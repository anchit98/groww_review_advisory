# Groww VoC AI Pulse Platform

## Overview

Groww VoC AI Pulse Platform is an AI-powered Voice of Customer (VoC) intelligence system designed to continuously monitor, analyze, and summarize customer feedback from the Groww mobile application ecosystem.

The platform automatically scrapes reviews from both the Google Play Store and Apple App Store on a scheduled weekly basis, identifies emerging customer pain points and product sentiment trends, and generates leadership-ready summaries using LLM-powered thematic analysis.

The system combines data ingestion, NLP-driven issue detection, automated reporting workflows, and a full-stack analytics dashboard into a single end-to-end product intelligence platform.

---

# Problem Statement

Consumer-facing fintech products receive thousands of reviews across app ecosystems every week. Manually reading, categorizing, and prioritizing this feedback is:

- Time-consuming
- Non-scalable
- Inconsistent across analysts
- Difficult to operationalize quickly

Product, Support, and Leadership teams often struggle to answer questions like:

- What are the top recurring customer complaints this week?
- Are sentiment trends improving or declining?
- Which product features are causing the most friction?
- What issues are escalating rapidly?
- What action items should teams prioritize immediately?

This project solves that problem through automated AI-driven review intelligence.

---

# Key Features

## Automated Weekly Review Scraping

- Scrapes latest reviews from:
  - Google Play Store
  - Apple App Store
- Scheduled weekly refresh pipeline
- Captures:
  - Review text
  - Rating
  - Date
  - Platform source
  - Version metadata (where available)

---

## AI-Powered Theme & Issue Detection

After ingestion, reviews are processed through an LLM pipeline powered by:

- Groq API
- Llama Versatile model

The system automatically identifies:

- Recurring complaint themes
- Sentiment patterns
- Product pain points
- Feature-level issues
- Escalation signals
- Customer frustration indicators

Examples:
- Login failures
- KYC issues
- Portfolio loading delays
- Payment failures
- UI/UX friction
- Order execution concerns

---

## Weekly Leadership Pulse Generation

The platform generates:

### Detailed Executive Report (Google Docs)

A structured document containing:

- Weekly summary
- Emerging themes
- Top complaints
- Sentiment analysis
- Trend comparison
- Priority issues
- Actionable recommendations

---

### Leadership Email Draft (Gmail)

A concise executive summary generated automatically and saved as a Gmail draft ready to send.

The email includes:
- Key highlights
- Top escalations
- Critical customer risks
- Recommended focus areas

---

## MCP Server Integration

Built a custom MCP (Model Context Protocol) server to integrate AI workflows directly with:

- Google Docs
- Gmail

This enables the AI system to:
- Create/update reports automatically
- Draft executive emails
- Maintain workflow automation without manual intervention

---

## Full-Stack Dashboard

A frontend dashboard provides real-time visibility into:

- Weekly review trends
- Top issue categories
- Sentiment distribution
- Review volumes
- AI-generated insights
- Historical comparisons

### Deployment

| Layer | Platform |
|---|---|
| Frontend | Vercel |
| Backend | Render |

---

# System Architecture

```text
App Store / Play Store Reviews
                ↓
        Weekly Scraper Pipeline
                ↓
        Data Cleaning & Parsing
                ↓
       AI Theme Detection Engine
        (Groq + Llama API)
                ↓
    Insight & Action Item Generator
                ↓
 ┌──────────────┴──────────────┐
 ↓                             ↓
Google Docs Report      Gmail Draft Summary
(MCP Integration)       (MCP Integration)
                ↓
         Frontend Dashboard
