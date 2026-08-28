---
name: ht-highlighter
description: Research a B2B account and draft grounded outreach. Use when the user gives a company domain (and optionally a contact name/title) and wants a research brief plus a first-draft email. Calls the HT Highlighter service, which pulls the account's SEC 10-K, CRM history, and other lanes, then returns a cited brief and a draft.
---

# HT Highlighter

Thin launcher. All research/orchestration lives in the Railway service — this
skill just collects inputs, calls it, and presents the result. Do NOT try to do
the research yourself.

## Inputs to collect

1. **domain** — the account's website domain, e.g. `snowflake.com` (required).
2. **contact** — a person's name or title (e.g. "Priya Raman" or "VP of
   Marketing"), OR the word "general" for account-level outreach.

If the user only gives a company name, ask for the domain. If they don't mention
a person, ask: "a specific person, or general company outreach?"

## How to run

Run the bundled script with the collected inputs:

```bash
HT_ENDPOINT="<your Railway URL>" python3 skill/call_ht.py --domain "<domain>" --contact "<contact or empty>" --mode "<person|general>"
```

- Use `--mode person` when a name/title was given, `--mode general` otherwise.
- `HT_ENDPOINT` is the deployed Railway base URL (no trailing slash). Locally it
  defaults to `http://localhost:8000`.

The script prints a JSON object: `{ cache, brief, draft }`.

## How to present the result

1. Lead with the account: name, public/private, and 3–5 top signals from
   `brief.signals` (show the claim + source; these are grounded, cite them).
2. List `brief.gaps` plainly under "What we don't know" — do not fill them in.
3. Then the email:
   - If `draft.needs_human` is true, DO NOT show a drafted email. Say it's held
     for a human and give `draft.reason` (e.g. the contact is Do-Not-Contact).
   - Otherwise show `draft.subject` and `draft.body`, and note it's a **draft for
     the rep to review and send** — never auto-send.
4. Mention whether it was a cache `hit` or `miss`.

Never invent facts beyond what the service returned.
