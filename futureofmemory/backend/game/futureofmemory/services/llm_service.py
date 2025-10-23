import os
import re
import json
import typing
from typing import Any, Dict

import boto3
import botocore
from langchain.prompts import PromptTemplate

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
ENDPOINT_NAME = os.getenv("SM_ENDPOINT_NAME", "neuro-rag-rt")
MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "1536"))
MAX_TOTAL_TOKENS = int(os.getenv("MAX_TOTAL_TOKENS", "2048"))

_boto = boto3.Session(region_name=AWS_REGION)
_rt = _boto.client("sagemaker-runtime")

# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────


def _approx_tokens(s: str) -> int:
    # very rough heuristic: ~4 chars per token
    return max(1, len(s) // 4)


def _clip_chars(s: str, limit_chars: int) -> str:
    """Clip long strings to a character limit, cutting at newline if possible."""
    if len(s) <= limit_chars:
        return s
    return (s[:limit_chars].rsplit("\n", 1)[0]) or s[:limit_chars]


def _clip_context(text: str, max_chars: int = 1500) -> str:
    """Trim long RAG context so total prompt stays within token limit."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " ..."


def _extract_json_block(text: str) -> Dict[str, Any] | None:
    """
    Extract the last valid JSON object from a text output.
    Prefers one containing 'scenario_text' or 'choices' keys.
    """
    if not isinstance(text, str):
        return None

    # Clean code fences
    t = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    t = re.sub(r"\n?```$", "", t).strip()

    candidates = []
    stack = []
    for i, ch in enumerate(t):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            start = stack.pop()
            candidate = t[start: i + 1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    candidates.append(obj)
            except Exception:
                pass

    # Prefer the last valid JSON with keys we expect
    for obj in reversed(candidates):
        if "scenario_text" in obj or "choices" in obj:
            return obj
    return candidates[-1] if candidates else None

# ──────────────────────────────────────────────────────────────────────────────
# Realtime SageMaker call
# ──────────────────────────────────────────────────────────────────────────────


def invoke_sync_tgi(
    prompt: str,
    *,
    max_new_tokens: int = 300,
    temperature: float = 0.7,
) -> str:
    """Fixed: makes sync behave exactly like async (works for TGI models)."""
    import json

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 50,
            "repetition_penalty": 1.05,
            "return_full_text": True,
            "stop": ["\n\n\n"]
        },
        "stream": False
    }

    response = _rt.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(payload).encode("utf-8"),
    )

    raw = response["Body"].read().decode("utf-8", errors="replace")

    try:
        data = json.loads(raw)
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
    except Exception:
        pass

    return raw

# ──────────────────────────────────────────────────────────────────────────────
# JSON generator (sync)
# ──────────────────────────────────────────────────────────────────────────────


def generate_json(
    prompt: str,
    *,
    max_new_tokens: int = 600,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    prompt = _clip_chars(prompt, 4000)

    # --- Dynamic token safety adjustment ---
    tokens_in = _approx_tokens(prompt)
    max_allowed = MAX_TOTAL_TOKENS - tokens_in - 50
    safe_new_tokens = min(max_new_tokens, max(50, max_allowed))

    """
    Realtime JSON generator. Returns a dict with:
    - keys from the model (scenario_text, choices, citations) when possible
    - or {"raw_text": "..."} fallback.
    """
    raw = invoke_sync_tgi(
        prompt, max_new_tokens=max_new_tokens, temperature=temperature)

    print("==== RAW MODEL OUTPUT START ====")
    print(raw)
    print("==== RAW MODEL OUTPUT END ====")

    # If it's JSON already:
    if isinstance(raw, dict):
        return raw
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    obj = _extract_json_block(raw)
    if isinstance(obj, dict):
        return obj

    return {"raw_text": raw}

# ──────────────────────────────────────────────────────────────────────────────
# Back-compat shims for code that still expects async-style functions
# ──────────────────────────────────────────────────────────────────────────────


def start_generation(prompt: str, max_new_tokens=200, temperature=0.7) -> Dict[str, Any]:
    """
    Back-compat: used to kick off async and return an S3 OutputLocation.
    Now we run synchronously and return the parsed dict immediately.
    """
    return generate_json(prompt, max_new_tokens=max_new_tokens, temperature=temperature)


def collect_generation(output_location: typing.Any, timeout_s: int | None = None) -> Dict[str, Any]:
    """
    Back-compat: used to poll S3 and return parsed output.
    Now, if 'output_location' is already a dict (from start_generation), just return it.
    """
    if isinstance(output_location, dict):
        return output_location
    # If someone passes a string by mistake, try to parse it as JSON fallback:
    if isinstance(output_location, str):
        try:
            obj = json.loads(output_location)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return {"raw_text": output_location}
    return {"raw_text": str(output_location)}

# ──────────────────────────────────────────────────────────────────────────────
# Prompts & rules
# ──────────────────────────────────────────────────────────────────────────────

# defines system rules that the LLM must adhere to
SYSTEM_RULES = {
    "rules": [
        "Neurotechnology implants have become popular by 2075.",
        "Memory manipulation is technically possible but ethically controversial.",
        "Each year, one major neurotech-related event happens.",
        "Players always receive exactly 3 choices.",
    ],
    "constraints": [
        "Scenarios must stay realistic for neurotechnology research.",
        "Avoid academic or technical language. Keep it simple, clear, and engaging."
    ],
    "factions": {
        "rightists": "Sees memory as a right: not for sale, need explicit consent, revocable at any time.",
        "responsibilists": "Sees memory as a common responsibility. The community co-governs and cares for memory together.",
        "resourceists": "Sees memory as a resource. Memories can be traded, sold, and used for profit."
    }
}

# defines the base prompt template for scenario generation
BASE_PROMPT = """
Follow these fixed system rules (do not change them):
{system_rules}

Here is some background information retrieved from research on neurotechnology or memory manipulation.
Use it as inspiration or factual grounding where it fits naturally, but you should expand beyond it if needed for
clarity, realism, or storytelling flow.
Context:
{context}
"""

first_scenario_and_choices_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer and choice maker.
    1. Write the first ~50 word scenario for the year {year}.
    2. Then, propose 3 realistic player choices that follow from it.
    
    The chosen faction: {faction} should shape the perspective and concerns in the story.
    Since this is the opening, introduce the world vividly:
    - Show a dramatic neurotech incident (scandal, invention, protest, accident etc).
    - Make it personal and emotional, not abstract or academic.

    Respond with **only** a valid JSON object.
    Do not include explanations, commentary, or text outside the JSON.
    
    Output JSON:
    {{
        "scenario_text": "...",
        "choices": [
            {{"id": 1, "text": "..."}},
            {{"id": 2, "text": "..."}},
            {{"id": 3, "text": "..."}}
        ],
        "citations": [{citations}]
    }}
    """
)

# defines the prompt template for generating the next scenario and choices
next_scenario_and_choices_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer and choice maker.
    
    Strict rules:
    1. Write a 40-50 word scenario for the year {year}. Start with: "In {year}, ...".
    2. Then, propose 3 realistic player choices that follow naturally from it.
    3. The scenario must directly continue from the previous scenario and the player's chosen response. Do not restart. Do not ignore.

    Previous scenario:
    "{previous_scenario}"

    Player's chosen response:
    "{chosen_choice}"

    Escalate the story:
    - Show unexpected consequences of the choice (e.g. backlash, unintended effects, new actors entering the scene).
    - Add variety: not just scandals and protests, but also breakthroughs, accidents, personal tragedies, underground movements, black markets etc.
    - Make it emotional and vivid, like a human drama

    Respond with **only** a valid JSON object.
    Do not include explanations, commentary, or text outside the JSON.

    Output JSON ONLY:
    {{
        "scenario_text": "...",
        "choices": [
            {{"id": 1, "text": "..."}},
            {{"id": 2, "text": "..."}},
            {{"id": 3, "text": "..."}}
        ],
        "citations": [{citations}]
    }}
    """
)
