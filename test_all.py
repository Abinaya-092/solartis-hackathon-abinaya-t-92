import requests
import json

BASE = "http://localhost:8000"

tests = [
    # Category 1 - Happy path
    {"name": "C1-1 Status query", "endpoint": "/analyze/full", "body": {"question": "SELECT * FROM policy_data WHERE status = 'ACTIVE' is slow", "mode": "technical"}},
    {"name": "C1-2 JSON query", "endpoint": "/analyze/full", "body": {"question": "my JSON query using JSON_EXTRACT is taking 25 seconds", "mode": "technical"}},
    {"name": "C1-3 Policy search simple", "endpoint": "/analyze/full", "body": {"question": "policy search is very slow today", "mode": "simple"}},
    {"name": "C1-4 Policy search executive", "endpoint": "/analyze/full", "body": {"question": "policy search is very slow today", "mode": "executive"}},

    # Category 2 - Anomaly
    {"name": "C2-1 Spike anomaly", "endpoint": "/analyze/full", "body": {"question": "my query suddenly spiked from 1 second to 50 seconds with no code changes", "mode": "technical"}},
    {"name": "C2-2 Slow today", "endpoint": "/analyze/full", "body": {"question": "database was fine yesterday but extremely slow today", "mode": "technical"}},

    # Category 3 - Edge cases
    {"name": "C3-1 Stored procedure", "endpoint": "/analyze/full", "body": {"question": "stored procedure execution is slow", "mode": "technical"}},
    {"name": "C3-2 Connection timeout", "endpoint": "/analyze/full", "body": {"question": "my database connection keeps timing out", "mode": "technical"}},
    {"name": "C3-3 Reporting executive", "endpoint": "/analyze/full", "body": {"question": "how do I optimize my insurance reporting queries", "mode": "executive"}},

    # Category 4 - Out of scope
    {"name": "C4-1 Pasta", "endpoint": "/ask", "body": {"question": "how do I make pasta"}},
    {"name": "C4-2 ML question", "endpoint": "/ask", "body": {"question": "what is machine learning"}},
    {"name": "C4-3 Hello", "endpoint": "/ask", "body": {"question": "hello"}},
]

DIVIDER = "=" * 70
SECTION = "-" * 70

def print_section(title, value, color=None):
    if value:
        print(f"  {title}:")
        if isinstance(value, list):
            for item in value:
                print(f"    → {item}")
        else:
            # Word wrap long values
            words = str(value).split()
            line = "    "
            for word in words:
                if len(line) + len(word) > 68:
                    print(line)
                    line = "    " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(line)

print(DIVIDER)
print("  SOLARTIS AI SYSTEM — FULL DETAILED TEST SUITE")
print(DIVIDER)

passed = 0
failed = 0
warnings = 0

for test in tests:
    print(f"\n{'█' * 70}")
    print(f"  TEST: {test['name']}")
    print(f"  ENDPOINT: {test['endpoint']}")
    print(f"  INPUT: {test['body']}")
    print(f"{'█' * 70}")

    try:
        res = requests.post(
            f"{BASE}{test['endpoint']}",
            json=test["body"],
            timeout=60
        )
        data = res.json()

        # ── Determine overall result ──────────────────────────────
        is_out_of_scope_test = any(x in test["name"] for x in ["Pasta", "ML question", "Hello"])
        status = data.get("status", "")
        error = data.get("error", "")
        warning = data.get("warning", "")

        if is_out_of_scope_test:
            if error or warning or status == "out_of_scope":
                overall = "✅ PASS — rejected correctly"
                passed += 1
            else:
                overall = "❌ FAIL — should have been rejected"
                failed += 1
        elif status == "success":
            overall = "✅ PASS"
            passed += 1
        elif warning:
            overall = "⚠️  WARN — uncertain match"
            warnings += 1
        elif error:
            overall = f"❌ FAIL — {error}"
            failed += 1
        else:
            overall = "✅ PASS"
            passed += 1

        print(f"\n  OVERALL: {overall}")
        print(SECTION)

        # ── Reasoning Chain ───────────────────────────────────────
        chain = data.get("reasoning_chain", [])
        if chain:
            print(f"\n  REASONING CHAIN ({len(chain)} steps):")
            for step in chain:
                print(f"    > {step}")

        # ── Diagnosis ─────────────────────────────────────────────
        diagnosis = data.get("diagnosis", {})
        if diagnosis:
            print(f"\n  🔬 DIAGNOSISAGENT:")
            print_section("Problem", diagnosis.get("problem"))
            print_section("Root Cause", diagnosis.get("root_cause"))
            print_section("Pattern Matched", diagnosis.get("pattern_matched"))
            print_section("Confidence", diagnosis.get("confidence"))
            print_section("Similarity Score", diagnosis.get("similarity_score"))
            print_section("Matched Cases", diagnosis.get("matched_cases"))

        # ── Fix ───────────────────────────────────────────────────
        fix = data.get("fix", {})
        if fix:
            print(f"\n  🔧 FIXAGENT:")
            print_section("SQL Executed", fix.get("sql_executed"))
            print_section("Safe", fix.get("safe"))
            print_section("Action Taken", fix.get("action_taken"))
            print_section("Query Benchmarked", fix.get("query_benchmarked"))
            print_section("Before MS", fix.get("before_ms"))
            print_section("After MS", fix.get("after_ms"))
            print_section("Improvement", fix.get("improvement"))
            print_section("Already Existed", fix.get("already_existed"))

        # ── Impact ────────────────────────────────────────────────
        impact = data.get("impact", {})
        if impact:
            print(f"\n  📊 IMPACTAGENT:")
            print_section("Technical", impact.get("technical"))
            print_section("User Facing", impact.get("user_facing"))
            print_section("Executive", impact.get("executive"))
            print_section("Daily Cost", impact.get("estimated_daily_cost"))
            print_section("Trajectory", impact.get("trajectory"))
            print_section("Urgency", impact.get("urgency"))
            print_section("Fix ROI", impact.get("fix_roi"))

        # ── Audience Summary ──────────────────────────────────────
        summary = data.get("audience_summary")
        if summary:
            print(f"\n  💬 AUDIENCE SUMMARY:")
            print_section("Summary", summary)

        # ── Out of scope / errors ─────────────────────────────────
        if error:
            print(f"\n  ⚠️  ERROR: {error}")
        if warning:
            print(f"\n  ⚠️  WARNING: {warning}")
        if data.get("similarity_score"):
            print(f"\n  📏 SIMILARITY SCORE: {data.get('similarity_score')}")
        if data.get("closest_match"):
            print(f"  📎 CLOSEST MATCH: {data.get('closest_match')}")

    except requests.exceptions.ConnectionError:
        print(f"\n  ❌ CONNECTION ERROR — Is the backend running on port 8000?")
        failed += 1
    except Exception as e:
        print(f"\n  ❌ ERROR — {str(e)}")
        failed += 1

print(f"\n{DIVIDER}")
print(f"  FINAL RESULTS: {passed} passed · {warnings} warnings · {failed} failed")
print(f"  TOTAL TESTS: {len(tests)}")
print(DIVIDER)