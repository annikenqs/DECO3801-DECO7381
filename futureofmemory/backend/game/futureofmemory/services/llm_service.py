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

Context:
{context}
"""

first_scenario_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer.
    Write the first ~40 word scenario for the year: {year}.
    
    The chosen faction: {faction} should shape the perspective and concerns in the story.
    Since this is the opening, introduce the world vividly:
    - Show a dramatic neurotech incident (scandal, invention, protest, accident etc).
    - Make it personal and emotional, not abstract or academic.
    
    Output JSON:
    {{
        "scenario_text": "...",
        "citations": [{citations}]
    }}
    """
)

next_scenario_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Scenario Writer.
    Write a ~40 word scenario for the year {year}. Start with: "In {year}, ...".

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

    Output JSON ONLY:
    {{
        "scenario_text": "...",
        "citations": [{citations}]
    }}
    """
)


choice_maker_prompt = PromptTemplate.from_template(
    BASE_PROMPT + """
    You are the Choice Maker. Given the following scenario: {scenario}, write exactly 3 distinct choices a player can make in response to the scenario.
    The choices should be realistic and reflect different perspectives, as well as the chosen faction: {faction}. They should be concise (max 20 words each).
    
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

