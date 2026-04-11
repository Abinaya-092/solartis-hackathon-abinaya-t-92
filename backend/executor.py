import sqlite3
import time
import re
from database import get_connection
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# ── Safety validator ──────────────────────────────────────────────
# ONLY these SQL operations are allowed to execute
SAFE_PREFIXES = [
    "CREATE INDEX",
    "ANALYZE",
    "VACUUM",
]

def is_safe_sql(sql: str) -> bool:
    """
    Validates that LLM-generated SQL is safe to execute.
    Only allows CREATE INDEX, ANALYZE, VACUUM.
    Rejects anything that could modify or destroy data.
    """
    if not sql or sql.upper() == "NONE":
        return False
    cleaned = sql.strip().upper()
    return any(cleaned.startswith(prefix) for prefix in SAFE_PREFIXES)

# ── LLM-generated fix SQL ─────────────────────────────────────────
def generate_fix_sql(problem: str, suggestion: str, root_cause: str) -> str | None:
    """
    Asks the LLM to generate a safe SQL fix based on the diagnosis.
    Validates the output before returning.
    """
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    prompt = ChatPromptTemplate.from_template("""
You are a database fix generator for SQLite. Your job is to generate ONE safe SQL statement to fix a performance problem.

STRICT RULES:
- You may ONLY generate one of these statement types:
  * CREATE INDEX idx_name ON table_name(column_name)
  * CREATE INDEX idx_name ON table_name(col1, col2)
  * ANALYZE
  * VACUUM
- NEVER generate: DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
- NEVER generate multiple statements
- If no safe fix exists, return exactly: NONE
- Return ONLY the SQL statement, nothing else

Database schema:
- policy_data(policy_id, state, premium_amount, status, created_date, end_date, product_id, data)
- claims_data(claim_id, policy_id, claim_amount, claim_date, status)
- config_table(id, key, value, category)
- knowledge_base(id, category, key, value)
- system_logs(log_id, created_date, event_type, policy_id, message)

Problem: {problem}
Root Cause: {root_cause}
Suggestion: {suggestion}

Return ONLY the SQL statement or NONE:
""")
    chain = prompt | llm
    raw = chain.invoke({
        "problem": problem,
        "root_cause": root_cause,
        "suggestion": suggestion
    }).content.strip()

    # Clean any accidental markdown
    raw = re.sub(r"```sql|```", "", raw).strip()

    if is_safe_sql(raw):
        return raw
    return None

# ── Check if index already exists ────────────────────────────────
def index_exists(conn, sql: str) -> bool:
    """
    Extracts index name from CREATE INDEX statement
    and checks if it already exists in the database.
    """
    match = re.search(r"CREATE INDEX\s+(\w+)\s+ON", sql, re.IGNORECASE)
    if not match:
        return False
    index_name = match.group(1)
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    ).fetchone()
    return result is not None

# ── Apply the generated fix ───────────────────────────────────────
def apply_fix(sql: str) -> dict:
    """
    Applies the LLM-generated, safety-validated SQL fix.
    Checks if fix already exists before applying.
    """
    conn = get_connection()
    try:
        # Check if already exists (for index creation)
        if sql.upper().startswith("CREATE INDEX"):
            if index_exists(conn, sql):
                return {
                    "action_taken": f"Index already exists — skipped",
                    "already_existed": True,
                    "sql_executed": sql
                }

        conn.execute(sql)
        conn.commit()
        return {
            "action_taken": f"Executed: {sql}",
            "already_existed": False,
            "sql_executed": sql
        }
    except Exception as e:
        return {
            "action_taken": f"Fix failed: {str(e)}",
            "already_existed": False,
            "sql_executed": sql
        }
    finally:
        conn.close()

