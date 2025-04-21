# 🔍 Optimal Chunk Size and Embedding Dimension for RAG Systems

## 📈 Chunk Size Recommendations

**Ideal Chunk Size:**

| Document Type | Recommended Chunk Size |
|:--------------|:------------------------|
| Plain Text / Articles | 350–450 tokens |
| Dense Academic Papers | 450–600 tokens |
| FAQs / Short Answers | 250–300 tokens |

**Best Practices:**
- Target **400 tokens** per chunk for a balanced semantic coverage.
- Maintain an **overlap** of **15–20%** (~50–80 tokens) to preserve context between adjacent chunks.
- Prefer **semantic splitting** (e.g., by sentence or paragraph) over raw token slicing.

**Example Settings:**
```json
{
  "chunk_size_tokens": 400,
  "chunk_overlap_tokens": 80
}
```

---

## 🔄 Embedding Dimension Recommendations

**Based on Embedding Model:**

| Embedding Model | Dimension | Notes |
|:----------------|:----------|:------|
| OpenAI Ada-002 | 1536 | Default, high-quality embeddings |
| OpenAI text-embedding-3-small | 1536 | Fast, efficient, new generation |
| OpenAI text-embedding-3-large | 3072 | Highest quality, higher cost |
| E5-Large / Instructor-XL (Open Source) | 768 | Great for private hosting |
| MiniLM / MPNet | 384 | Lightweight, fast, smaller memory footprint |

**Professional Guidance:**
- Use **1536 dimensions** for most RAG deployments with OpenAI models.
- Choose **768 dimensions** for open-source embeddings (e.g., HuggingFace models).
- Use **384 dimensions** only for resource-constrained environments.

---

## 💡 Optimized Settings for Production

```json
{
  "chunk_size_tokens": 400,
  "chunk_overlap_tokens": 80,
  "embedding_dimension": 1536
}
```

- Balanced between **retrieval accuracy** and **performance**.
- Ideal for most real-world applications including technical docs, knowledge bases, and customer support systems.

---

## 🌟 Pro-Tuned Settings for Long Documents

```json
{
  "chunk_size_tokens": 512,
  "chunk_overlap_tokens": 100,
  "embedding_dimension": 3072
}
```

- Useful for **legal**, **medical**, and **scientific** documents with complex structures.
- Requires higher memory and compute resources.

---

# 📚 Summary Table

| Parameter | Recommended Value | Reason |
|:----------|:------------------|:------|
| Chunk Size | 400 tokens | Preserves semantic meaning, fast retrieval |
| Overlap Size | 80 tokens | Maintains context continuity |
| Embedding Dimension | 1536 | Balances cost and quality |

---

###            default_chunk_size: int = 1400,  # ✅ ~400 tokens
###            default_chunk_overlap: int = 250,  # ✅ ~20% of chunk size
###            default_separator: str = "\n"  # ✅ Still fine as fallback



> ✨ These settings ensure your RAG system performs with **high semantic retrieval quality**, **low latency**, and **optimized memory usage**.
 
# 📦 Models Management - RAG System

Welcome to the `models/` directory! This folder stores **locally downloaded models** for **offline RAG operations**.

We manage two major categories of models:
- **Embedding models** (for vectorization)
- **LLM models** (for generating answers)

---

## 📂 Folder Structure

```bash
models/
├── embedding/          # Embedding models
│   ├── instructor-xl/  # Downloaded Instructor model
│   └── all-MiniLM/     # Other sentence-transformer model
│
├── llm/                # LLM models (Chat models)
│   ├── mistral-7b/     # Mistral-7B (GGUF or bin)
│   └── llama-2-7b/     # Llama-2 (HF or Ollama)
```

---

## 🛠 Downloading Models

### ➡️ Download HuggingFace Models
Use:
```bash
python scripts/setup_llm_model.py --source hf --model-name TheBloke/Mistral-7B-Instruct-v0.1-GGUF --file-types gguf --backend ollama --env-key LOCAL_LLM_MODEL_PATH
```

### ➡️ Pull Ollama Models
Use:
```bash
python scripts/setup_llm_model.py --source ollama --model-name mistral
```

### ➡️ Download Embedding Models
Use:
```bash
python scripts/setup_instructor_model.py --type instructor
```

---

## 🔑 Environment Variables (.env)

| Key | Meaning |
|:----|:--------|
| `INSTRUCTOR_MODEL_NAME` | Path to local embedding model |
| `SENTENCE_TRANSFORMER_MODEL_NAME` | Path to local sentence-transformer |
| `LOCAL_LLM_MODEL_PATH` | Path to local LLM model folder |
| `EMBEDDING_SERVICE` | Which embedding service to use |
| `LLM_BACKEND` | Ollama / Transformers |

Always **PATCH the correct path** automatically when downloading using our setup scripts.

---

## ⚡ Best Practices

- **One model = One folder** under correct category (`embedding/` or `llm/`)
- Always use **lowercase, hyphenated** folder names (e.g., `mistral-7b-instruct`)
- **Never mix** LLMs and embeddings into the same subfolder.
- Prefer `.gguf` format for Ollama-based models.
- After download, check size — avoid >16GB models unless you have enough RAM.
- Regularly **backup** the `models/` folder.

---

## 🛑 Common Mistakes

- ❌ Putting multiple different models inside the same folder.
- ❌ Forgetting to update `.env` when switching models.
- ❌ Using incompatible model format (e.g., trying `.bin` with Ollama instead of `.gguf`).

---

## 🚀 Future Improvements

- Add model version control.
- Automatically check quantization levels.
- Scan models for required minimum VRAM.

---

> ✨ With clean model management, your RAG system stays blazing fast, portable, and reliable!