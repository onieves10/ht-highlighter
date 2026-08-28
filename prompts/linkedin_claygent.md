# LinkedIn lanes — Clay / Claygent (prompt specs)

STUBBED in the running demo; real prompts for production. Clay is used here (not
a general web LLM) because it runs a waterfall across enrichment providers, which
is what LinkedIn-grade person data actually needs. Two prompts run:

## A. Account LinkedIn (company-level, cacheable)

Return, for {{account_name}} ({{account_domain}}), ONLY fields you can confirm
from the company's LinkedIn page or a provider:
- employee count + headcount trend (growing/flat/shrinking) if shown
- hiring focus (which functions they're hiring for now)
- recent company posts/announcements (last 60 days) with the post text
For anything not found, return the field as `null`. Do not estimate. Output JSON:
`{ "employees": ..., "headcount_trend": ..., "hiring_focus": [...], "recent_posts": [...] }`

## B. Prospect LinkedIn (contact-level, always fresh)

For {{prospect_name}} ({{prospect_title}}) at {{account_name}}, return ONLY
confirmable fields:
- current title + start date (tenure)
- prior role/company if a recent change (< 12 months)
- recent posts/activity (last 60 days) with text
- anything relevant to their function (e.g. marketing ops, growth)
Unknown -> `null`. No guessing about seniority, scope, or interests. Output JSON:
`{ "title": ..., "tenure_months": ..., "recent_change": ..., "recent_posts": [...] }`

Both feed synthesis as evidence; every non-null field must be provider-backed.
