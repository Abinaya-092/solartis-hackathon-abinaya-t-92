import os
import json
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from rag import load_vectordb, build_vectordb, search_cases
from agent import SQLPerformanceAgent

load_dotenv()

app = FastAPI(
    title="Solartis SQL Performance Analyzer",
    description="RAG-powered SQL query analysis API",
    version="1.0.0"
)

# ── Startup ───────────────────────────────────────────────────────
agent = SQLPerformanceAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "dataset.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

if not os.path.exists(CHROMA_PATH):
    print("Building DB...")
    build_vectordb(dataset_path=DATASET_PATH)
else:
    print("chroma_db found. Loading existing DB...")

# ── DB keywords for domain validation ────────────────────────────
DB_KEYWORDS = ["query", "select", "table", "index", "slow", "database",
               "sql", "join", "update", "scan", "insert", "delete",
               "latency", "timeout", "performance", "cache", "lock"]

VALID_CONFIDENCE = {"high", "medium", "low"}

# ── Request models ────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    execution_time: str = "unknown"

class AnomalyRequest(BaseModel):
    query: str
    current_time: str
    baseline_time: str

# ── Endpoint 1: /analyze/query ────────────────────────────────────
@app.post("/analyze/query")
def analyze_query(request: QueryRequest):
    """
    Takes a slow SQL query description.
    Returns: problem, root_cause, suggestion, confidence.
    """
    try:
        # Domain validation
        if not any(word in request.query.lower() for word in DB_KEYWORDS):
            return {
                "error": "Query does not appear to be database-related.",
                "suggestion": "Please describe a SQL performance issue.",
                "confidence": "low"
            }

        search_query = request.query
        if request.execution_time != "unknown":
            search_query += f" execution time {request.execution_time}"

        docs = search_cases(search_query, k=3)
        raw = agent.analyze(request.query, docs)
        result = json.loads(raw)

        # Normalize confidence
        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "high"

        result["matched_cases"] = [d.metadata["title"] for d in docs]
        return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint 2: /detect/anomaly ───────────────────────────────────
@app.post("/detect/anomaly")
def detect_anomaly(request: AnomalyRequest):
    """
    Detects if a latency spike is anomalous.
    Returns: is_anomaly, spike_ratio, problem, suggestion.
    """
    try:
        def parse_seconds(t):
            try:
                return float(re.sub(r"[^\d.]", "", t).strip())
            except:
                return None

        current = parse_seconds(request.current_time)
        baseline = parse_seconds(request.baseline_time)
        ratio = round(current / baseline, 1) if current and baseline else None

        search_query = f"sudden latency spike anomaly {request.query}"
        docs = search_cases(search_query, k=2)
        raw = agent.analyze(
            f"Query: {request.query}. Baseline: {request.baseline_time}, Current: {request.current_time}. Why did this spike?",
            docs
        )
        result = json.loads(raw)

        # Normalize confidence
        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "high"

        result["is_anomaly"] = (ratio is not None and ratio >= 2)
        result["spike_ratio"] = f"{ratio}x" if ratio else "unknown"
        result["matched_cases"] = [d.metadata["title"] for d in docs]
        return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint 3: /suggest/optimization ────────────────────────────
@app.post("/suggest/optimization")
def suggest_optimization(request: QueryRequest):
    """
    Proactively suggests optimizations for a given query pattern.
    Returns: optimizations list with priority and impact.
    """
    try:
        # Domain validation
        if not any(word in request.query.lower() for word in DB_KEYWORDS):
            return {
                "error": "Query does not appear to be database-related.",
                "suggestion": "Please describe a SQL performance issue.",
                "confidence": "low"
            }

        docs = search_cases(request.query, k=3)
        context_str = "\n\n".join([
            f"Case: {d.metadata['title']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}\nImpact: Resolving this can significantly reduce query execution time and DB load."
            for d in docs
        ])

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer. Return ONLY a JSON object. No markdown, no explanation.

QUERY PATTERN: {question}

RELEVANT CASES:
{context}

Return ONLY this exact JSON format:
{{
  "optimizations": [
    {{"priority": "high", "action": "specific technical action to take", "impact": "what improvement this will cause"}},
    {{"priority": "medium", "action": "specific technical action to take", "impact": "what improvement this will cause"}}
  ],
  "estimated_improvement": "e.g. 80% reduction in query time",
  "confidence": "high/medium/low"
}}
""")
        chain = prompt | llm
        raw = chain.invoke({"context": context_str, "question": request.query}).content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        # Normalize confidence
        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "high"

        return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health check ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "endpoints": ["/analyze/query", "/detect/anomaly", "/suggest/optimization"]
    }