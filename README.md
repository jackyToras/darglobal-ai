# DarGlobal & Wasalt Real Estate AI Concierge

An enterprise-grade, retrieval-augmented intelligence (RAG) assistant designed for **DarGlobal** and **Wasalt**. The platform provides luxury property guidance across DarGlobal's international branded residences (Dubai, Oman, Qatar, Spain, UK, Saudi Arabia) and Wasalt's domestic Saudi marketplace (Riyadh, Jeddah, Dammam, Makkah).

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
- **Smart Response Cache**: Instant 30ms resolution for frequent questions at zero token cost.
- **Offline Structured Fallback Engine**: If upstream APIs encounter rate limits, the system serves structured property intelligence directly from the local store with zero downtime.

### 4. Hybrid Search Engine (Parametric + BM25 + Dense)
- Eliminates naive RAG hallucinations on numerical filters.
- Combines exact parametric filtering (city, price bounds, bedroom counts) with BM25 token matching and semantic relevance.

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
├── frontend/
│   └── index.html
├── scraper/
│   └── scrape_all.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
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

## Cloud Deployment (100% Free Live URL)

### Deploying to Hugging Face Spaces (Recommended Free Docker Host)
1. Create a free account at [huggingface.co](https://huggingface.co).
2. Click **New Space** -> Choose **Docker** as SDK -> Select **Blank**.
3. Push this repository to your Space:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/darglobal-ai
   git push space main
   ```
4. In Space Settings -> **Variables and secrets**, add `OPENROUTER_API_KEY` (optional, offline fallback active by default).
5. Your public URL is immediately live at: `https://huggingface.co/spaces/YOUR_USERNAME/darglobal-ai`.
