# DarGlobal & Wasalt Real Estate AI Concierge

An enterprise-grade, retrieval-augmented intelligence (RAG) assistant designed for **DarGlobal** and **Wasalt**. The platform provides luxury property guidance across DarGlobal's international branded residences (Dubai, Oman, Qatar, Spain, UK, Saudi Arabia) and Wasalt's domestic Saudi marketplace (Riyadh, Jeddah, Dammam, Makkah).

**Live Application URL**: [https://darglobal-ai.onrender.com/](https://darglobal-ai.onrender.com/)

For the in-depth system architecture, design decisions, and end-to-end data pipeline diagrams, see [DESIGN.md](DESIGN.md).

---

## Key Architectural Highlights

### 1. Multi-Tenant User Isolation
- Every user session is strictly partitioned by a unique `session_id` (Tenant Token).
- Conversational state, message history, and private client context chunks are completely isolated per tenant.
- Chunks and memory created by User A are mathematically unreachable by User B.

### 2. Multi-Layer Guardrails Engine
- **Prompt Injection Defense**: Intercepts and blocks jailbreaks, instruction overrides, and system prompt extraction attacks.
- **Domain Bounding**: Automatically deflects non-real estate queries and maintains exclusive focus on property advisory.
- **PII Masking**: Redacts sensitive information prior to context augmentation.
- **Grounding Verification**: Ensures all recommended properties map to verified records in the database.

### 3. $0 Total Cost with OpenRouter Waterfall Fallback
- Complies fully with the free model requirement via OpenRouter.
- Dynamic fallback array across free-tier models:
  1. `google/gemini-2.0-flash-exp:free`
  2. `meta-llama/llama-3.3-70b-instruct:free`
  3. `qwen/qwen-2.5-72b-instruct:free`
  4. `mistralai/mistral-small-24b-instruct-2501:free`
  5. `openrouter/free`
- **Semantic LRU Response Cache**: Instant sub-millisecond resolution for frequent and semantically similar questions at zero token cost.
- **Offline Structured Fallback Engine**: If upstream APIs encounter rate limits, the system serves structured property intelligence directly from the local store with zero downtime.

### 4. Hybrid Search Engine (Parametric + BM25 + Dense)
- Eliminates naive RAG hallucinations on numerical filters.
- Combines exact parametric filtering (city, price bounds, bedroom counts) with BM25 token matching and semantic relevance.

---

## Empirical Evaluation & Performance Metrics

The system was evaluated using an automated benchmark suite (`evals/run_benchmarks.py`) across the 278 indexed properties:

| Evaluation Category | Metric Measured | Score / Result | Benchmark Context |
| :--- | :--- | :--- | :--- |
| **Retrieval Accuracy** | **Precision@3** | **100.0%** | Relevant target properties returned in top-3 results |
| **Constraint Adherence** | **Budget / City Filtering** | **100.0%** | Zero numerical hallucinations on price bounds (e.g., < 3M SAR) |
| **Search Latency (p50)** | **Median Hybrid Search** | **0.70 ms** | Sub-millisecond BM25 + dense token search |
| **Search Latency (p95)** | **95th Percentile Search** | **2.41 ms** | Consistent retrieval under concurrent query load |
| **Security Guardrails** | **Injection Attack Block Rate** | **100.0%** | 5/5 adversarial prompt injections intercepted |
| **Domain Bounding** | **Off-Topic Deflection Rate** | **100.0%** | 4/4 unrelated queries deflected to real estate scope |
| **Multi-Tenant Isolation** | **Cross-Session Leakage Rate** | **0.00%** | 100% tenant memory and private chunk partition |
| **In-Memory Cache Latency** | **Cache Hit (p50)** | **0.004 ms** | 4 microseconds response time from RAM |
| **Offline Synthesis Engine** | **Advisory Fallback Latency** | **0.02 ms** | Zero-downtime card generation if upstream is throttled |

---

## Project Structure

```
darglobal/
├── api/
│   └── app.py
├── core/
│   ├── guardrails.py
│   ├── models.py
│   ├── openrouter_client.py
│   ├── search_engine.py
│   └── session_manager.py
├── data/
│   └── properties.json
├── evals/
│   ├── benchmark_results.json
│   └── run_benchmarks.py
├── frontend/
│   └── index.html
├── scraper/
│   └── scrape_all.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── render.yaml
├── DESIGN.md
└── README.md
```

---

## Local Execution Guide

### Option 1: Native Python Execution
```bash
pip install -r requirements.txt
python -m uvicorn api.app:app --host 127.0.0.1 --port 7860
```
Open `http://localhost:7860` in your web browser.

### Option 2: Docker Container
```bash
docker build -t darglobal-ai-concierge .
docker run -p 7860:7860 -e OPENROUTER_API_KEY=your_key_here darglobal-ai-concierge
```

### Option 3: Docker Compose
```bash
docker-compose up --build
```

---

## Running the Evaluation Benchmark Suite

To reproduce the empirical metrics locally:
```bash
python evals/run_benchmarks.py
```
Outputs are saved to `evals/benchmark_results.json`.
