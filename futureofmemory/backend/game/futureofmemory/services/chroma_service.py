"""
chroma_service.py
-----------------
Handles initialization of the Chroma vector store and ingestion of documents
for the RAG pipeline.
"""
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path

def init_chroma(embeddings, persist_directory="./chroma_langchain_db"):
    """Initialize and return a Chroma vector store."""
    return Chroma(
        collection_name="neuro_collection",
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )

# Loads documents from the neurotech data directory
BASE_DIR = Path(__file__).resolve().parent  
DATA_DIR = BASE_DIR / "neurotech"

def load_documents(data_dir=DATA_DIR):
    """Load PDF files, add metadata, and split them into chunks."""
    docs = []

    for path in Path(data_dir).rglob("*"):
        suf = path.suffix.lower()
        if suf == ".pdf":
            loaded = PyPDFLoader(str(path)).load()
        else:
            continue
        for d in loaded:
            d.metadata = d.metadata or {}
            d.metadata["source"] = path.name
        docs.extend(loaded)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    return [c for c in splits if c.page_content.strip()]
