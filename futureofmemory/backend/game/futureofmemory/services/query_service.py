from typing_extensions import TypedDict, List
from langgraph.graph import StateGraph, START
from langchain_core.documents import Document

from .embedding_service import get_embeddings
from .chroma_service import init_chroma, load_documents
from .llm_service import (
    get_llm,
    SYSTEM_RULES,
    scenario_writer_prompt,
    choice_maker_prompt,
    outcome_updater_prompt
)

vector_store = None
llm = None

def init_rag():
    global vector_store, llm
    if vector_store is None:
        embeddings = get_embeddings()
        vector_store = init_chroma(embeddings)
        llm = get_llm()
        splits = load_documents()
        if splits: 
            vector_store.add_documents(splits)
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
    role: str
    scenario: str
    choices: List[dict]
    choice_id: int
    year: int

def retrieve(state: State):
    vs, _ = init_rag()
    retrieved_docs = vs.similarity_search(state["question"])
    return {"context": retrieved_docs}

def generate(state: State):
    vs, llm = init_rag()
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    year = state.get("year", 2075)
    role = state["role"]

    if role == "scenario":
        sources = list({(doc.metadata or {}).get("source") for doc in state["context"] if doc.metadata})
        if not sources:
            sources = ["(no_source_found)"]
        citations_literal = ", ".join([f'"{s}"' for s in sources])
        prompt = scenario_writer_prompt.format(
            context=docs_content,
            year=year,
            system_rules=SYSTEM_RULES,
            citations=citations_literal
        )
    elif role == "choices":
        prompt = choice_maker_prompt.format(
            context=docs_content,
            year=year,
            system_rules=SYSTEM_RULES,
            scenario=state.get("scenario", "")
        )
    elif role == "outcome":
        prompt = outcome_updater_prompt.format(
            context=docs_content,
            system_rules=SYSTEM_RULES,
            scenario=state.get("scenario", ""),
            choices=state.get("choices", ""),
            choice_id=state.get("choice_id", None)
        )
    else:
        raise ValueError(f"Unknown role: {role}")

    response = llm.invoke(prompt)
    return {"answer": response.content, role: response.content}

graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

def run_rag(question: str, role: str, year: int = 2075, scenario=None, choices=None, choice_id=None):
    state = {
        "question": question,
        "role": role,
        "year": year,
        "scenario": scenario,
        "choices": choices,
        "choice_id": choice_id
    }
    return graph.invoke(state)
