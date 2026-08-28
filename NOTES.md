# HT Highlighter — scratch-paper outline notes

(~1.5 hrs to spill + compile. Raw thinking, left mostly as-is on purpose.)

App / GH name: HT Highlighter

## Architecture notes
- Whole repo pushed on GH.
- Deployed on Railway; needs a Postgres DB to store company-specific research and synthesized data outputs.
- Selecting Railway due to easy Postgres hosting alongside a deployed GH repo; yeet.
- Documentation on the GH repo primary readme (home page).
- Diagram in the GH readme.

## Tools to use for each research step
- Firecrawl API: scrape company website (pricing, product, careers, blog).
- Perplexity Sonar Pro: news / recent events.
- Clay: person / LinkedIn data (title, tenure, job change, recent posts), because a waterfall is needed here.
- SEC's EDGAR API (10-K) with Unstructured OSS to extract + chunk the 10-K into JSON; Claude Sonnet synthesizes.
- Claude Sonnet: summary generation + email drafting.

## How it looks end to end
1. Claude Skill triggers a webhook to kick off the research workflow that lives in Railway.
2. Next Q from system: "do you have a particular person in mind (name, or just position), or do you want general company outreach?"
3. Edge function first checks Postgres: "has this account already been researched in the past week?"
4a. Yes? Serve cached brief, then run per-contact only: Claygent prospect search + CRM pull (prior emails/transcripts + DNC check) + draft (all if a prospect is named; if general, just return the brief).
4b. No? Conduct a whole new search (+ prospect search, CRM pull, DNC check, and draft if a person is named), then cache the brief.
5a. If a particular person is named: router agent kicks off parallel research agents against the {account domain} variable and compiles the outputs to synthesize (strict output dictated in each prompt for consistency).
   - Research agent 1: Claygent account LinkedIn search.
   - Research agent 2: Claygent prospect LinkedIn search.
   - Research agent 3: Perplexity Sonar Pro news + blogs search.
   - Research agent 4: EDGAR API with Unstructured OSS and Sonnet, 10-K / SEC docs search.
   - Research agent 5: API call to Salesforce (my fake gsheets CRM here) to grab tasks and events (prior emails, prior call transcripts, prior meeting transcripts, any notes) and synthesize with Claude Sonnet.
5b. If just general company research is needed: same as 5a but drop the prospect LinkedIn search (agent 2).
6. Router agent synthesizes outputs into a clean summary (one output) and a clean email (another output). Prompts for both must have a strict output schema.
7. Outputs delivered to:
   - Claude chat.
   - Nooks (prospect record if a person; account record if just a company).
   - Slack channel (only the brief, but with a button to the Nooks account and/or contact, depending on whether a person was named).

## Additional rules
To install confidence:
- Every claim in the SUMMARY brief carries a source URL + retrieved snippet (an evidence ledger in the schema).
- The email generator (which requires human review before sending) may only reference facts that carry a citation. Low-confidence facts get dropped.

