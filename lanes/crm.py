"""
CRM lane (LIVE) — reads the published Google Sheet (fake Salesforce).

Returns prior-touch history + a deterministic DNC verdict + explicit gaps for
empty fields. Never fabricates: a blank cell becomes a stated gap.
"""
import csv
import io

import requests

from config import CRM_CSV_URL

_DNC_MARKERS = ["do not contact", "do-not-contact", "dnc",
                "legal review", "active deal", "legal hold"]


def _rows():
    r = requests.get(CRM_CSV_URL, timeout=30)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def _g(row, key):
    return (row.get(key) or "").strip()


def _match_account(row, domain, account_name):
    dom = _g(row, "Account Domain").lower()
    acct = _g(row, "What Account").lower()
    stem = domain.split(".")[0].lower() if domain else ""
    return bool(
        (domain and domain.lower() in dom)
        or (account_name and account_name.lower() in acct)
        or (stem and stem in acct)
    )


def run(domain=None, account_name=None, contact=None, mode="person"):
    try:
        rows = _rows()
    except Exception as e:
        return {"found": False, "dnc": {"flag": False, "reason": None},
                "text": "NO_CRM_HISTORY", "gaps": [f"CRM unreachable: {e}"]}

    acct_rows = [r for r in rows if _match_account(r, domain, account_name)]

    target = None
    if mode == "person" and contact:
        cl = contact.lower()
        for r in acct_rows:
            if cl in _g(r, "Name").lower() or cl in _g(r, "Their Job Title").lower():
                target = r
                break

    if target is None:
        # No matching contact row. General mode, or a net-new prospect.
        note = ("NO_CRM_HISTORY (net-new contact — no prior touch on record)"
                if mode == "person" else
                "General outreach — no specific contact selected.")
        return {"found": False, "dnc": {"flag": False, "reason": None},
                "text": note, "gaps": ["No prior CRM history for this contact"]}

    # DNC check (deterministic).
    status = _g(target, "Status / Do Not Contact")
    dnc_flag = any(m in status.lower() for m in _DNC_MARKERS)

    # Build history text + record gaps for empty fields.
    fields = [
        ("Title", "Their Job Title"), ("Owner", "Owner (Our Rep)"),
        ("Status", "Status / Do Not Contact"), ("Last touch", "Last Touch Date"),
        ("Prior email subject", "Prior Email Subject"),
        ("Prior email body", "Prior Email Body"),
        ("Meeting", "Meeting Title"), ("Transcript", "Meeting Transcript"),
    ]
    lines, gaps = [f"Contact: {_g(target, 'Name')}"], []
    for label, key in fields:
        val = _g(target, key)
        if val:
            lines.append(f"{label}: {val}")
        else:
            gaps.append(f"CRM field empty: {key}")

    return {"found": True,
            "dnc": {"flag": dnc_flag, "reason": status if dnc_flag else None},
            "contact_title": _g(target, "Their Job Title"),
            "text": "\n".join(lines), "gaps": gaps}
