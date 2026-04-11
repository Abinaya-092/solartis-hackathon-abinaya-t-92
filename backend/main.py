import os
import json
import re
from database import init_db, DB_PATH
from executor import analyze_and_fix
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from agent import SQLPerformanceAgent
from rag import load_vectordb, build_vectordb, search_cases, search_cases_with_confidence
from supervisor import SupervisorAgent
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Solartis SQL Performance Analyzer",
    description="RAG-powered SQL query analysis API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Startup ───────────────────────────────────────────────────────
agent = SQLPerformanceAgent()
supervisor = SupervisorAgent()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "dataset.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

if not os.path.exists(CHROMA_PATH):
    print("Building DB...")
    build_vectordb(dataset_path=DATASET_PATH)
else:
    print("chroma_db found. Loading existing DB...")

init_db()

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

        # Confidence-aware search
        search_result = search_cases_with_confidence(search_query, k=3)

        # Out of scope — reject cleanly
        if search_result["confidence_level"] == "out_of_scope":
            return {
                "error": "Query pattern is outside my knowledge base.",
                "suggestion": "This system specializes in SQL performance issues. Try describing a specific slow query pattern.",
                "confidence": "low",
                "similarity_score": search_result["best_score"]
            }

        # Uncertain — return honest message without wasting LLM call
        if search_result["confidence_level"] == "uncertain":
            docs = search_result["docs"]
            return {
                "warning": "This query pattern is not well represented in my knowledge base.",
                "closest_match": docs[0].metadata["title"] if docs else "none",
                "suggestion": "Try rephrasing with more specific SQL performance terms.",
                "confidence": "low",
                "similarity_score": search_result["best_score"]
            }

        # Confident match — full analysis
        docs = search_result["docs"]
        raw = agent.analyze(request.query, docs)
        result = json.loads(raw)

        if result.get("confidence") not in VALID_CONFIDENCE:
            result["confidence"] = "high"

        result["matched_cases"] = [d.metadata["title"] for d in docs]
        result["similarity_score"] = search_result["best_score"]
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

        # Step 3: Confidence-aware search
        if intent == "anomaly":
            search_query = f"sudden latency spike anomaly {question}"
        elif intent == "optimization":
            search_query = question
        else:
            search_query = question

        search_result = search_cases_with_confidence(search_query, k=3)

        # Out of scope — reject cleanly
        if search_result["confidence_level"] == "out_of_scope":
            return {
                "error": "Query pattern is outside my knowledge base.",
                "suggestion": "This system specializes in SQL performance issues. Try describing a specific slow query pattern.",
                "confidence": "low",
                "intent_detected": intent,
                "similarity_score": search_result["best_score"]
            }

        docs = search_result["docs"]

        # Step 4: Route to the right logic
        if intent == "anomaly":
            raw = agent.analyze(question, docs)
            result = json.loads(raw)
            if result.get("confidence") not in VALID_CONFIDENCE:
                result["confidence"] = "high"
            if search_result["confidence_level"] == "uncertain":
                result["confidence"] = "low"
                result["warning"] = search_result["warning"]
            result["intent_detected"] = "anomaly"
            result["matched_cases"] = [d.metadata["title"] for d in docs]
            result["similarity_score"] = search_result["best_score"]
            return result

        elif intent == "optimization":
            context_str = "\n\n".join([
                f"Case: {d.metadata['title']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}\nSpecific Impact: {d.metadata['suggestion']}"
                for d in docs
            ])
            opt_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
            opt_prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer. Return ONLY a JSON object.

QUESTION: {question}
RELEVANT CASES: {context}

Priority must be one of: high, medium, low.
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
            if search_result["confidence_level"] == "uncertain":
                result["confidence"] = "low"
                result["warning"] = search_result["warning"]

            result["intent_detected"] = "optimization"
            result["similarity_score"] = search_result["best_score"]
            return result

        else:  # analysis (default)
            # If uncertain — don't waste LLM call, return honest message
            if search_result["confidence_level"] == "uncertain":
                return {
                    "warning": "This query pattern is not well represented in my knowledge base.",
                    "closest_match": docs[0].metadata["title"] if docs else "none",
                    "suggestion": "Try rephrasing with more specific SQL performance terms, or consult a DBA for this pattern.",
                    "confidence": "low",
                    "intent_detected": intent,
                    "similarity_score": search_result["best_score"]
                }

            raw = agent.analyze(question, docs)
            result = json.loads(raw)
            if result.get("confidence") not in VALID_CONFIDENCE:
                result["confidence"] = "high"
            result["intent_detected"] = "analysis"
            result["matched_cases"] = [d.metadata["title"] for d in docs]
            result["similarity_score"] = search_result["best_score"]
            return result

    except json.JSONDecodeError:
        return {"raw_response": raw, "error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ── Endpoint 5: /analyze/and/fix ──────────────────────────────────
@app.post("/analyze/and/fix")
def analyze_and_fix_endpoint(request: QueryRequest):
    """
    Full agentic loop — diagnoses the problem AND fixes it.
    Returns before/after performance proof.
    """
    try:
        if not any(word in request.query.lower() for word in DB_KEYWORDS):
            return {
                "error": "Query does not appear to be database-related.",
                "confidence": "low"
            }

        # Step 1 — RAG + LLM diagnosis
        docs = search_cases(request.query, k=3)
        raw = agent.analyze(request.query, docs)
        diagnosis = json.loads(raw)

        if diagnosis.get("confidence") not in VALID_CONFIDENCE:
            diagnosis["confidence"] = "high"

        # Step 2 — Agentic fix + measurement
        fix_proof = analyze_and_fix(
            problem=diagnosis.get("problem", ""),
            root_cause=diagnosis.get("root_cause", ""),
            suggestion=diagnosis.get("suggestion", ""),
            user_query=request.query  # ADD THIS
        )

        # Step 3 — Combine diagnosis + proof
        return {
            "diagnosis": diagnosis,
            "proof": fix_proof,
            "matched_cases": [d.metadata["title"] for d in docs]
        }

    except json.JSONDecodeError:
        return {"error": "LLM returned non-JSON."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Request model ─────────────────────────────────────────────────
class FullAnalysisRequest(BaseModel):
    question: str
    mode: str = "technical"  # technical | simple | executive

# ── Endpoint 6: /analyze/full — Multi-Agent Orchestration ─────────
@app.post("/analyze/full")
def analyze_full(request: FullAnalysisRequest):
    """
    Full multi-agent analysis.
    Supervisor orchestrates DiagnosisAgent, FixAgent, ImpactAgent.
    Returns diagnosis + fix proof + business impact + reasoning chain.
    """
    try:
        if not any(word in request.question.lower() for word in DB_KEYWORDS):
            return {
                "status": "rejected",
                "error": "Question does not appear to be database-related.",
                "confidence": "low"
            }

        if request.mode not in {"technical", "simple", "executive"}:
            return {
                "status": "rejected",
                "error": "Invalid mode. Use: technical, simple, or executive"
            }

        result = supervisor.run(
            question=request.question,
            mode=request.mode
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
    
     
@app.post("/suggest/similar")
def suggest_similar(request: AskRequest):
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
            "/analyze/query",
            "/detect/anomaly",
            "/suggest/optimization",
            "/ask",
            "/analyze/and/fix",
            "/analyze/full",
            "/suggest/similar"
        ]
    }