# 🎓 Agentic RAG SaaS

**Production-grade Retrieval-Augmented Generation** with agentic reasoning, hybrid search, adaptive fine-tuning, and full observability.

> **Stack** : Qwen3-235B (NVIDIA API) · LangGraph · FastAPI · React · Qdrant · Redis · MongoDB · Celery · Prometheus · Grafana

---

## ⚡ Quick Start (Docker)

```bash
# 1. Configure
cp .env.example .env
# → Add your NVIDIA_API_KEY in .env

# 2. Build & Launch (9 services)
docker-compose up --build -d

# 3. Open
# 🌐 Frontend    → http://localhost:3001
# 🛠 Admin Panel → http://localhost:8502
# 📖 API Docs    → http://localhost:8000/docs
# 📊 Grafana     → http://localhost:3000  (admin/admin)
# 🔍 Qdrant UI   → http://localhost:6333/dashboard
# 📈 Prometheus  → http://localhost:9090
```

---

## 🏗 Architecture

```
                    ┌─────────────┐    ┌──────────────┐
                    │ React :3001 │    │ Streamlit    │
                    │ (Frontend)  │    │ Admin :8502  │
                    └──────┬──────┘    └──────┬───────┘
                           │    SSE Stream    │
                    ┌──────▼──────────────────▼───────┐
                    │     FastAPI Backend :8000        │
                    │  ┌─────────────────────────────┐│
                    │  │  LangGraph Pipeline          ││
                    │  │  analyze → retrieve →        ││
                    │  │  [data] → generate → critic  ││
                    │  └─────────────────────────────┘│
                    └──┬────┬────┬────┬───────────────┘
                       │    │    │    │
              ┌────────┘    │    │    └────────┐
              ▼             ▼    ▼             ▼
        ┌──────────┐  ┌────────┐ ┌─────────┐ ┌──────────┐
        │ Qdrant   │  │ Redis  │ │ MongoDB │ │ Celery   │
        │ :6333    │  │ :6379  │ │ :27017  │ │ Worker   │
        │ Vectors  │  │ Cache  │ │ Persist │ │ Async    │
        └──────────┘  └────────┘ └─────────┘ └──────────┘
                                       │
                    ┌──────────────────┘
                    ▼
        ┌────────────────────────────────┐
        │  Prometheus → Grafana          │
        │  :9090        :3000            │
        └────────────────────────────────┘
```

---

## 📂 Project Structure

```
agentic_rag_saas/
├── backend/
│   ├── main.py                      # FastAPI + all routes
│   ├── config.py                    # Pydantic Settings (.env)
│   ├── middleware.py                # CORS + Prometheus metrics + Logging
│   ├── graph.py                     # LangGraph pipeline (core RAG)
│   ├── cache.py                     # Redis cache + simulated SSE
│   ├── mongodb.py                   # MongoDB client (sync + async)
│   ├── celery_app.py                # Celery config (Redis broker)
│   ├── tasks.py                     # Async RAG tasks (retry + priority)
│   ├── ingestion_service/           # Upload, parse, chunk, embed → Qdrant
│   ├── retrieval_service/           # Hybrid BM25 + Dense + RRF fusion
│   ├── critic_service/              # Response quality evaluation
│   ├── data_agent_service/          # CSV/Excel analysis with Pandas
│   ├── feedback_service/            # 👍👎 collection → MongoDB
│   ├── analytics_service/           # Stats, satisfaction, top questions
│   └── finetuning_service/          # 3-level adaptive learning
│
├── frontend-react/                  # React + Vite (glassmorphism UI)
│   └── src/
│       ├── App.jsx                  # Main layout + admin toggle
│       ├── api.js                   # SSE streaming + REST API
│       ├── hooks/useChat.js         # Chat state + SSE handler
│       └── components/
│           ├── ChatMessage.jsx      # Messages + feedback buttons
│           ├── ChatInput.jsx        # Input + reasoning toggle
│           ├── KnowledgeSidebar.jsx # Source browser + upload
│           ├── PipelineViz.jsx      # Pipeline step visualization
│           ├── FeedbackButtons.jsx  # 👍👎 with MongoDB storage
│           ├── AdminDashboard.jsx   # Analytics + fine-tuning UI
│           └── WelcomeScreen.jsx    # Landing with suggestions
│
├── frontend/                        # Streamlit (legacy + admin)
├── monitoring/                      # Prometheus + Grafana configs
├── k8s/                             # Kubernetes manifests
├── docker-compose.yml               # 9-service orchestration
└── requirements.txt                 # Python dependencies
```

---

## 🔄 RAG Pipeline (LangGraph)

```
User Query
    ↓
[analyze]         Reformulation + intent detection
    ↓
[retrieve]        Hybrid: Dense (Qdrant) + BM25 → RRF fusion
    ↓
[data_analysis]   CSV/Parquet stats (conditional)
    ↓
[generate]        Qwen3-235B streaming (NVIDIA API)
    ↓
[critic]          Confidence score + quality check (when reasoning=true)
    ↓
Streaming Response + Sources + Feedback
```

---

## 🚀 Key Features

### 🧠 Agentic Reasoning
Toggle **Reasoning Mode** in the chat UI to activate the critic node. The LLM self-evaluates groundedness, relevance, and completeness.

### ⚡ Redis Cache
Identical queries are served from cache with **simulated word-by-word streaming** — the frontend experience is seamless. Default TTL: 1 hour.

### 👍👎 Feedback System
Every response has thumbs up/down buttons. Feedback is stored in MongoDB and feeds the adaptive fine-tuning engine.

