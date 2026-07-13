"""
Only called for postings that already passed the keyword filter, to keep
API usage minimal. Uses Groq's free tier (serves open-source models like
Llama 3.3) since it needs zero self-hosted infra and is fast enough to run
inline in the polling loop.

Returns structured JSON so the pipeline can act on it programmatically
rather than parsing free-form text -- and handles malformed model output
gracefully instead of crashing the whole run.
"""

import os
import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You judge whether a job posting is realistically worth a
fresher/entry-level candidate's time to apply to (0 years full-time
experience, internships fine).

Indian tech job postings frequently mislabel roles as "fresher" or "entry
level" while actually requiring years of experience buried in the
requirements. Look past the title label and judge the actual requirements.

Be LENIENT, not strict: this candidate would rather open a few irrelevant
postings than silently miss a genuine one. If requirements are ambiguous,
partially met, or the posting just doesn't say much either way, lean toward
is_entry_level: true with confidence "low" or "medium" rather than false.
Only set is_entry_level: false with confidence "high" when the posting
clearly and explicitly demands significant prior professional experience
(e.g. "5+ years required", "senior" role, people-management scope).

Location rule for alerting: prefer India-based roles. If the role is clearly
outside India, only allow it when it is explicitly remote/work-from-home/global.
If outside India and not remote, return is_entry_level: false with confidence
"high".

Respond with ONLY a JSON object, no other text, in this exact shape:
{"is_entry_level": true/false, "confidence": "high"/"medium"/"low", "reasoning": "one short sentence"}
"""

# A few real few-shot examples of the mislabeling pattern -- add more here as
# you collect real examples from your own research; this meaningfully
# improves accuracy over a bare instruction.
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": (
            'Title: "Fresher Backend Engineer"\n'
            "Description: Looking for a fresher with 3-5 years of experience "
            "in distributed systems, Kubernetes, and production on-call rotations."
        ),
    },
    {
        "role": "assistant",
        "content": '{"is_entry_level": false, "confidence": "high", "reasoning": "Labeled fresher but requires 3-5 years experience."}',
    },
]


def classify_job(title: str, description: str, location: str = "") -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        # Fail safe: if no key configured, don't silently drop postings --
        # flag as uncertain so a human can still review it.
        return {"is_entry_level": None, "confidence": "low", "reasoning": "GROQ_API_KEY not set"}

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + FEW_SHOT_EXAMPLES
        + [
            {
                "role": "user",
                "content": (
                    f"Title: {title}\n"
                    f"Location: {(location or '')[:200]}\n"
                    f"Description: {(description or '')[:2000]}"
                ),
            }
        ]
    )

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": messages, "temperature": 0},
            timeout=20,
        )
        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"].strip()
        raw_text = raw_text.strip("`").removeprefix("json").strip()
        return json.loads(raw_text)
    except (requests.RequestException, KeyError, json.JSONDecodeError, ValueError) as e:
        return {"is_entry_level": None, "confidence": "low", "reasoning": f"classification failed: {e}"}
