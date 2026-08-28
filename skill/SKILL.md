---
name: ht-highlighter
description: Research a B2B account and draft grounded outreach. Use when the user gives a company domain (and optionally a contact name/title) and wants a research brief plus a first-draft email. Calls the HT Highlighter service, which pulls the account's SEC 10-K, CRM history, and other lanes, then returns a cited brief and a draft.
---

# HT Highlighter

Thin launcher. All research/orchestration lives in the hosted service — this
skill just collects inputs, calls it, and presents the result. Do NOT try to do
the research yourself.

## Inputs to collect

1. **domain** — the account's website domain, e.g. `snowflake.com` (required).
2. **contact** — a person's name or title (e.g. "Priya Raman" or "VP of
   Marketing"), OR "general" for account-level outreach.

If only a company name is given, ask for the domain. If no person is mentioned,
ask: "a specific person, or general company outreach?"

## How to run

Make one HTTP POST to the service and read the JSON back. Use the code tool
(or a terminal) to run:

```bash
curl -s --max-time 180 \
  "https://ht-highlighter-production.up.railway.app/research" \
  -H "content-type: application/json" \
  -d '{"domain":"<DOMAIN>","contact":"<CONTACT or empty>","mode":"<person|general>"}'
```

- `mode` = `person` when a name/title was given, else `general`.
- The call can take ~90 seconds on a cache miss (full research). That's normal.
- Response is JSON: `{ cache, brief, draft }`.

## How to present the result

1. Lead with the account: name, public/private, and 3–5 top items from
   `brief.signals` — show each claim **with its source** (these are grounded, cite them).
2. List `brief.gaps` under "What we don't know" — do not fill them in.
3. Then the email:
   - If `draft.needs_human` is true, do NOT show a drafted email. Say it's held
     for a human and give `draft.reason` (e.g. the contact is Do-Not-Contact).
   - Otherwise show `draft.subject` and `draft.body`, and note it's a **draft for
     the rep to review and send** — never auto-send.
4. Mention whether it was a cache `hit` or `miss`.

Never invent facts beyond what the service returned.
