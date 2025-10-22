# imports the HuggingFaceEmbeddings class
from langchain_huggingface import HuggingFaceEmbeddings

# retrieves the embeddings model
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

