"""
LLM + prompt/schema helpers.

- load_prompt() / load_schema() read the deliverable files so prompts have a
  single source of truth (the .md files in prompts/).
- call_json() forces valid, schema-conformant JSON with ONE repair retry, then
  fails loud. This is the "bad LLM output" guard from the failure-modes plan.
"""
import json
import re
from pathlib import Path

from anthropic import Anthropic
from jsonschema import validate as _jsonschema_validate, ValidationError

from config import ANTHROPIC_API_KEY, MODEL

BASE = Path(__file__).resolve().parent
_client = Anthropic(api_key=ANTHROPIC_API_KEY)


# ---------- prompt + schema loading ----------

def load_prompt(rel_path):
    """Split a prompt .md into (system, user_template).

    Convention: everything between '## SYSTEM' and '## INPUT' is the system
    prompt (includes the '## OUTPUT' section); the body after the '## INPUT'
    header is the user template with {{placeholders}}.
    """
    text = (BASE / rel_path).read_text()
    sys_start = text.index("## SYSTEM") + len("## SYSTEM")
    inp_idx = text.index("## INPUT", sys_start)  # matches '## INPUT' and '## INPUTS'
    system = text[sys_start:inp_idx].strip()
    after = text[inp_idx:]
    user_template = after[after.index("\n"):].strip()
    return system, user_template


def load_schema(name):
    return json.loads((BASE / "schemas" / f"{name}.schema.json").read_text())


def render(template, **kwargs):
    out = template
    for k, v in kwargs.items():
        out = out.replace("{{%s}}" % k, "" if v is None else str(v))
    return out


# ---------- Claude calls ----------

def call_text(system, user, max_tokens=1500):
    resp = _client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def _extract_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    return raw[start:end + 1]


def _parse_validate(raw, schema):
    js = _extract_json(raw)
    if js is None:
        return None, "no JSON object found in output"
    try:
        obj = json.loads(js)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    if schema is not None:
        try:
            _jsonschema_validate(obj, schema)
        except ValidationError as e:
            return None, f"schema error at {list(e.path)}: {e.message}"
    return obj, None


def call_json(system, user, schema=None, max_tokens=2000):
    """Return a validated dict. One repair retry, then raise."""
    messages = [{"role": "user", "content": user}]
    err = None
    for _ in range(2):
        resp = _client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system, messages=messages,
        )
        raw = resp.content[0].text
        obj, err = _parse_validate(raw, schema)
        if obj is not None:
            return obj
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content":
            f"That output was invalid ({err}). Return ONLY corrected JSON that "
            f"matches the schema. No prose, no code fence."})
    raise ValueError(f"LLM JSON still invalid after repair retry: {err}")
