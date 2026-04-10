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
VALID_PRIORITY = {"high", "medium", "low"}

# ── Request models ────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    execution_time: str = "unknown"

class AnomalyRequest(BaseModel):
    query: str
    current_time: str
    baseline_time: str

class AskRequest(BaseModel):
    question: str

# ── Endpoint 1: /analyze/query ────────────────────────────────────
@app.post("/analyze/query")
def analyze_query(request: QueryRequest):
    """
    Takes a slow SQL query description.
    Returns: problem, root_cause, suggestion, confidence.
    """
    try:
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
        if not any(word in request.query.lower() for word in DB_KEYWORDS):
            return {
                "error": "Query does not appear to be database-related.",
                "suggestion": "Please describe a SQL performance issue.",
                "confidence": "low"
            }

        docs = search_cases(request.query, k=3)
        context_str = "\n\n".join([
            f"Case: {d.metadata['title']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}\nSpecific Impact: {d.metadata['suggestion']}"
            for d in docs
        ])

        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer. Return ONLY a JSON object. No markdown, no explanation.

QUERY PATTERN: {question}

RELEVANT CASES:
{context}

Return ONLY this exact JSON format.
Priority rules: 
- "high" = fixes the core performance problem directly
- "medium" = important but secondary improvement  
- "low" = nice to have, minimal immediate impact
Not everything can be high priority. Distribute priorities realistically.
Impact must be a specific measurable outcome like "eliminates full table scan" or "reduces DB load by 90%":
{{
  "optimizations": [
    {{"priority": "high", "action": "specific technical action to take", "impact": "specific measurable outcome"}},
    {{"priority": "medium", "action": "specific technical action to take", "impact": "specific measurable outcome"}}
  ],
  "estimated_improvement": "e.g. 80% reduction in query time",
  "confidence": "high/medium/low"
}}
""")
        chain = prompt | llm
        raw = chain.invoke({"context": context_str, "question": request.query}).content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "high"

        for opt in result.get("optimizations", []):
            if opt.get("priority") not in VALID_PRIORITY:
                opt["priority"] = "high"

        return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoint 4: /ask — Natural Language Front Door ────────────────
@app.post("/ask")
def ask(request: AskRequest):
    """
    Accepts any natural language question about SQL performance.
    Automatically detects intent and routes to the right analysis.
    """
    try:
        question = request.question.strip()

        # Step 1: Domain validation
        if not any(word in question.lower() for word in DB_KEYWORDS):
            return {
                "error": "Question does not appear to be database-related.",
                "suggestion": "Try asking about slow queries, indexes, joins, or performance issues.",
                "confidence": "low"
            }

        # Step 2: Intent detection
        intent_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        intent_prompt = ChatPromptTemplate.from_template("""
You are a query intent classifier. Read the user's question carefully.

Definitions:
- "anomaly": user mentions a SUDDEN change, spike, or unexpected degradation that wasn't there before. Keywords: suddenly, spike, jumped, used to be fast, no code changes, unexpectedly.
- "optimization": user asks HOW TO IMPROVE or WHAT TO CHANGE proactively. Keywords: how can I, what should I change, optimize, improve, best way.
- "analysis": user asks WHY something is slow or wants a diagnosis. This is the default for most questions.

User question: {question}

Return ONLY one word: anomaly, optimization, or analysis
""")
        intent_chain = intent_prompt | intent_llm
        intent = intent_chain.invoke({"question": question}).content.strip().lower()

        if intent not in {"anomaly", "optimization", "analysis"}:
            intent = "analysis"

        # Step 3: Route to the right logic
        if intent == "anomaly":
            docs = search_cases(f"sudden latency spike anomaly {question}", k=2)
            raw = agent.analyze(question, docs)
            result = json.loads(raw)
            if result.get("confidence") not in VALID_CONFIDENCE:
                result["confidence"] = "high"
            result["intent_detected"] = "anomaly"
            result["matched_cases"] = [d.metadata["title"] for d in docs]
            return result

        elif intent == "optimization":
            docs = search_cases(question, k=3)
            context_str = "\n\n".join([
                f"Case: {d.metadata['title']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}\nSpecific Impact: {d.metadata['suggestion']}"
                for d in docs
            ])
            opt_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
            opt_prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer. Return ONLY a JSON object.

QUESTION: {question}
RELEVANT CASES: {context}

Priority rules: 
- "high" = fixes the core performance problem directly
- "medium" = important but secondary improvement  
- "low" = nice to have, minimal immediate impact
Not everything can be high priority. Distribute priorities realistically.
Impact must be specific and measurable like "eliminates full table scan" or "reduces DB load by 90%".

Return ONLY this JSON:
{{
  "optimizations": [
    {{"priority": "high", "action": "specific technical action", "impact": "specific measurable outcome"}},
    {{"priority": "medium", "action": "specific technical action", "impact": "specific measurable outcome"}}
  ],
  "estimated_improvement": "e.g. 80% reduction in query time",
  "confidence": "high/medium/low"
}}
""")
            opt_chain = opt_prompt | opt_llm
            raw = opt_chain.invoke({"context": context_str, "question": question}).content.strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)

            if result.get("confidence") not in VALID_CONFIDENCE:
                result["confidence"] = "high"
            for opt in result.get("optimizations", []):
                if opt.get("priority") not in VALID_PRIORITY:
                    opt["priority"] = "high"

            result["intent_detected"] = "optimization"
            return result

        else:  # analysis (default)
            docs = search_cases(question, k=3)
            raw = agent.analyze(question, docs)
            result = json.loads(raw)
            if result.get("confidence") not in VALID_CONFIDENCE:
                result["confidence"] = "high"
            result["intent_detected"] = "analysis"
            result["matched_cases"] = [d.metadata["title"] for d in docs]
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
        "endpoints": ["/analyze/query", "/detect/anomaly", "/suggest/optimization", "/ask"]
    }