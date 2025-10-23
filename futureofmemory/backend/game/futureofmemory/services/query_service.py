from typing_extensions import TypedDict, List
from langgraph.graph import StateGraph, START
from langchain_core.documents import Document
from threading import Lock

# import requisite services for querying
from .embedding_service import get_embeddings
from .chroma_service import init_chroma, load_documents
from .llm_service import (
    generate_json,
    SYSTEM_RULES,
    first_scenario_and_choices_prompt,
    next_scenario_and_choices_prompt,
)

vector_store = None
_vector_lock = Lock()

# initialise the RAG
def init_rag():
    global vector_store
    if vector_store is None:
        embeddings = get_embeddings()
        vector_store = init_chroma(embeddings)
        splits = load_documents()
        if splits:
            vector_store.add_documents(splits)
    return vector_store


def run_rag_query(query: str):
    vs = init_rag()
    retriever = vs.as_retriever()
    docs = retriever.invoke(query)
    return docs

def _clip(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars].rsplit("\n", 1)[0] or s[:max_chars]

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

# retrieves relevant documents
def retrieve(state: State):
    vs = init_rag()

    faction = state.get("faction", "Unknown")
    prev_scenario = state.get("scenario", "")
    chosen_choice = state.get("chosen_choice", "")

    if prev_scenario and chosen_choice:
        query = (
            "Neurotechnology ethics, memory manipulation, and societal impact in the future. "
            f"Focus on themes from the last event: {chosen_choice} and previous scenario {prev_scenario}. "
            f"Consider information that could be relevant to faction {faction}."
        )
    else:
        query = (
            "General context on neurotechnology, memory implants, memory manipulation, and ethics in the future. "
            f"Consider information that could be relevant to faction {faction}."
        )

    # smaller fanout
    raw = vs.similarity_search(query, k=3)

    # de-dupe by (source, page)
    seen = set()
    deduped = []
    for d in raw:
        meta = d.metadata or {}
        key = (meta.get("source"), meta.get("page"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(d)

    return {"context": deduped[:2]}

# generates the next scenario
def generate(state: State):
    vs = init_rag()
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])

    # Keep context compact (smaller than before)
    docs_content = _clip(docs_content, 1600)  # ~400 tokens max


    year = state.get("year", 2075)
    faction = state.get("faction", "Unknown")
    sources = list({(doc.metadata or {}).get("source") for doc in state["context"] if doc.metadata}) or ["(no_source_found)"]
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

# runs RAG
def run_rag(year: int = 2075, scenario=None, choices=None, chosen_choice=None, faction="Unknown", **kwargs):
    state = {
        "year": year,
        "scenario": scenario,
        "choices": choices,
        "chosen_choice": chosen_choice, 
        "faction": faction
    }
    return graph.invoke(state)