SDR experience:
- SDR chats with the Claude Skill (meets them where they're at).
- SDR answers the Q from the system on the particular person in mind.
- System output gets delivered into Claude, Nooks, and as a DM alert in a Slack channel from a custom app (again, meet them where they're at).

## Rollout plan
Phase it. Start small and expand.

Week 0 (before anyone touches it):
- grab the baseline: research time/rep/day, reply rate, positive reply rate, meetings booked. we need this to measure against later.

Week 1 (small pilot):
- 1-2 reps who are into AI. let them be the proof.
- draft-only. rep reviews and approves before anything sends.
- on-demand only: rep runs it themselves via the skill. no automation yet so they stay in control.
- watch: research time saved, % of drafts usable, citations checking out.

Month 1 (open it up):
- roll out to the wider team.
- deliver into Nooks + Slack so it's where they already work.
- turn on the holdout now that there's enough reps to split: half on the tool, half off, so we know the lift is real and not just a good month.
- check the 2-week bar: 60%+ drafts sent with light edits, >=40% research time saved.

Month 3 (scale + automate):
- automate the trigger (new lead, sequence enrollment, or an overnight batch for tomorrow's call list) instead of running it by hand.
- add pgVector once there's enough transcripts to actually search against.
- check the lagging stuff: positive reply rate, meetings booked, pipeline vs the holdout.

## "My team won't use this"
- it's draft-only. the rep reviews and approves before anything sends. it just writes the first draft.
- start with one rep who's into it. if it saves them time and gets replies, the rest follow.
- every claim in the brief shows its source, so they're not worried it'll make something up and embarrass them.
- if a rep hates it, they turn it off. we watch usage in the backend so we know who's actually using it.

## What can go wrong (and how it's handled)
- empty CRM field: leave it blank in the brief and say what's missing. don't make stuff up to fill it.
- private company (no EDGAR filing): skip the 10-K step, note there's no public filing, use news + site instead.
- DNC / active deal (Tom's row): system sees the status and won't draft. flags it for a human instead.
- hallucination: the email only uses facts that have a citation. anything unsourced gets cut.
- stale data: cache re-runs research if it's older than a week. last touch date tells us if old context still matters.
- bad LLM output: check it against the schema, retry once, if it's still junk error out instead of passing it on.
- rep ignores it: we can see usage in the backend and ask in an NPS survey. if they're not using it, we find out why.
- human always stays in the loop to hit send; no auto-send.

## Measurement
Baseline metrics:
- current research time/rep/day (~3 hrs)
- current reply rate
- positive-reply rate
- meetings booked/rep/week

Pilot success bar:
- define it up front, e.g. "in 2 weeks, expect 60%+ drafts sent with light edits, >=40% research time saved; in 2 months: reply rate up X% vs. holdout."

Holdout / A-B:
- split reps (or accounts) into tool vs no-tool. Without a control you can't attribute anything to the tool vs. seasonality.

Leading indicators (move in week 1):
- research minutes saved
- % drafts sent-as-is vs. edited vs. scrapped
- # accounts researched/day

Lagging indicators (month 2-3):
- positive reply rate
- meetings booked
- pipeline created

Quality of outputs:
- sample N drafts, % of personalization claims that trace to a real cited source. This catches quantity up while quality down.

Qualitative:
- internal NPS with SDRs, survey "would you keep using it"
- also look in the backend if they're actually using it

## For this demo
What's actually live in this demo (not hand-waved, it runs):
- EDGAR API: real 10-K pull for the account.
- CRM call: reading my "SAILs4s CRM" Google Sheet published as CSV. Fake data pulled into synthesis.
- Real Claude call: synthesis + email draft against a strict schema, citations required, low-confidence facts dropped.
- Claude Skill: kicks it off and POSTs to my Railway endpoint. Webhook trigger is real.
- Railway service: router.py deployed as a FastAPI app.
- Railway Postgres: the live cache (research_cache table). On the Loom: first pull on Snowflake is a cache MISS (full research), the next contact at Snowflake is a cache HIT (skips the expensive 10-K work, contact draft still runs). That's the "has this been researched in the past week?" check, real.
- Keys handled right: ANTHROPIC_API_KEY lives as a Railway env var, DATABASE_URL auto-injected by Railway. Nothing secret in the repo.

What's not live yet (scoped out for the time box on purpose, didn't wire it before hitting 3 hrs):
- pgVector: not yet. Nothing to retrieve against at single-account scale; relevant once the transcript corpus grows.
- News + company-site lanes: stubbed (TODO: swap in Perplexity + Firecrawl). Prototype leans on EDGAR + CRM as the live lanes to stay at one paid key.
- LinkedIn / person enrichment (Clay waterfall): conceptual.
- Salesforce: faked with the Google Sheet (fake contacts, emails, transcripts I wrote).
- Delivery surfaces (Nooks, Slack DM app): conceptual. Output just returns in the Skill for now instead of fanning out.
- Parallel lanes: coded with a ThreadPoolExecutor so it matches the diagram, but only EDGAR + CRM return live data.
- Event-driven / batch trigger: I trigger manually via the Skill for now; scheduled/on-create is the month-3 version.
- Measurement numbers: target/illustrative, no real pilot has run. Those are the bars I'd hold it to, not results.
