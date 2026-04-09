import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from rag import load_vectordb, build_vectordb, search_cases
from agent import SQLPerformanceAgent

load_dotenv()

app = FastAPI(
    title="Solartis SQL Performance Analyzer",
    description="RAG-powered SQL query analysis API",
    version="1.0.0"
)

# ── Startup: load or build vector DB once ─────────────────────────
agent = SQLPerformanceAgent()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "dataset.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

if not os.path.exists(CHROMA_PATH):
    print("Building DB...")
    build_vectordb(dataset_path=DATASET_PATH)
else:
    print("chroma_db found. Loading existing DB...")

# ── Request/Response models ───────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    execution_time: str = "unknown"  # optional context

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
        # Build search query with optional execution time context
        search_query = request.query
        if request.execution_time != "unknown":
            search_query += f" execution time {request.execution_time}"

        docs = search_cases(search_query, k=3)
        raw = agent.analyze(request.query, docs)
        result = json.loads(raw)
        result["matched_cases"] = [d.metadata["title"] for d in docs]
        return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON. Raw response above."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint 2: /detect/anomaly ───────────────────────────────────
@app.post("/detect/anomaly")
def detect_anomaly(request: AnomalyRequest):
    """
    Detects if a latency spike is anomalous.
    Returns: is_anomaly, severity, explanation, suggestion.
    """
    try:
        # Parse times for ratio calculation
        def parse_seconds(t):
            try:
                return float(t.replace("s", "").replace("sec", "").strip())
            except:
                return None

        current = parse_seconds(request.current_time)
        baseline = parse_seconds(request.baseline_time)
        ratio = round(current / baseline, 1) if current and baseline else None

        # Build an anomaly-aware search query
        search_query = f"sudden latency spike anomaly {request.query}"
        docs = search_cases(search_query, k=2)
        raw = agent.analyze(
            f"Query: {request.query}. Baseline: {request.baseline_time}, Current: {request.current_time}. Is this an anomaly?",
            docs
        )
        result = json.loads(raw)

        # Enrich with anomaly metadata
        result["is_anomaly"] = True if ratio and ratio >= 2 else False
        result["spike_ratio"] = f"{ratio}x" if ratio else "unknown"
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
        docs = search_cases(request.query, k=3)

        # Override agent prompt slightly for optimization focus
        context_str = "\n".join([
            f"Case: {d.metadata['title']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}"
            for d in docs
        ])

        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer. Return ONLY a JSON object.

QUERY PATTERN: {question}

RELEVANT CASES:
{context}

Return this exact format:
{{
  "optimizations": [
    {{"priority": "high", "action": "...", "impact": "..."}},
    {{"priority": "medium", "action": "...", "impact": "..."}}
  ],
  "estimated_improvement": "e.g. 80% reduction in query time",
  "confidence": "high/medium/low"
}}
""")
        chain = prompt | llm
        raw = chain.invoke({"context": context_str, "question": request.query}).content.strip()
        raw = raw.replace("```json", "").replace("```", "")
        return json.loads(raw)

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