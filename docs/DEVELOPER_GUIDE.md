# Sovereignty AI Studio - Developer Guide

**Enterprise-Grade, Production-Ready RAG Framework**

Sovereignty AI Studio provides a unified interface for integrating widely used Retrieval Augmented Generation (RAG) systems such as ChromaDB, Pinecone, Weaviate, Qdrant, SingleStore, Faiss, Redis, and more. This guide details installation, usage, configuration, and advanced features for developers.

---

## 1. Installation

### Requirements

- Python 3.10+
- `.env` file with API keys (see `.env.example`)

### Install via pip

```bash
pip install sovereignty-ai
```

---

## 2. Configuration & Environment Variables

Sovereignty AI Studio uses environment variables to manage API keys, endpoints, and configuration options. Create a `.env` file at the root of your project.

| Variable | Required | Description |
|---|---|---|
| `PINECONE_API_KEY` | Yes | API key for Pinecone vector database |
| `PINECONE_ENV` | Optional | Pinecone environment name (e.g., `us-east1-gcp`) |
| `QDRANT_API_KEY` | Optional | API key for Qdrant Cloud deployments |
| `QDRANT_URL` | Optional | Qdrant Cloud or local server URL |
| `SINGLESTORE_HOST` | Optional | SingleStore database host |
| `SINGLESTORE_PORT` | Optional | Database port (default: 3306) |
| `SINGLESTORE_USER` | Optional | Database username |
| `SINGLESTORE_PASSWORD` | Optional | Database password |
| `SINGLESTORE_DATABASE` | Optional | Database name |
| `REDIS_URL` | Optional | Connection string for Redis (when supported) |

### Example `.env` file

```env
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENV=us-east1-gcp
QDRANT_API_KEY=your-qdrant-key
QDRANT_URL=https://your-cluster.qdrant.tech
SINGLESTORE_HOST=localhost
SINGLESTORE_USER=admin
SINGLESTORE_PASSWORD=password123
SINGLESTORE_DATABASE=rag_db
```

> **Note:** Only define the variables for the RAG systems you intend to use.

---

## 3. Quickstart Usage

Below are examples for setting up and running different RAG wrappers.

### 3.1 Pinecone Example

```python
from swarms_memory import PineconeMemory

pinecone_db = PineconeMemory(
    api_key="your-api-key",
    environment="your-environment",
    index_name="your-index-name"
)

pinecone_db.add("This is a document about AI.", {"category": "AI"})
results = pinecone_db.query("What is AI?", filter={"category": "AI"})
print(results)
```

### 3.2 ChromaDB Example

```python
from swarms_memory import ChromaDB

chromadb = ChromaDB(metric="cosine")
chromadb.add("Test document.")
result = chromadb.query("Test query.")
print(result)
```

### 3.3 FAISS Example

```python
from swarms_memory.faiss_wrapper import FAISSDB

faiss_db = FAISSDB(dimension=768, index_type="Flat")
faiss_db.add("Example AI document")
results = faiss_db.query("What is AI?")
print(results)
```

### 3.4 Qdrant Example

```python
from qdrant_client import QdrantClient
from swarms_memory.vector_dbs import QdrantDB

client = QdrantClient(":memory:")  # In-memory testing
qdrant_db = QdrantDB(client=client, collection_name="demo_collection", n_results=3)

qdrant_db.add("Qdrant is a vector database.")
results = qdrant_db.query("What is vector search?")
print(results)
```

---

## 4. Advanced Features

### 4.1 Custom Embedding Functions

```python
from transformers import AutoTokenizer, AutoModel
import torch

def custom_embedding_function(text: str):
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModel.from_pretrained("bert-base-uncased")
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
```

### 4.2 Preprocessing & Postprocessing Hooks

```python
def preprocess(text: str) -> str:
    return text.lower().strip()

def postprocess(results):
    for res in results:
        res["custom_score"] = res["score"] * 2
    return results
```

### 4.3 Deployment Modes

- **In-Memory:** For prototyping and testing
- **Local Server:** Self-hosted production
- **Cloud:** Pinecone, Qdrant Cloud, SingleStore for large-scale RAG

### 4.4 Logging & Monitoring

```python
logger_config = {
    "handlers": [
        {"sink": "rag_wrapper.log", "rotation": "1 GB"},
        {"sink": lambda msg: print(f"Log: {msg}")}
    ]
}
```

---

## 5. Supported RAG Systems

| System | Status | Description | Website |
|---|---|---|---|
| ChromaDB | Available | Distributed database for large-scale AI tasks | [ChromaDB](https://chromadb.com/) |
| Pinecone | Available | Fully managed vector database | [Pinecone](https://pinecone.io/) |
| Redis | Coming Soon | In-memory DB for caching and message brokering | [Redis](https://redis.io/) |
| Faiss | Available | Efficient similarity search library | [Faiss](https://faiss.ai/) |
| SingleStore | Available | Distributed SQL DB with vector search | [SingleStore](https://www.singlestore.com/) |
| Qdrant | Available | Rust-based scalable vector database | [Qdrant](https://qdrant.tech/) |
| HNSW | Coming Soon | Graph-based nearest neighbor search | [HNSW](https://github.com/nmslib/hnswlib) |

---

## 6. License

MIT License

---

## 7. Citation

```bibtex
@misc{swarms,
  author = {Gomez, Kye},
  title = {Sovereignty AI Studio: Enterprise-Grade RAG Framework},
  howpublished = {\url{https://github.com/kyegomez/swarms}},
  year = {2026},
  note = {Accessed: Date}
}
```
