# 🧠 Solartis AI SQL Performance Analyzer
### Multi-Agent RAG System for Database Reliability Engineering

**Submitted by:** Abinaya T  
**College:** Madras Institute of Technology, Anna University  
**CGPA:** 8.99 | B.Tech Information Technology (2022–2026)  
**GitHub:** [solartis-hackathon-abinaya-t-92](https://github.com/Abinaya-092/solartis-hackathon-abinaya-t-92)

---

## 🎯 Problem Understanding

Insurance platforms like Solartis process millions of policy transactions daily. A single slow SQL query isn't just a performance issue — it's a financial leak. 

**The core challenge:**
- Junior developers and support engineers lack the expertise to diagnose database performance issues that senior DBAs resolve intuitively
- Mean Time To Resolution (MTTR) for slow queries is 30–60 minutes of manual analysis
- As data grows, undetected query patterns silently degrade into production incidents

**This system solves it by acting as an "Expert-in-a-Box"** — a multi-agent AI system that diagnoses, fixes, and explains database performance issues in seconds, for any audience.

---

## 🏗️ Architecture
## 🏗️ Architecture

```mermaid
flowchart TD
    A["🧑‍💻 User Query\nNatural Language"] --> B["🛡️ Domain Validator\nRejects non-DB queries instantly"]
    
    B -->|"DB-related"| C["🔍 RAG Layer — ChromaDB\nSemantic search with confidence scoring"]
    B -->|"Non-DB"| X1["❌ Rejected\nClean error message"]
    
    C -->|"Score < 1.2\nCONFIDENT"| D["🧠 Supervisor Agent\nOrchestrates specialist agents"]
    C -->|"Score 1.2–1.5\nUNCERTAIN"| X2["⚠️ Honest Warning\nNo hallucination"]
    C -->|"Score > 1.5\nOUT OF SCOPE"| X3["❌ Clean Rejection\nSimilarity too low"]
    
    D --> E["🔬 DiagnosisAgent\nWHY is it slow?\nRAG + LLM reasoning"]
    D --> F["🔧 FixAgent\nWHAT fixes it?\nLLM-generated SQL\n+ Safety Validator"]
    D --> G["📊 ImpactAgent\nWHAT does it cost?\nBusiness impact\ncalculation"]
    
    E --> H["📋 Supervisor\nAssembles reasoning chain\n+ combines all outputs"]
    F --> H
    G --> H
    
    H --> I["⚙️ Technical Mode\nFor developers"]
    H --> J["👤 Simple Mode\nFor support analysts"]
    H --> K["💼 Executive Mode\nFor managers"]
    
    style A fill:#1a1a2e,color:#fff
    style D fill:#16213e,color:#fff
    style E fill:#0f3460,color:#fff
    style F fill:#0f3460,color:#fff
    style G fill:#0f3460,color:#fff
    style H fill:#16213e,color:#fff
    style X1 fill:#4a0000,color:#fff
    style X2 fill:#4a3500,color:#fff
    style X3 fill:#4a0000,color:#fff
    style I fill:#004a00,color:#fff
    style J fill:#004a00,color:#fff
    style K fill:#004a00,color:#fff
```
---

## ✨ Key Features

### 1. Multi-Agent Supervisor Architecture
Three specialist agents orchestrated by a Supervisor — each with a single responsibility. The system returns a full **reasoning chain** showing every decision made, ensuring complete auditability — critical in regulated insurance environments.

### 2. Advanced RAG with Confidence Scoring
Goes beyond basic RAG with similarity threshold scoring:
- Score < 1.2 → confident match → full analysis
- Score 1.2–1.5 → uncertain → honest warning returned
- Score > 1.5 → out of scope → clean rejection

The system knows what it doesn't know. No hallucinated answers on edge cases.

### 3. Agentic Fix Loop with Safety Validator
The FixAgent doesn't just suggest fixes — it **executes them** on a real database:
1. LLM generates the fix SQL autonomously
2. Safety validator whitelists only `CREATE INDEX`, `ANALYZE`, `VACUUM`
3. Fix applied to real SQLite database with 1.7M rows
4. Before/after performance measured and returned as proof

### 4. Natural Language Intent Router (`/ask`)
Single endpoint that accepts anything a user types — raw SQL, plain English symptom description, or vague complaint. Intent classifier routes to the right analysis automatically.

### 5. Audience-Aware Responses
Same diagnosis, three different explanations:
- **Developer:** "Full table scan due to missing index on status column"
- **Support:** "Users experience slow query performance and increased wait times"
- **Executive:** "Business incurs significant productivity losses — urgency: HIGH"

### 6. Enriched Knowledge Base
11 SQL performance cases enriched with real-world symptoms, detection signals, fix validation steps, and Solartis-specific insurance context — enabling semantic matching on natural language descriptions, not just keywords.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| LLM | LLaMA 3.1 8B via Groq API |
| Embeddings | HuggingFace all-MiniLM-L6-v2 (local) |
| Vector DB | ChromaDB (persistent) |
| Orchestration | LangChain LCEL |
| API | FastAPI + Uvicorn |
| Database | SQLite (1.7M rows — policy, claims, logs) |
| Frontend | React + Vite |

---

## 📁 Project Structure
HACKATHON/
├── dataset.json          # Enriched knowledge base (11 cases)
├── README.md
├── backend/
│   ├── main.py           # FastAPI — 6 endpoints
│   ├── supervisor.py     # Multi-agent orchestrator
│   ├── agent.py          # DiagnosisAgent
│   ├── executor.py       # FixAgent — LLM SQL + safety validator
│   ├── rag.py            # RAG layer with confidence scoring
│   ├── database.py       # SQLite schema + 1.7M row seeder
│   └── .env              # GROQ_API_KEY (not committed)
└── frontend/
└── src/
└── App.jsx       # React dashboard

---

## 🚀 How to Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- Free Groq API key from [console.groq.com](https://console.groq.com)

### Backend Setup
```bash
# 1. Clone the repository
git clone https://github.com/Abinaya-092/solartis-hackathon-abinaya-t-92
cd solartis-hackathon-abinaya-t-92

# 2. Install dependencies
pip install fastapi uvicorn langchain langchain-community langchain-groq
pip install langchain-huggingface chromadb sentence-transformers python-dotenv

# 3. Create .env file in backend/
echo "GROQ_API_KEY=your_key_here" > backend/.env

# 4. Start backend (auto-builds ChromaDB and seeds database on first run)
cd backend
python -m uvicorn main:app --reload
```

### Frontend Setup
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

**Note:** On first run, the system automatically:
- Downloads the HuggingFace embedding model (~90MB)
- Builds ChromaDB from dataset.json
- Seeds SQLite with 1.7M rows (takes ~3 minutes)

Subsequent runs start in seconds.

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/analyze/full` | POST | **Main endpoint** — full multi-agent analysis |
| `/ask` | POST | Natural language router with intent detection |
| `/analyze/query` | POST | Direct query analysis |
| `/detect/anomaly` | POST | Anomaly detection with spike ratio |
| `/suggest/optimization` | POST | Prioritized optimization list |
| `/analyze/and/fix` | POST | Agentic fix loop with before/after proof |

### Example Request
```json
POST /analyze/full
{
  "question": "SELECT * FROM policy_data WHERE status = 'ACTIVE' is taking too long",
  "mode": "technical"
}
```

### Example Response
```json
{
  "status": "success",
  "reasoning_chain": [
    "RAG confidence: CONFIDENT (score: 0.80)",
    "Delegating to DiagnosisAgent...",
    "DiagnosisAgent returned: Missing Index on Frequently Filtered Column",
    "Delegating to FixAgent...",
    "FixAgent generated safe SQL: CREATE INDEX idx_status ON policy_data(status)",
    "Safety validated: True",
    "Delegating to ImpactAgent..."
  ],
  "diagnosis": {
    "problem": "Missing Index on Frequently Filtered Column",
    "root_cause": "No index on status column forces full table scan",
    "confidence": "high",
    "similarity_score": 0.8026
  },
  "fix": {
    "sql_executed": "CREATE INDEX idx_status ON policy_data(status)",
    "safe": true,
    "validated_by": "safety_validator",
    "before_ms": 1645,
    "after_ms": 142,
    "improvement": "91.4% faster"
  },
  "impact": {
    "technical": "Full table scan on every query due to missing index",
    "user_facing": "Users experience slow policy search across all modules",
    "executive": "Business incurs productivity losses — HIGH urgency",
    "urgency": "high — impacts all users on every query"
  },
  "audience_summary": "Full table scan occurs on every query due to missing index on status column"
}
```

---

## 🎨 Design Decisions & Trade-offs

### Why SQLite over MySQL/PostgreSQL?
SQLite requires zero installation — evaluators can run the system with a single command. In production, the system would connect to managed PostgreSQL (Supabase/RDS) with connection pooling. The agentic fix loop works identically regardless of the database backend.

### Why LLM-generated SQL over hardcoded patterns?
Early versions used keyword-matching to map diagnoses to SQL fixes. This was brittle — "add index on status" and "create an index for the status field" would fail to match the same pattern. The LLM-generated approach handles any phrasing and any column name, while the safety validator ensures nothing dangerous executes.

### RAG Strategy Decisions
I evaluated four advanced RAG strategies:
- **HyDE** — rejected. At 11 cases, retrieval precision is already high. Would reconsider at 1000+ cases.
- **Reranking** — rejected. LLM reranking doesn't scale; production would need Cohere Rerank.
- **Multi-query retrieval** — rejected. Triples search cost with marginal benefit at small scale.
- **Similarity threshold** ✅ implemented. Zero cost, scales perfectly, prevents hallucination on edge cases.

### Why three separate agents instead of one LLM call?
Single responsibility principle. Each agent has one job, one system prompt, one output schema. This makes the system debuggable, testable, and extensible. Adding a new agent (e.g., a PredictionAgent for future trajectory) requires zero changes to existing agents.

---

## 🚀 Production Scaling Considerations

*Answering the mandatory question: "If you were designing this system for production at scale, what would you change or improve?"*

**1. Vector Database**
Replace ChromaDB with Pinecone or pgvector for millions of cases with horizontal scaling.

**2. LLM Calls**
At 50 requests/minute, 4–5 LLM calls per request = 200–250 Groq calls/minute. Production needs response caching for similar queries, async processing, and batch analysis for non-urgent requests.

**3. Prompt Management**
Replace manual prompt tuning with automated eval pipelines. Libraries like Guardrails AI would enforce output schemas. LangSmith would provide observability into failure patterns across thousands of requests.

**4. Feedback Loop**
Collect user feedback on diagnosis accuracy. Feed successful fixes back into the knowledge base automatically (Institutional Memory pattern). System improves with usage.

**5. Real Database Integration**
Connect to actual MySQL/PostgreSQL production database. Read `EXPLAIN` output directly. Apply fixes with rollback capability. Measure real query plans, not just execution time.

**6. Agent Orchestration**
Replace custom supervisor with LangGraph for proper agent state management, conditional routing, and parallel agent execution. DiagnosisAgent and ImpactAgent could run in parallel since they're independent.

**7. Security**
Current safety validator whitelists `CREATE INDEX`, `ANALYZE`, `VACUUM`. Production needs role-based access control — read-only analysis for support teams, fix execution only for DBAs.

---

## 🤖 AI Usage Disclosure

As required by the challenge guidelines:

**Tools used:** Claude (Anthropic), for architectural guidance and code review

**What I used AI for:**
- Discussing system architecture and trade-offs
- Reviewing code for bugs and improvements
- Understanding LangChain API changes between versions
- Enriching the dataset with real-world symptoms and context

**What I built and own:**
- System architecture decisions (chose SQLite over Supabase after risk analysis)
- Multi-agent supervisor design
- Safety validator logic
- Similarity threshold values (derived from real score measurements)
- All debugging and integration work
- Every line was read, understood, and intentionally placed

**What I changed/improved beyond AI suggestions:**
- Added epistemic honesty — system admits uncertainty instead of hallucinating
- Chose not to implement HyDE/reranking after analyzing production trade-offs
- Designed audience-aware responses based on real user personas
- Added `already_existed` fix handling to prevent misleading metrics

**Challenges faced:**
- LangChain version conflicts between `langchain.schema` and `langchain_core.documents`
- SQLite index performance on SSDs — learned that low-cardinality columns don't benefit from indexes when result sets are large
- LLM occasionally returning invalid JSON — solved with regex extraction and schema validation

---

## 📊 Dataset

11 SQL performance cases covering:
- Full table scans
- JSON field filtering (MySQL JSON_EXTRACT)
- High frequency config queries
- Complex joins with JSON processing
- Anomaly detection (sudden latency spikes)
- Nested subqueries
- Aggregation with multiple joins
- Large logging table queries
- Bulk update performance
- Knowledge base config lookups
- Missing index on filtered columns

Each case enriched with: symptoms, detection signals, real-world insurance context, fix validation steps, and related patterns — enabling semantic matching on natural language descriptions.

---

*Built with curiosity, ownership, and a lot of terminal windows — Abinaya T, April 2026*