# ── LLM-generated benchmark query ────────────────────────────────
def generate_benchmark_query(problem: str, suggestion: str, user_query: str) -> dict:
    """
    Asks the LLM to generate the right benchmark query
    based on the diagnosis and user's original question.
    """
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    prompt = ChatPromptTemplate.from_template("""
You are a database benchmark query generator for SQLite.
Given a performance problem, generate the exact slow query to benchmark.

STRICT RULES:
- Return ONLY a SELECT or UPDATE query
- Use ONLY these tables and columns:
  * policy_data(policy_id, state, premium_amount, status, created_date, end_date, product_id, data)
  * claims_data(claim_id, policy_id, claim_amount, claim_date, status)
  * config_table(id, key, value, category)
  * knowledge_base(id, category, key, value)
  * system_logs(log_id, created_date, event_type, policy_id, message)
- Return ONLY the SQL query, nothing else
- No markdown, no explanation

User's original question: {user_query}
Problem diagnosed: {problem}
Suggestion: {suggestion}

Return ONLY the SQL query:
""")
    chain = prompt | llm
    raw = chain.invoke({
        "user_query": user_query,
        "problem": problem,
        "suggestion": suggestion
    }).content.strip()

    raw = re.sub(r"```sql|```", "", raw).strip()

    # Safety check — benchmark queries must be SELECT or UPDATE only
    cleaned = raw.upper()
    if not (cleaned.startswith("SELECT") or cleaned.startswith("UPDATE")):
        # Fallback to safe default
        return {
            "query": "SELECT * FROM policy_data WHERE status = 'ACTIVE'",
            "description": "Default benchmark — filter by status"
        }

    return {
        "query": raw,
        "description": f"Benchmark for: {problem[:60]}"
    }

# ── Measure query execution time ──────────────────────────────────
def measure_query(query: str) -> dict:
    """
    Runs a query and returns execution time in milliseconds.
    UPDATE queries are rolled back — timing only, no data change.
    """
    conn = get_connection()
    cursor = conn.cursor()
    is_update = query.strip().upper().startswith("UPDATE")

    try:
        start = time.perf_counter()

        if is_update:
            cursor.execute(query)
            row_count = cursor.rowcount
            conn.rollback()
        else:
            cursor.execute(query)
            rows = cursor.fetchall()
            row_count = len(rows)

        end = time.perf_counter()
        elapsed_ms = round((end - start) * 1000, 2)

        return {
            "execution_ms": elapsed_ms,
            "rows_affected": row_count
        }
    except Exception as e:
        return {
            "execution_ms": -1,
            "rows_affected": 0,
            "error": str(e)
        }
    finally:
        conn.close()

# ── Calculate improvement ─────────────────────────────────────────
def calculate_improvement(before_ms: float, after_ms: float) -> str:
    if before_ms <= 0 or after_ms <= 0:
        return "unknown"
    if after_ms >= before_ms:
        return "no improvement detected"
    improvement = ((before_ms - after_ms) / before_ms) * 100
    return f"{round(improvement, 1)}% faster"

# ── Main agentic function ─────────────────────────────────────────
def analyze_and_fix(problem: str, root_cause: str, suggestion: str, user_query: str = "") -> dict:
    """
    The full agentic loop:
    1. LLM generates the right benchmark query
    2. Measure before
    3. LLM generates the fix SQL
    4. Safety validator approves it
    5. Fix applied to real database
    6. Measure after
    7. Return proof
    """

    # Step 1 — LLM generates benchmark query
    print(f"\n🤖 Generating benchmark query...")
    pattern = generate_benchmark_query(problem, suggestion, user_query)
    query = pattern["query"]
    print(f"   Query: {query[:80]}")

    # Step 2 — measure before
    print("   Measuring BEFORE fix...")
    before = measure_query(query)
    print(f"   Before: {before['execution_ms']}ms ({before['rows_affected']} rows)")

    # Step 3 — LLM generates fix SQL
    print("   Generating fix SQL...")
    fix_sql = generate_fix_sql(problem, suggestion, root_cause)

    if not fix_sql:
        print("   No safe fix generated.")
        return {
            "query_benchmarked": query,
            "before_ms": before["execution_ms"],
            "after_ms": before["execution_ms"],
            "rows_affected": before["rows_affected"],
            "improvement": "no safe fix available",
            "action_taken": "LLM could not generate a safe fix for this pattern",
            "sql_executed": None,
            "fix_already_existed": False
        }

    print(f"   Fix SQL: {fix_sql}")

    # Step 4 — apply fix
    print("   Applying fix...")
    fix_result = apply_fix(fix_sql)
    print(f"   Result: {fix_result['action_taken']}")

    # Step 5 — measure after
    print("   Measuring AFTER fix...")
    after = measure_query(query)
    print(f"   After: {after['execution_ms']}ms ({after['rows_affected']} rows)")

    # Step 6 — calculate improvement
    improvement = calculate_improvement(before["execution_ms"], after["execution_ms"])
    print(f"   Improvement: {improvement}")

    return {
        "query_benchmarked": query,
        "before_ms": before["execution_ms"],
        "after_ms": after["execution_ms"],
        "rows_affected": before["rows_affected"],
        "improvement": improvement,
        "action_taken": fix_result["action_taken"],
        "sql_executed": fix_result["sql_executed"],
        "fix_already_existed": fix_result["already_existed"]
    }