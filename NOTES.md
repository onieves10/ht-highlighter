# HT Highlighter — Notes

**Platform to deliver this on:** GitHub Repo w/ README first page as the primary docs.

---

## Scenario: SDR research is eating the day

**Scenario A**
- **Problem statement:** Your SDR team spends 3+ hours a day copy-pasting between LinkedIn, the CRM, news articles, and 10K filings to write a semi-personalized email. Reply rates are mediocre. Reps are burning out doing research instead of selling. The VP of Sales wants this fixed.
- **Your job:** Design an agentic workflow that handles the research and drafts outreach. Diagram the architecture. Write the key prompts. Explain how you'd measure whether it's working and how you'd roll it out to a team that's skeptical of AI-generated emails.

**Requirements from HT**
- Architecture diagram
- Tool choices
- 2–3 key prompts
- Measurement
- Rollout plan
- What can go wrong
- Bonus (not required): a working prototype in GH; a Loom walking through your thinking

---

## Outline notes (will talk through GH + app in Loom)

App/GH name: **HT Highlighter**

**Architecture notes**
- Whole repo to be pushed on GH.
- Deployed on Railway; needs a Postgres DB to store company-specific research and synthesized data outputs.
- Selecting Railway due to easy Postgres hosting alongside a deployed GH repo; yeet.
- Documentation on the GH repo primary README (home page).
- Diagram in the GH README.

**Tools to use for each research step**
- Firecrawl API - scrape company website (pricing, product, careers, blog).
- Perplexity Sonar Pro - news / recent events.
- Clay - person / LinkedIn data (title, tenure, job change, recent posts) because a waterfall is needed here.
- SEC's EDGAR API (10-K) w/ Unstructured OSS to extract + chunk the 10-K into JSON; Claude Sonnet synthesizes.
- Claude Sonnet - summary generation + email drafting.

**How it looks end to end**
1. Claude Skill triggers a webhook to kick off the research workflow that lives in Railway.
2. Next Q from system: "do you have a particular person in mind (name, or just position), or do you want general company outreach?"
3. Orchestrator first checks Postgres: "has this account already been researched in the past week?"
   - 4a. Yes? Serve cached brief, then run per-contact only: Claygent prospect search + CRM pull (prior emails/transcripts + DNC check) + draft (all if a prospect is named; if general, just return the brief).
   - 4b. No? Conduct a whole new search (+ prospect search, CRM pull, DNC check, and draft if a person is named), then cache the brief.
5. **5a. If a particular person was named:** router agent kicks off parallel research agents against the {account domain} variable and compiles the outputs to synthesize (strict output dictated in each prompt for consistency).
   - Research agent 1: Claygent account LinkedIn search.
   - Research agent 2: Claygent prospect LinkedIn search.
   - Research agent 3: Perplexity Sonar Pro news + blogs search.
   - Research agent 4: EDGAR API w/ Unstructured OSS and Sonnet, 10-K / SEC docs search.
   - Research agent 5: API call to Salesforce (my fake gsheets CRM here) to grab tasks and events (prior emails, prior call transcripts, prior meeting transcripts, any notes) & synthesize with Claude Sonnet.
6. **5b. If just general company research is needed:** same as 5a but drop the prospect LinkedIn search (agent 2).
7. Router agent synthesizes outputs into a clean summary (one output) and a clean email (another output). Prompts for both must have a strict output schema.
8. Outputs delivered to:
   - Claude chat.
   - Nooks (prospect record if a person; account record if just a company).
   - Slack channel (only the brief, but with a button to the Nooks account and/or contact, depending on whether a person was named).

