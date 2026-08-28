# Company-site lane — Firecrawl (config, not a prose prompt)

STUBBED in the running demo; this is the production config. Firecrawl is a
scraper/crawler, so the "prompt" is really a scrape target + an extraction
schema, not a chat prompt. Firecrawl is used (vs. a general web LLM) because we
want deterministic pulls of specific pages we control the source of.

Crawl seed: https://{{account_domain}}
Include paths: /pricing, /product*, /solutions*, /customers*, /careers*, /blog*
Limit: ~25 pages. Format: markdown + Firecrawl LLM `extract`.

Extraction schema (Firecrawl `extract`):
```json
{
  "value_props": ["string"],
  "products": ["string"],
  "target_segments": ["string"],
  "pricing_signals": ["string"],
  "open_roles": ["string"],
  "recent_blog_titles": ["string"],
  "notable_customers": ["string"]
}
```

Rules baked into the extract instruction: only fill a field from text actually on
the page; leave unseen fields as empty arrays; capture the source URL per item so
synthesis can cite it. No inference beyond page content.
