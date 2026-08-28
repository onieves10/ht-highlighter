"""
HT Highlighter — router (reference implementation).

Deterministic control flow here; the LLM only does language work. Deployed as a
FastAPI service on Railway; the Claude Desktop skill POSTs to /research.

Flow (matches the diagram):
  POST /research {domain, contact, mode, account_name?}
    1. account cache check (Postgres, <7 days)
       HIT  -> reuse cached account material (skip 10-K/news/site/LinkedIn)
       MISS -> run account lanes in parallel, cache the material
    2. contact lanes (CRM + prospect LinkedIn) ALWAYS run fresh
    3. synthesis (Claude) -> brief; account/DNC facts overridden in code
    4. email draft (Claude) -> draft; deterministic DNC short-circuit
"""
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from pydantic import BaseModel

import db
from lanes import edgar, crm, stubs
from llm import load_prompt, load_schema, render, call_json

app = FastAPI(title="HT Highlighter")


class ResearchRequest(BaseModel):
    domain: str
    contact: str | None = None          # name or title; null for general
    mode: str = "person"                # "person" | "general"
    account_name: str | None = None     # optional hint for EDGAR/CRM matching


@app.on_event("startup")
def _startup():
    db.init()


@app.get("/health")
def health():
    return {"ok": True}


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # a dead lane must not kill the run
        return {"error": str(e)}


def _build_account_material(domain, account_name):
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_edgar = ex.submit(_safe, edgar.run, domain, account_name)
        f_news = ex.submit(_safe, stubs.news, domain, account_name)
        f_site = ex.submit(_safe, stubs.site, domain, account_name)
        f_la = ex.submit(_safe, stubs.clay_account, domain, account_name)
        e = f_edgar.result()
        news, site, la = f_news.result(), f_site.result(), f_la.result()

    e = e if isinstance(e, dict) else {"is_public": False, "text": "ERROR", "cik": None}
    return {
        "account_name": e.get("name") or account_name or domain,
        "is_public": bool(e.get("is_public")),
        "cik": e.get("cik"),
        "edgar_text": e.get("text", "NO_PUBLIC_FILING"),
        "edgar_url": e.get("url"),
        "news_text": news if isinstance(news, str) else str(news),
        "site_text": site if isinstance(site, str) else str(site),
        "linkedin_account_text": la if isinstance(la, str) else str(la),
    }


def _build_contact_material(domain, account_name, contact, mode):
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_crm = ex.submit(_safe, crm.run, domain, account_name, contact, mode)
        f_lp = ex.submit(_safe, stubs.clay_prospect, contact, account_name)
        c, lp = f_crm.result(), f_lp.result()
    if not isinstance(c, dict):
        c = {"found": False, "dnc": {"flag": False, "reason": None},
             "text": "ERROR", "gaps": []}
    return {"crm": c, "linkedin_prospect_text": lp if isinstance(lp, str) else str(lp)}


def _synthesize(domain, req, material, contact_material):
    system, user_t = load_prompt("prompts/synthesis.md")
    crm_data = contact_material["crm"]
    linkedin = f'{material["linkedin_account_text"]}\n{contact_material["linkedin_prospect_text"]}'
    user = render(
        user_t,
        account_domain=domain,
        contact=req.contact or "general company outreach",
        mode=req.mode,
        edgar_output=material["edgar_text"],
        crm_output=crm_data.get("text", "NO_CRM_HISTORY"),
        news_output=material["news_text"],
        site_output=material["site_text"],
        linkedin_output=linkedin,
    )
    brief = call_json(system, user, schema=load_schema("brief"), max_tokens=8000)

    # Code owns the checkable facts — don't trust the LLM for these.
    brief["account"]["domain"] = domain
    brief["account"]["is_public"] = material["is_public"]
    brief["account"]["cik"] = material["cik"]
    if crm_data.get("dnc", {}).get("flag"):
        brief["dnc"] = crm_data["dnc"]
    return brief


def _draft_email(brief):
    # Deterministic DNC short-circuit — never even ask the model to draft.
    if brief.get("dnc", {}).get("flag"):
        return {"needs_human": True,
                "reason": brief["dnc"].get("reason") or "Do not contact (CRM status).",
                "subject": None, "body": None, "cited_facts": []}
    system, user_t = load_prompt("prompts/email.md")
    user = render(user_t, brief_json=json.dumps(brief, indent=2))
    try:
        return call_json(system, user, schema=load_schema("email"), max_tokens=2000)
    except Exception as e:
        # Never 500 the whole call over a draft hiccup — hold for a human.
        return {"needs_human": True,
                "reason": f"Draft generation failed validation ({e}); held for a human.",
                "subject": None, "body": None, "cited_facts": []}


@app.post("/research")
def research(req: ResearchRequest):
    domain = req.domain.strip().lower()

    material = db.get_account_material(domain)
    cache = "hit" if material else "miss"
    if material is None:
        material = _build_account_material(domain, req.account_name)
        db.set_account_material(domain, material)

    contact_material = _build_contact_material(
        domain, req.account_name or material["account_name"], req.contact, req.mode)

    brief = _synthesize(domain, req, material, contact_material)
    draft = _draft_email(brief)
    return {"cache": cache, "brief": brief, "draft": draft}
