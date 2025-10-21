import os, json, re
from langchain.prompts import PromptTemplate
from .sagemaker_service import start_async_job, poll_async_output

USE_SAGEMAKER = os.getenv("USE_SAGEMAKER", "true").lower() == "true"

if USE_SAGEMAKER:
    from .sagemaker_service import invoke_async_tgi

DEFAULT_TIMEOUT_S = int(os.getenv("SM_TIMEOUT_SECONDS", "300"))  # 300 is plenty for warm endpoint

def start_generation(prompt: str, max_new_tokens=200, temperature=0.7) -> str:
    extra = {"return_full_text": False}
    return start_async_job(
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        extra_params=extra,
    )

def collect_generation(output_location: str, timeout_s: int | None = None):
    raw = poll_async_output(
        output_location,
        timeout_s=timeout_s or DEFAULT_TIMEOUT_S,
        endpoint_name=os.getenv("SM_ENDPOINT_NAME", "neuro-rag-async"),
    )
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {"raw_text": raw}


def get_llm():
    """Return a Gemini client only when not using SageMaker."""
    if USE_SAGEMAKER:
        raise RuntimeError("get_llm() is only for the Gemini backend")
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)

def _approx_tokens(s: str) -> int:
    return max(1, len(s) // 4)

def _clip_chars(s: str, limit_chars: int) -> str:
    if len(s) <= limit_chars:
        return s
    return (s[:limit_chars].rsplit("\n", 1)[0]) or s[:limit_chars]

def _extract_json(text: str):
    """
    Try hard to find a JSON object in free-form text (with/without code fences),
    prefer one that contains 'scenario_text'.
    """
    if not isinstance(text, str):
        return None

    # remove fences
    t = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    t = re.sub(r"\n?```$", "", t).strip()

    # 1) Fast path: the whole thing is JSON
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2) Scan for {...} substrings
    stack = []
    starts = []
    for i, ch in enumerate(t):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            start = stack.pop()
            candidate = t[start:i+1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    # prefer ones that look like our schema
                    if "scenario_text" in obj:
                        return obj
                    # keep the first valid dict as fallback
                    if not starts:
                        starts.append(obj)
            except Exception:
                pass
    if starts:
        return starts[0]
    return None

MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "1536"))

def generate_json(prompt: str, max_new_tokens=200, temperature=0.7):
    # Leave a larger headroom (e.g., 300 tokens) for safety
    headroom = 300
    if _approx_tokens(prompt) >= MAX_INPUT_TOKENS - headroom:
        keep_chars = max(600, (MAX_INPUT_TOKENS - headroom) * 4)
        prompt = _clip_chars(prompt, keep_chars)

    extra = {
        # these won’t break TGI; harmless hints
        "return_full_text": False
    }

    raw = invoke_async_tgi(
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        extra_params=extra,
    )
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {"raw_text": raw}



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
    1. Write the first ~40 word scenario for the year {year}.
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

next_scenario_and_choices_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer and choice maker.
    
    1. Write a ~40 word scenario for the year {year}. Start with: "In {year}, ...".
    2. Then, propose 3 realistic player choices that follow naturally from it.

    Strict rules:
    This must directly continue from the previous scenario and the player's chosen response.
    Do not restart. Do not ignore.

    Previous scenario:
    "{previous_scenario}"

    Player's chosen response:
    "{chosen_choice}"

    Escalate the story:
    - Show unexpected consequences of the choice (e.g. backlash, unintended effects, new actors entering the scene).
    - Add variety: not just scandals and protests, but also breakthroughs, accidents, personal tragedies, underground movements, black markets etc.
    - Make it emotional and vivid, like a human drama
    - Keep it ~40 words

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