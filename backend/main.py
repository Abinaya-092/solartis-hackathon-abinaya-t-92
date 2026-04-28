import os
import json
import re
from database import init_db
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from rag import build_vectordb, search_cases_with_confidence
from supervisor import SupervisorAgent
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="SQL Performance Analyzer",
    description="Multi-Agent RAG-powered SQL query analysis API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────
supervisor = SupervisorAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "dataset.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

if not os.path.exists(CHROMA_PATH):
    print("Building ChromaDB from dataset...")
    build_vectordb(dataset_path=DATASET_PATH)
else:
    print("ChromaDB found. Loading existing DB...")

init_db()

# ── Smart domain validation ───────────────────────────────────────
OBVIOUS_DB_KEYWORDS = [
    "select", "query", "sql", "table", "index", "database",
    "join", "slow", "latency", "performance", "update", "insert",
    "delete", "scan", "timeout", "cache", "lock", "optimize",
    "procedure", "execution", "reporting", "queries"
]

NON_DB_KEYWORDS = [
    "pasta", "recipe", "cook", "movie", "weather",
    "football", "cricket", "music", "song", "food"
]

def is_db_related(question: str) -> bool:
    q = question.lower()
    if any(word in q for word in OBVIOUS_DB_KEYWORDS):
        return True
    if any(word in q for word in NON_DB_KEYWORDS):
        return False
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        prompt = f"""Is this question related to database performance, SQL queries, system performance, or data retrieval issues?

Question: "{question}"

Reply with only YES or NO."""
        response = llm.invoke(prompt).content.strip().upper()
        return "YES" in response
    except:
        return True

# ── Helper — normalize confidence ─────────────────────────────────
VALID_CONFIDENCE = {"high", "medium", "low"}

def normalize_confidence(result: dict) -> dict:
    if result.get("confidence") not in VALID_CONFIDENCE:
        result["confidence"] = "high"
    return result

# ── Request models ────────────────────────────────────────────────
class FullAnalysisRequest(BaseModel):
    question: str
    mode: str = "technical"

class SuggestRequest(BaseModel):
    question: str

# ── Endpoint 1: /analyze/full — Main endpoint ─────────────────────
@app.post("/analyze/full")
def analyze_full(request: FullAnalysisRequest):
    """
    Full multi-agent analysis.
    Supervisor orchestrates DiagnosisAgent, FixAgent, ImpactAgent.
    Returns diagnosis + fix proof + business impact + reasoning chain.
    """
    try:
        if not is_db_related(request.question):
            return {
                "error": "Question does not appear to be database-related.",
                "suggestion": "Please describe a SQL performance issue.",
                "confidence": "low"
            }

        if request.mode not in {"technical", "simple", "executive"}:
            return {
                "status": "rejected",
                "error": "Invalid mode. Use: technical, simple, or executive"
            }

        return supervisor.run(
            question=request.question,
            mode=request.mode
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint 2: /suggest/similar — Dynamic suggestions ───────────
@app.post("/suggest/similar")
def suggest_similar(request: SuggestRequest):
    """
    Given a vague query, generates dynamic similar example queries
    based on known performance patterns.
    """
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
        prompt = ChatPromptTemplate.from_template("""
You are a database performance expert. A user described a vague database issue.
Generate 4 specific example queries they might actually mean.

IMPORTANT: Your suggestions must be related to these known performance patterns:
- Full table scan (SELECT * with no WHERE clause)
- JSON field filtering (JSON_EXTRACT in WHERE clause)
- High frequency config queries (repeated lookups with no cache)
- Complex joins with JSON processing
- Anomaly / sudden latency spike
- Nested subqueries (WHERE IN subquery)
- Aggregation with multiple joins
- Large logging table queries
- Bulk update performance
- Missing index on filtered column

User said: "{question}"

Generate 4 suggestions that are:
1. Related to what the user described
2. Matching one of the known patterns above
3. Specific and actionable

Return ONLY a JSON array of 4 strings. No markdown, no explanation.
""")
        chain = prompt | llm
        raw = chain.invoke({"question": request.question}).content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        suggestions = json.loads(raw)
        return {"suggestions": suggestions[:4]}
    except Exception as e:
        return {"suggestions": [
            "Why is SELECT * FROM policy_data WHERE status = 'ACTIVE' slow?",
            "My JSON query using JSON_EXTRACT is taking 25 seconds",
            "Query suddenly spiked from 1s to 50s with no code changes",
            "SELECT * FROM large_table with no WHERE clause is very slow"
        ]}


# ── Health check ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "endpoints": [
            "/analyze/full",
            "/suggest/similar"
        ]
    }