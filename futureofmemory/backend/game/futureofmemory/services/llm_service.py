import os
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in your .env or shell.")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=api_key,
    )

SYSTEM_RULES = {
    "rules": [
        "Neurotechnology implants have become popular by 2075.",
        "Memory manipulation is technically possible but ethically controversial.",
        "Each year, one major neurotech-related event happens.",
        "Players always receive exactly 3 choices."
    ],
    "constraints": [
        "Scenarios must stay realistic for neurotechnology research.",
    ]
}

BASE_PROMPT = """
Follow these fixed system rules (do not change them):
{system_rules}

Context:
{context}
"""

scenario_writer_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer.
    Write a ~80 word scenario describing a neurotechnology-related event in the year {year}.
    Output JSON:
    {{
        "year": {year},
        "scenario_text": "...",
        "citations": [{citations}]
    }}
    """
)

choice_maker_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Choice Maker.
    Scenario:
    {scenario}
    Output JSON:
    {{
        "choices": [
            {{"id": 1, "text": "..."}},
            {{"id": 2, "text": "..."}},
            {{"id": 3, "text": "..."}}
        ]
    }}
    """
)

