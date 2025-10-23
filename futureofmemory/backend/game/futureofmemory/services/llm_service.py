"""
llm_service.py
----------------
Manages SageMaker model calls and JSON parsing for scenario generation.
Includes helpers for token limits, text cleanup, and structured output.
"""
import os
import re
import json
from typing import Any, Dict

import boto3
from langchain.prompts import PromptTemplate

# --- Configuration ---

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
ENDPOINT_NAME = os.getenv("SM_ENDPOINT_NAME", "neuro-rag-rt")
MAX_TOTAL_TOKENS = int(os.getenv("MAX_TOTAL_TOKENS", "2048"))

_boto = boto3.Session(region_name=AWS_REGION)
_rt = _boto.client("sagemaker-runtime")


# --- Utility functions ---

def _approx_tokens(s: str) -> int:
    """Rough heuristic: ~4 characters per token."""
    return max(1, len(s) // 4)


def _clip_chars(s: str, limit_chars: int) -> str:
    """Clip long strings to a character limit, cutting at newline if possible."""
    if len(s) <= limit_chars:
        return s
    return (s[:limit_chars].rsplit("\n", 1)[0]) or s[:limit_chars]

# --- JSON extraction and normalization functions ---

def _extract_json_obj(text: str) -> Dict[str, Any] | None:
    """
    Extract a valid JSON object from text output.
    - First tries to find the first balanced {...} JSON object (handles quotes and escapes).
    - If multiple valid objects exist, prefers the last one containing 'scenario_text' or 'choices'.
    - Falls back to parsing the whole text if direct extraction fails.
    """
    if not isinstance(text, str):
        return None

    # Remove markdown fences
    t = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    t = re.sub(r"\n?```$", "", t).strip()

    candidates = []
    depth = 0
    start = None
    in_str = False
    escape = False

    for i, ch in enumerate(t):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}' and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                frag = t[start:i+1]
                try:
                    obj = json.loads(frag)
                    if isinstance(obj, dict):
                        candidates.append(obj)
                except Exception:
                    pass

    # Prefer last valid JSON with expected keys 
    for obj in reversed(candidates):
        if "scenario_text" in obj or "choices" in obj:
            return obj

    if candidates:
        return candidates[-1]

    # Fallback: maybe the entire string is JSON 
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None

    return None

def safe_parse_response(raw_output):
    """
    Safely parse model output into JSON.
    Handles both dicts and string outputs.
    """

    # if already parsed JSON, just return
    if isinstance(raw_output, dict):
        return raw_output

    if raw_output is None:
        return {}

    text = str(raw_output).strip()

    # remove code fences or markdown formatting
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # try to extract last JSON object if multiple exist
    if text.count("{") > 1 and text.count("}") > 1:
        try:
            start = text.rfind("{")
            text = text[start:]
        except Exception:
            pass

    try:
        return json.loads(text)
    except Exception:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except Exception:
            return {"error": "Failed to parse model output", "raw": text}


# --- Model invocation ---

def invoke_sync_tgi(prompt: str, *, max_new_tokens: int = 300, temperature: float = 0.7) -> str:
    """Invoke a SageMaker text-generation endpoint synchronously."""

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



def generate_json(prompt: str, *, max_new_tokens: int = 600, temperature: float = 0.7) -> Dict[str, Any]:
    """
    Generate and parse a JSON object from model output.
    Clips overly long prompts and ensures safe token limits.
    """
    
    prompt = _clip_chars(prompt, 4000)
    tokens_in = _approx_tokens(prompt)
    max_allowed = MAX_TOTAL_TOKENS - tokens_in - 50
    safe_new_tokens = min(max_new_tokens, max(50, max_allowed))

    raw = invoke_sync_tgi(prompt, max_new_tokens=safe_new_tokens, temperature=temperature)

    print("==== RAW MODEL OUTPUT START ====")
    print(raw)
    print("==== RAW MODEL OUTPUT END ====")

    if isinstance(raw, dict):
        return raw
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    obj = _extract_json_obj(raw)
    if isinstance(obj, dict):
        return obj

    return {"raw_text": raw}


# --- Prompt templates and scenario rules ---

# Defines system rules that the LLM must adhere to
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

# Defines the base prompt template for scenario generation
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

# Defines the prompt template for generating the next scenario and choices
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
