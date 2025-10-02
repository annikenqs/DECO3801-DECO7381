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
    scenario_writer_prompt,
    choice_maker_prompt,
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
    choice_id: int
    year: int
    faction: str 

def retrieve(state: State):
    vs, _ = init_rag()
    retrieved_docs = vs.similarity_search(state["question"])
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
    
    if not state.get("scenario") or not state.get("choice_id"):
        previous_context = ""
    else:
        previous_context = f"""
        Previous scenario: {state['scenario']}
        Player chose: {state['choice_id']}
        """

    sources = list({(doc.metadata or {}).get("source") for doc in state["context"] if doc.metadata})
    if not sources:
        sources = ["(no_source_found)"]
    citations_literal = ", ".join([f'"{s}"' for s in sources])
    
    scenario_prompt = scenario_writer_prompt.format(
        context=docs_content,
        year=year,
        system_rules=SYSTEM_RULES,
        citations=citations_literal,
        previous_context=previous_context,
        faction=faction
    )
    
    scenario_response = llm.invoke(scenario_prompt)
    scenario_raw = scenario_response.content.strip()
    scenario_parsed = safe_parse_response(scenario_raw)
    scenario_text = scenario_parsed.get("scenario_text", "No scenario generated")
    citations = scenario_parsed.get("citations", [])

    choice_prompt = choice_maker_prompt.format(
        context=docs_content,
        system_rules=SYSTEM_RULES,
        scenario=scenario_text
    )
    
    choice_response = llm.invoke(choice_prompt)
    choice_raw = choice_response.content.strip()
    choice_parsed = safe_parse_response(choice_raw)
    choices = choice_parsed.get("choices", [])
    
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

def run_rag(question: str, year: int = 2075, scenario=None, choices=None, choice_id=None, faction="Unknown"):
    state = {
        "question": question,
        "year": year,
        "scenario": scenario,
        "choices": choices,
        "choice_id": choice_id,
        "faction": faction
    }
    return graph.invoke(state)
