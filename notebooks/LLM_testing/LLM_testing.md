# LLM testing
This notebook lets you test several LLMs through Hugging Face. 

## How to use it

### 1. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate     # macOS/Linux
.\.venv\Scripts\Activate      # Windows PowerShell
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Authenticate with Hugging Face
Get a token from [Hugging Face → Settings → Access Tokens](https://huggingface.co/settings/tokens) (role: **Read**).
If you don't have a Hugging Face account, create one here: https://huggingface.co

```bash
hf auth login
```

### 4. Choose your LLMs
Under Base endpoints, you can choose which Hugging Face models you would like to test. 
```bash
# Base endpoints
_llama = HuggingFaceEndpoint(repo_id="meta-llama/Llama-3.1-8B-Instruct", **common_llm)
_qwen  = HuggingFaceEndpoint(repo_id="Qwen/Qwen2.5-7B-Instruct", **common_llm)
_gemma = HuggingFaceEndpoint(repo_id="google/gemma-2-9b-it", **common_llm) 


model_A = ChatHuggingFace(llm=_llama)
model_B = ChatHuggingFace(llm=_qwen)
model_C = ChatHuggingFace(llm=_gemma) 

models = {
    "llama8b": model_A,
    "qwen7b": model_B,
    "gemma9b": model_C,

```