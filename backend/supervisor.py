import json
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from rag import search_cases_with_confidence
from agent import SQLPerformanceAgent
from executor import generate_fix_sql, apply_fix, measure_query, generate_benchmark_query

# ── The three specialist agents ───────────────────────────────────

class DiagnosisAgent:
    """
    Specialist: WHY is the query slow?
    Uses RAG to find similar cases, LLM to diagnose.
    """
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        self.prompt = ChatPromptTemplate.from_template("""
You are a Database Reliability Engineer specializing in ROOT CAUSE ANALYSIS.
Your ONLY job is to diagnose WHY a query is slow.
Return ONLY a JSON object.

RETRIEVED CASES:
{context}

USER QUERY:
{question}

Return ONLY this JSON:
{{
    "problem": "specific problem name",
    "root_cause": "detailed technical root cause",
    "confidence": "high/medium/low",
    "pattern_matched": "which known pattern this matches"
}}
""")

    def analyze(self, question: str, docs: list) -> dict:
        context_str = "\n\n".join([
            f"Case: {d.metadata['title']}\nProblem: {d.metadata['problem']}\nRoot Cause: {d.metadata['root_cause']}\nSeverity: {d.metadata['severity']}"
            for d in docs
        ])
        chain = self.prompt | self.llm
        raw = chain.invoke({"context": context_str, "question": question}).content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)


class FixAgent:
    """
    Specialist: WHAT SQL fixes it?
    Generates safe SQL, validates it, applies to real database.
    """
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    def generate_and_apply(self, problem: str, root_cause: str, suggestion: str, user_query: str) -> dict:
        # Generate benchmark query
        pattern = generate_benchmark_query(problem, suggestion, user_query)
        query = pattern["query"]

        # Measure before
        before = measure_query(query)

        # Generate safe fix SQL
        fix_sql = generate_fix_sql(problem, suggestion, root_cause)

        if not fix_sql:
            return {
                "fix_sql": None,
                "safe": False,
                "action_taken": "No safe fix could be generated",
                "query_benchmarked": query,
                "before_ms": before["execution_ms"],
                "after_ms": before["execution_ms"],
                "improvement": "no fix available"
            }
        
        # Apply fix
        fix_result = apply_fix(fix_sql)

        # If fix already existed — skip after measurement
        # timing variance is meaningless when nothing changed
        if fix_result.get("already_existed"):
            return {
                "fix_sql": fix_sql,
                "safe": True,
                "validated_by": "safety_validator",
                "action_taken": fix_result["action_taken"],
                "already_existed": True,
                "query_benchmarked": query,
                "before_ms": before["execution_ms"],
                "after_ms": None,
                "improvement": "fix already applied — no measurement needed"
            }

        # Measure after only if fix was newly applied
        after = measure_query(query)

        # Calculate improvement
        if before["execution_ms"] > 0 and after["execution_ms"] < before["execution_ms"]:
            pct = ((before["execution_ms"] - after["execution_ms"]) / before["execution_ms"]) * 100
            improvement = f"{round(pct, 1)}% faster"
        else:
            improvement = "marginal improvement"

        return {
            "fix_sql": fix_sql,
            "safe": True,
            "validated_by": "safety_validator",
            "action_taken": fix_result["action_taken"],
            "already_existed": False,
            "query_benchmarked": query,
            "before_ms": before["execution_ms"],
            "after_ms": after["execution_ms"],
            "improvement": improvement
        }

class ImpactAgent:
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        self.prompt = ChatPromptTemplate.from_template("""
You are a Database Impact Analyst. Return ONLY a JSON object. No markdown, no explanation, no text outside the JSON.

PROBLEM: {problem}
ROOT CAUSE: {root_cause}
EXECUTION TIME: {execution_time}ms

Return ONLY this exact JSON with no extra text:
{{
    "technical_impact": "what is happening at DB level in one sentence",
    "user_impact": "what users experience in one sentence",
    "executive_impact": "business cost and risk in one sentence",
    "estimated_daily_cost": "estimated productivity hours lost per day",
    "trajectory": "gets worse over time as data grows",
    "urgency": "high — impacts all users on every query",
    "fix_roi": "fixing saves significant daily productivity"
}}
""")

    def calculate(self, problem: str, root_cause: str, execution_time_ms: float) -> dict:
        chain = self.prompt | self.llm
        raw = chain.invoke({
            "problem": problem,
            "root_cause": root_cause,
            "execution_time": execution_time_ms
        }).content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # Find JSON object — extract only the first { } block
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

        return json.loads(raw)

# ── The Supervisor — orchestrates all three agents ─────────────────

