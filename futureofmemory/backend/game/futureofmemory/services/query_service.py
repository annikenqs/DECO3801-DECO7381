from typing_extensions import TypedDict, List
from langgraph.graph import StateGraph, START
from langchain_core.documents import Document
import json
import re

from .embedding_service import get_embeddings
from .chroma_service import init_chroma, load_documents
from .llm_service import (
    get_llm,
    SYSTEM_RULES,
    first_scenario_and_choices_prompt,
    next_scenario_and_choices_prompt,
)

vector_store = None
llm = None

def init_rag():
    global vector_store, llm
    if vector_store is None:
        embeddings = get_embeddings()
        vector_store = init_chroma(embeddings)
        splits = load_documents()
        if splits: 
            vector_store.add_documents(splits)
    if llm is None:
        llm = get_llm()
    return vector_store, llm

def run_rag_query(query: str):
    vs, model = init_rag()
    retriever = vs.as_retriever()
    docs = retriever.invoke(query)
    return docs, model

# State
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str
    scenario: str
    choices: List[dict]
    chosen_choice: str
    year: int
    faction: str 

def retrieve(state: State):
    vs, _ = init_rag()

    year = state.get("year", 2075)
    faction = state.get("faction", "Unknown")
    prev_scenario = state.get("scenario", "")
    chosen_choice = state.get("chosen_choice", "")

    if prev_scenario and chosen_choice:
        query = (
            f"Neurotechnology ethics, memory manipulation, and societal impact in the future."
            f"Focus on themes from the last event: {chosen_choice} and previous scenario {prev_scenario}. "
            f"Consider information that could be relevant to faction {faction}."
        )
    else:
        query = (
            f"General context on neurotechnology, memory implants, memory manipulation, and ethics in the future"
            f"Consider information that could be relevant to faction {faction}."
        )

    retrieved_docs = vs.similarity_search(query, k=6) 
    return {"context": retrieved_docs}

def safe_parse_response(raw: str) -> dict:
    """Try to parse model output into JSON, with fallbacks."""
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", raw)  
    cleaned = re.sub(r"\n?```$", "", cleaned)     
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw": raw}

    # Fallbacks if keys are missing
    if "scenario_text" not in parsed and "scenario" in parsed:
        parsed["scenario_text"] = parsed["scenario"]
    if "scenario_text" not in parsed:
        parsed["scenario_text"] = parsed.get("raw", "")

    return parsed

def generate(state: State):
    vs, llm = init_rag()
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    year = state.get("year", 2075)
    faction = state.get("faction", "Unknown")

    sources = list({(doc.metadata or {}).get("source") for doc in state["context"] if doc.metadata})
    if not sources:
        sources = ["(no_source_found)"]
    citations_literal = ", ".join([f'"{s}"' for s in sources])
    
    chosen_choice_text = state.get("chosen_choice") or "None"
    
    if not state.get("scenario") or not state.get("chosen_choice"):
        scenario_prompt = first_scenario_and_choices_prompt.format(
            context=docs_content,
            year=year,
            system_rules=SYSTEM_RULES,
            citations=citations_literal,
            faction=faction
        )
    else:
        scenario_prompt = next_scenario_and_choices_prompt.format(
            context=docs_content,
            year=year,
            system_rules=SYSTEM_RULES,
            citations=citations_literal,
            faction=faction,
            previous_scenario=state.get("scenario", "None"),
            chosen_choice=chosen_choice_text
        )
    
    scenario_response = llm.invoke(scenario_prompt)
    scenario_raw = scenario_response.content.strip()
    scenario_parsed = safe_parse_response(scenario_raw)
    scenario_text = scenario_parsed.get("scenario_text", "No scenario generated")
    choices = scenario_parsed.get("choices", [])
    citations = scenario_parsed.get("citations", [])
    
    return {
        "scenario": {
            "year": year,
            "scenario_text": scenario_text,
            "citations": citations,
            "choices": choices
        }
    }

graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

def run_rag(year: int = 2075, scenario=None, choices=None, chosen_choice=None, faction="Unknown", **kwargs):
    state = {
        "year": year,
        "scenario": scenario,
        "choices": choices,
        "chosen_choice": chosen_choice, 
        "faction": faction
    }
    return graph.invoke(state)