### 🧬 Adaptive Fine-Tuning (3 Levels)
| Level | Trigger | Action |
|-------|---------|--------|
| L1 | ≥ 10 feedbacks | Adjust RRF search weights per document |
| L2 | ≥ 50 feedbacks | Analyze bad-response patterns by student level |
| L3 | ≥ 100 feedbacks | Recommend document re-indexation |

### 🔄 Celery Async Queue
Heavy queries can be offloaded to background workers via `/query/async`. Priority queue for `student_goal="examen"`.

### 📊 Full Observability
- **Prometheus** scrapes 4 metrics: `http_requests_total`, `rag_queries_total`, `documents_ingested_total`, `http_request_duration_seconds`
- **Grafana** dashboard pre-configured with latency, throughput, and ingestion panels

---

## 🌐 API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/query` | RAG pipeline (SSE streaming) |
| `POST` | `/query/async` | Submit async Celery task |
| `GET` | `/query/status/{id}` | Poll task result |
| `POST` | `/ingest/upload` | Upload + index document |
| `GET` | `/ingest/sources` | List indexed documents |
| `DELETE` | `/ingest/source` | Remove a document |
| `POST` | `/retrieve/search` | Direct hybrid search |
| `POST` | `/feedback` | Submit 👍👎 feedback |
| `GET` | `/analytics/stats` | Query stats |
| `GET` | `/analytics/satisfaction` | Satisfaction rate |
| `GET` | `/analytics/top-questions` | Most asked questions |
| `GET` | `/analytics/document-scores` | Per-document scores |
| `POST` | `/admin/finetune/trigger` | Run adaptive analysis |
| `GET` | `/admin/finetune/status` | Current fine-tune level |
| `GET` | `/admin/finetune/weights` | RRF weight map |
| `GET` | `/health` | Service health |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger UI |

---

## 📄 Supported Formats

| Format | Parser |
|--------|--------|
| `.pdf` | PyMuPDF |
| `.docx` | docx2txt |
| `.csv` | Pandas |
| `.parquet` | PyArrow |
| `.txt` | Unstructured |

---

## 🐳 Docker Services

| Service | Port | Role |
|---------|------|------|
| `backend` | 8000 | FastAPI + LangGraph |
| `frontend` | 3001 | React app (Nginx) |
| `admin` | 8502 | Streamlit admin |
| `qdrant` | 6333 | Vector database |
| `redis` | 6379 | Cache + Celery broker |
| `mongodb` | 27017 | Persistence |
| `celery_worker` | — | Background RAG tasks |
| `prometheus` | 9090 | Metrics collector |
| `grafana` | 3000 | Monitoring dashboards |

---

## 🖥️ Local Development (without Docker)

```bash
# Python environment
python -m venv venv
venv\Scripts\activate          # Linux: source venv/bin/activate
pip install -r requirements.txt

# Config
cp .env.example .env           # Fill NVIDIA_API_KEY

# Infrastructure (Docker still needed for these)
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 27017:27017 mongo:7

# Backend
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend-react && npm install && npm run dev

# Admin (separate terminal)
streamlit run frontend/admin_panel/admin.py --server.port 8502
```

---

## 📊 Monitoring

- **Prometheus** → http://localhost:9090 — Query `rag_queries_total`, `http_request_duration_seconds`
- **Grafana** → http://localhost:3000 — Login `admin`/`admin`, open pre-installed "Agentic RAG" dashboard
- **MongoDB** → Connect via Compass to `mongodb://localhost:27017` — collections: `interactions`, `feedbacks`
- **Redis** → `docker exec rag_redis redis-cli KEYS "*"` — see cached queries

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | — | NVIDIA API key (required) |
| `LLM_MODEL` | `qwen/qwen3-235b-a22b` | LLM model identifier |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model (local) |
| `QDRANT_HOST` | `qdrant` | Qdrant hostname |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `CACHE_TTL` | `3600` | Cache time-to-live (seconds) |
| `MONGODB_URL` | `mongodb://mongodb:27017/rag_saas` | MongoDB connection |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery broker |
| `CHUNK_SIZE` | `600` | Document chunk size (chars) |
| `CHUNK_OVERLAP` | `100` | Chunk overlap |
| `TOP_K` | `6` | Number of retrieved documents |

---

## ☸️ Kubernetes (minikube)

Ready to deploy the full 9-service stack to a local cluster.

> **Installation de minikube (Windows via Chocolatey)** :
> 1. Installez Chocolatey (PowerShell en admin) :
> ```powershell
> Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
> ```
> 2. Installez Minikube :
> ```powershell
> choco install minikube
> ```

```bash
# 1. Start minikube and use its Docker daemon
minikube start

# Connect your shell to minikube's Docker (Run the command for your OS):
eval $(minikube docker-env)                                     # Linux / Mac
minikube -p minikube docker-env --shell powershell | Invoke-Expression # Windows (PowerShell)

# 2. Build images directly in minikube
docker build -t rag-backend:latest -f Dockerfile.backend .
docker build -t rag-frontend:latest -f Dockerfile.frontend .
docker build -t rag-admin:latest -f Dockerfile.admin .

# 3. Create namespace
kubectl apply -f k8s/namespace.yml

# 4. Apply all manifests
kubectl apply -f k8s/config.yml
kubectl apply -f k8s/storage.yml
kubectl apply -f k8s/infra.yml
kubectl apply -f k8s/apps.yml
kubectl apply -f k8s/monitoring.yml

# 5. Connect
minikube service frontend-service -n rag-saas  # Open Frontend
minikube service admin-service -n rag-saas     # Open Admin
```

---

## 📜 License

MIT