class SupervisorAgent:
    """
    Orchestrates DiagnosisAgent, FixAgent, and ImpactAgent.
    Maintains reasoning chain showing every decision made.
    """
    def __init__(self):
        self.diagnosis_agent = DiagnosisAgent()
        self.fix_agent = FixAgent()
        self.impact_agent = ImpactAgent()

    def run(self, question: str, mode: str = "technical") -> dict:
        reasoning_chain = []
        reasoning_chain.append(f"Received query: '{question[:60]}...' " if len(question) > 60 else f"Received query: '{question}'")

        # ── Step 1: RAG with confidence ───────────────────────────
        reasoning_chain.append("Searching knowledge base with confidence scoring...")
        search_result = search_cases_with_confidence(question, k=3)

        if search_result["confidence_level"] == "out_of_scope":
            reasoning_chain.append(f"RAG confidence: OUT OF SCOPE (score: {search_result['best_score']})")
            reasoning_chain.append("Supervisor decision: reject — outside knowledge base")
            return {
                "status": "out_of_scope",
                "reasoning_chain": reasoning_chain,
                "error": "Query pattern is outside my knowledge base.",
                "similarity_score": search_result["best_score"]
            }

        docs = search_result["docs"]
        reasoning_chain.append(f"RAG confidence: {search_result['confidence_level'].upper()} (score: {search_result['best_score']})")
        reasoning_chain.append(f"Top match: {docs[0].metadata['title']}")

        # ── Step 2: DiagnosisAgent ────────────────────────────────
        reasoning_chain.append("Delegating to DiagnosisAgent...")
        try:
            diagnosis = self.diagnosis_agent.analyze(question, docs)
            reasoning_chain.append(f"DiagnosisAgent returned: {diagnosis.get('problem', 'unknown')}")
            reasoning_chain.append(f"Confidence: {diagnosis.get('confidence', 'unknown')}")
        except Exception as e:
            reasoning_chain.append(f"DiagnosisAgent failed: {str(e)}")
            diagnosis = {
                "problem": "Diagnosis failed",
                "root_cause": str(e),
                "confidence": "low",
                "pattern_matched": "unknown"
            }

        # ── Step 3: FixAgent ──────────────────────────────────────
        reasoning_chain.append("Delegating to FixAgent...")
        try:
            suggestion = docs[0].metadata.get("suggestion", "")
            fix = self.fix_agent.generate_and_apply(
                problem=diagnosis.get("problem", ""),
                root_cause=diagnosis.get("root_cause", ""),
                suggestion=suggestion,
                user_query=question
            )
            if fix["fix_sql"]:
                reasoning_chain.append(f"FixAgent generated safe SQL: {fix['fix_sql']}")
                reasoning_chain.append(f"Safety validated: {fix['safe']}")
                if fix.get("already_existed"):
                    reasoning_chain.append(f"Before measurement: {fix['before_ms']}ms — {fix['improvement']}")
                else:
                    reasoning_chain.append(f"Performance: {fix['before_ms']}ms → {fix['after_ms']}ms ({fix['improvement']})")
            else:
                reasoning_chain.append("FixAgent: no safe fix available for this pattern")
        except Exception as e:
            reasoning_chain.append(f"FixAgent failed: {str(e)}")
            fix = {"fix_sql": None, "safe": False, "action_taken": str(e), "improvement": "unknown"}

        # ── Step 4: ImpactAgent ───────────────────────────────────
        reasoning_chain.append("Delegating to ImpactAgent...")
        try:
            impact = self.impact_agent.calculate(
                problem=diagnosis.get("problem", ""),
                root_cause=diagnosis.get("root_cause", ""),
                execution_time_ms=fix.get("before_ms", 0)
            )
            reasoning_chain.append(f"ImpactAgent: urgency={impact.get('urgency', 'unknown')}")
        except Exception as e:
            reasoning_chain.append(f"ImpactAgent failed: {str(e)}")
            impact = {"error": str(e)}

        # ── Step 5: Supervisor assembles final response ───────────
        reasoning_chain.append("Supervisor assembling final response...")
        reasoning_chain.append(f"Response mode: {mode}")

        # Build mode-aware impact summary
        if mode == "simple":
            audience_summary = impact.get("user_impact", "Performance issue detected.")
        elif mode == "executive":
            audience_summary = impact.get("executive_impact", "Business impact detected.")
        else:
            audience_summary = impact.get("technical_impact", "Technical issue detected.")

        reasoning_chain.append("Response ready. Returning to user.")

        return {
            "status": "success",
            "mode": mode,
            "reasoning_chain": reasoning_chain,

            "diagnosis": {
                "problem": diagnosis.get("problem"),
                "root_cause": diagnosis.get("root_cause"),
                "pattern_matched": diagnosis.get("pattern_matched"),
                "confidence": diagnosis.get("confidence"),
                "similarity_score": search_result["best_score"],
                "matched_cases": [d.metadata["title"] for d in docs]
            },

            "fix": {
                "sql_executed": fix.get("fix_sql"),
                "safe": fix.get("safe"),
                "validated_by": fix.get("validated_by"),
                "action_taken": fix.get("action_taken"),
                "query_benchmarked": fix.get("query_benchmarked"),
                "before_ms": fix.get("before_ms"),
                "after_ms": fix.get("after_ms"),
                "improvement": fix.get("improvement")
            },

            "impact": {
                "technical": impact.get("technical_impact"),
                "user_facing": impact.get("user_impact"),
                "executive": impact.get("executive_impact"),
                "estimated_daily_cost": impact.get("estimated_daily_cost"),
                "trajectory": impact.get("trajectory"),
                "urgency": impact.get("urgency"),
                "fix_roi": impact.get("fix_roi")
            },

            "audience_summary": audience_summary
        }