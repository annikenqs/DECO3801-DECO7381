"""
embedding_service.py
--------------------
Provides embedding initialization for the RAG pipeline.
"""
from langchain_huggingface import HuggingFaceEmbeddings

def get_embeddings():
    """Initialize and return HuggingFace embedding model."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