**SDR experience**
- SDR chats with the Claude Skill (*meets them where they're at*).
- SDR answers the Q from the system on the particular person in mind.
- System output gets delivered into Claude, Nooks, and as a DM alert in a Slack channel from a custom app (*again, meet them where they're at*).

---

## Rollout plan

**Week 0 (before anyone touches it)**
- Grab the baseline: research time/rep/day, reply rate, positive reply rate, meetings booked. We need this to measure against later.

**Week 1 (small pilot)**
- 1-2 reps (known early adopters) - let them be the proof, make others jealous with success.
- Draft-only. Rep reviews and approves before anything sends.
- On-demand via Claude Desktop only: rep runs it themselves via the skill. Output received via Claude Desktop.
- Watch: research time saved, % of drafts usable, citations checking out.

**Week 3 (open it up)**
- Roll out to the wider team.
- Deliver into Nooks + Slack so it's where they already work.
- Turn on the holdout now that there's enough reps to split: half on the tool, half off, so we know the lift is real and not just a good month.
- Check the 2-week bar: 60%+ drafts sent with light edits, >=40% research time saved.

**Month 3 (scale + automate)**
- Automate the trigger via an account + prospect field in Nooks instead of running it by hand in Claude Desktop.
- Add pgVector once there's enough transcripts to actually search against.
- Check the lagging stuff: positive reply rate, meetings booked, pipeline vs the holdout.

**"My team won't use this"**
- It's draft-only. The rep reviews and approves before anything sends. It just writes the first draft.
- Start with one rep who's into it. If it saves them time and gets replies, the rest follow.
- Every claim in the summary brief carries a source URL + retrieved snippet, so they're not worried it'll make something up and embarrass them.
  - Low-confidence claims are not included.
- The email generator (which requires human review before sending) may only reference facts that carry a citation. Low-confidence facts get dropped.
- If a rep hates it, they turn it off. We watch usage in the backend so we know who's actually using it.
- DNC / active deal surfaces for human review.

---

## What can go wrong (and how it's handled)
- **empty CRM field:** leave it blank in the brief and say what's missing. Don't make stuff up to fill it.
- **private company (no EDGAR filing):** skip the 10-K step, note there's no public filing, use news + site instead.
- **DNC / active deal (Tom's row):** system sees the status and won't draft. Flags it for a human instead.
- **hallucination:** the email only uses facts that have a citation. Anything unsourced gets cut.
- **stale data:** cache re-runs research if it's older than a week. Last touch date tells us if old context still matters.
- **bad LLM output:** check it against the schema, retry once, if it's still junk error out instead of passing it on.
- **rep ignores it:** we can see usage in the backend and ask in an NPS survey. If they're not using it, we find out why.
- Human always stays in the loop to hit send; no auto-send.

---

## Measurement

**Baseline metrics**
- current research time/rep/day (~3 hrs)
- current reply rate
- positive-reply rate
- meetings booked/rep/week

**Pilot success bar**
- Define it up front, e.g. "in 2 weeks, expect 60%+ drafts sent with light edits, >=40% research time saved; in 2 months: reply rate up X% vs. holdout."

**Holdout / A-B**
- Split reps (or accounts) into tool vs no-tool. Without a control you can't attribute anything to the tool vs. seasonality.

**Leading indicators (move in week 1)**
- research minutes saved
- % drafts sent-as-is vs. edited vs. scrapped (can use Nooks API in CLI to pull email copy?)
- # accounts researched/day

**Lagging indicators (month 2-3)**
- positive reply rate
- meetings booked
- pipeline created

**Quality of outputs:** sample N drafts, % of personalization claims that trace to a real cited source. This catches quantity up while quality down.

**Qualitative**
- internal NPS w/ SDRs - survey "would you keep using it"
- Also look in the backend if they're actually using it.

---

## For this demo

**What's actually live (not hand-waved, it runs)**
- EDGAR API: real 10-K pull for the account.
- CRM call: reading my "SAILs4s CRM" Google Sheet published as CSV. Fake data pulled into synthesis.
- Real Claude call: synthesis + email draft against a strict schema, citations required, low-confidence facts dropped.
- Claude Skill: kicks it off and POSTs to my Railway endpoint - webhook trigger is real.
- Railway service: router.py deployed as a FastAPI app.
- Railway Postgres: the live cache (research_cache table).
  - On the Loom: first pull on Snowflake is a cache MISS (full research), the next contact at Snowflake is a cache HIT (skips the expensive 10-K work; contact draft still runs). That's the "has this been researched in the past week?" check, real.
- Keys handled right: ANTHROPIC_API_KEY lives as a Railway env var, DATABASE_URL auto-injected by Railway. Nothing secret in the repo.
- 3 prompts: email draft, summary synthesis, and Perplexity Sonar Pro web research prompt.

**What's not live yet (scoped out for the time box on purpose)**
- pgVector: not yet. Nothing to retrieve against at single-account scale; relevant once the transcript corpus grows.
- News + company-site lanes: stubbed (TODO: swap in Perplexity + Firecrawl). Prototype leans on EDGAR + CRM as the live lanes to stay at one paid key.
- LinkedIn / person enrichment (Clay waterfall): conceptual.
- Salesforce: faked with the Google Sheet (fake contacts, emails, transcripts I wrote).
- Delivery surfaces (Nooks, Slack DM app): conceptual. Output just returns in the Skill for now instead of fanning out.
- Parallel lanes: coded with a ThreadPoolExecutor so it matches the diagram, but only EDGAR + CRM return live data.
- Event-driven / batch trigger: I trigger manually via the Skill for now; scheduled/on-create is the month-3 version.
- Measurement numbers: target/illustrative, no real pilot has run. Those are the bars I'd hold it to, not results.

---

## Original prompt

**What this is**

We want to see how you'd actually approach building an AI-powered workflow for a real GTM problem. Pick one of the three scenarios below and go deep on it. We'd rather see a tight, opinionated take on one problem than a surface-level pass at all three.

**What we care about**
- Does your workflow actually work end-to-end?
- Are your prompts good? Structured, edge-case-aware, not just "summarize this account."
- How do you think about failure? Bad data, hallucinations, the CRM field that's empty 40% of the time.
- Can you phase a rollout? What's week 1 vs. month 3? How do you get a skeptical AE to actually use it?
- Is your thinking clear? We'll read this without you in the room. It needs to stand on its own.

**Pick a scenario**

**A. SDR research is eating the day** — Your SDR team spends 3+ hours a day copy-pasting between LinkedIn, the CRM, news articles, and 10K filings to write a semi-personalized email. Reply rates are mediocre. Reps are burning out doing research instead of selling. The VP of Sales wants this fixed. *Your job:* Design an agentic workflow that handles the research and drafts outreach. Diagram the architecture. Write the key prompts. Explain how you'd measure whether it's working and how you'd roll it out to a team that's skeptical of AI-generated emails.

**B. Pipeline reviews are a guessing game** — 200+ open opportunities. Every Monday, managers scroll through Salesforce trying to figure out which deals are real and which are quietly dying. By the time something gets flagged, it's usually too late. The CRO wants a system that catches slipping deals before humans do. *Your job:* Design a workflow that monitors deal health across signals (CRM activity, email engagement, call transcripts, calendar patterns) and surfaces risk before it's obvious. Show how it fits into the weekly sales rhythm — Slack alerts, pipeline review prep, the works.

**C. Sales-to-CS handoffs are broken** — Every time a deal closes, the CS team starts from scratch. The "handoff" is a Slack message and a half-filled Google Doc. Customers repeat themselves on the kickoff call. Onboarding slips. The VP of CS is frustrated and the data exists somewhere — in Gong recordings, email threads, the CRM — but nobody's stitching it together. *Your job:* Design a workflow that pulls deal context from wherever it lives and generates a structured onboarding plan. Think about what the CS team actually needs on day one, not just a data dump. How do you measure whether handoffs are getting better?

**What to include** (don't need to follow this order or use these exact headings — just make sure the thinking is in there)
- **Architecture diagram** — a visual of the workflow: what triggers it, where data comes from, what the AI does at each step, and what the output looks like.
- **Tool choices** — what's powering each piece and why? Be specific.
- **2–3 key prompts** — the actual prompts for the critical AI steps. The real thing, not pseudocode.
- **Measurement** — how do you know this is working? Baseline? Successful pilot after 2 weeks, 2 months? Quantitative and qualitative.
- **Rollout plan** — what ships first? How do you phase it? If a sales leader says "my team won't use this," what's your move?
- **What can go wrong** — bad data, hallucinations, the field that's empty half the time, the rep who ignores the tool. How does the system handle it? Where do humans stay in the loop?
- **Bonus (not required):** a working prototype, a cost/ROI estimate, or a Loom.

**Ground rules**
- **Use AI.** Use it to research, draft, diagram, think. The bar is that you can explain and defend everything.
- **Be opinionated.** "It depends" is not a design. Pick a direction, justify it, note the tradeoffs.
- **Stay in the time box.** If you hit 3 hours and aren't done, stop and send what you have.
- **Questions are welcome.** If something's ambiguous, ask.
