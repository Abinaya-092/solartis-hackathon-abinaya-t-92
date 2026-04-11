import { useState } from "react";

const API_BASE = "http://localhost:8000";
const MODES = ["technical", "simple", "executive"];
const MODE_LABELS = {
  technical: "⚙️ Technical",
  simple: "👤 Simple",
  executive: "💼 Executive",
};
const CONFIDENCE_COLORS = {
  high: "#16a34a",
  medium: "#d97706",
  low: "#dc2626",
};

function ReasoningChain({ steps }) {
  return (
    <div style={{
      background: "#1a1a2e",
      border: "1px solid #2d2d4e",
      borderRadius: "8px",
      padding: "16px",
      fontFamily: "'Courier New', monospace",
      fontSize: "13px",
    }}>
      <div style={{ color: "#6b7280", marginBottom: "12px", fontSize: "11px", letterSpacing: "2px" }}>
        REASONING CHAIN
      </div>
      {steps.map((step, i) => (
        <div key={i} style={{
          display: "flex",
          gap: "8px",
          marginBottom: "6px",
          animation: `fadeIn 0.3s ease ${i * 0.1}s both`,
          color: step.includes("failed") ? "#f87171" :
                 step.includes("CONFIDENT") ? "#4ade80" :
                 step.includes("UNCERTAIN") ? "#fbbf24" :
                 step.includes("Delegating") ? "#60a5fa" :
                 step.includes("returned") || step.includes("generated") ? "#4ade80" :
                 "#d1d5db"
        }}>
          <span style={{ color: "#4b5563" }}>{">"}</span>
          <span>{step}</span>
        </div>
      ))}
    </div>
  );
}

function AgentCard({ title, icon, color, children }) {
  return (
    <div style={{
      background: "#ffffff",
      border: `1px solid ${color}33`,
      borderTop: `3px solid ${color}`,
      borderRadius: "8px",
      padding: "20px",
      flex: 1,
      minWidth: "280px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
    }}>
      <div style={{
        color,
        fontSize: "12px",
        letterSpacing: "2px",
        marginBottom: "16px",
        fontFamily: "'Courier New', monospace",
        fontWeight: "700"
      }}>
        {icon} {title}
      </div>
      {children}
    </div>
  );
}

function Field({ label, value, highlight }) {
  if (!value) return null;
  return (
    <div style={{ marginBottom: "12px" }}>
      <div style={{
        color: "#6b7280",
        fontSize: "10px",
        letterSpacing: "1px",
        fontFamily: "'Courier New', monospace",
        marginBottom: "4px",
        fontWeight: "600"
      }}>
        {label}
      </div>
      <div style={{
        color: highlight || "#111827",
        fontSize: "13px",
        lineHeight: "1.6",
        fontWeight: highlight ? "600" : "400"
      }}>
        {value}
      </div>
    </div>
  );
}

function ConfidenceDots({ level }) {
  const color = CONFIDENCE_COLORS[level] || "#6b7280";
  const filled = level === "high" ? 3 : level === "medium" ? 2 : 1;
  return (
    <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: "10px",
          height: "10px",
          borderRadius: "50%",
          background: i < filled ? color : "#e5e7eb",
          border: `1px solid ${i < filled ? color : "#d1d5db"}`
        }} />
      ))}
      <span style={{
        color,
        fontSize: "11px",
        marginLeft: "6px",
        fontFamily: "'Courier New', monospace",
        fontWeight: "700"
      }}>
        {level?.toUpperCase()}
      </span>
    </div>
  );
}

function StatusBadge({ text, color }) {
  return (
    <span style={{
      background: `${color}18`,
      border: `1px solid ${color}`,
      color,
      padding: "3px 10px",
      borderRadius: "4px",
      fontSize: "11px",
      fontFamily: "'Courier New', monospace",
      fontWeight: "700"
    }}>
      {text}
    </span>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("technical");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [visibleSteps, setVisibleSteps] = useState([]);

  const animateChain = (steps) => {
    setVisibleSteps([]);
    steps.forEach((step, i) => {
      setTimeout(() => {
        setVisibleSteps(prev => [...prev, step]);
      }, i * 200);
    });
  };

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setVisibleSteps([]);
    try {
      const res = await fetch(`${API_BASE}/analyze/full`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, mode })
      });
      const data = await res.json();
      setResult(data);
      if (data.reasoning_chain) animateChain(data.reasoning_chain);
    } catch (e) {
      setError("Failed to connect to API. Make sure the backend server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f9fafb",
      color: "#111827",
      fontFamily: "'Segoe UI', sans-serif",
      padding: "40px 24px",
    }}>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateX(-8px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        * { box-sizing: border-box; }
        textarea:focus { outline: 2px solid #16a34a; outline-offset: 2px; }
        button { cursor: pointer; }
        button:disabled { cursor: not-allowed; }
      `}</style>

      <div style={{ maxWidth: "1100px", margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: "40px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
            <div style={{
              width: "8px", height: "8px", borderRadius: "50%",
              background: "#16a34a",
              animation: "pulse 2s infinite"
            }} />
            <span style={{
              color: "#16a34a",
              fontSize: "11px",
              letterSpacing: "3px",
              fontFamily: "'Courier New', monospace",
              fontWeight: "700"
            }}>
              AI DATABASE ENGINEER — LIVE
            </span>
          </div>
          <h1 style={{
            fontSize: "36px",
            fontWeight: "800",
            margin: "0 0 8px 0",
            color: "#111827",
            letterSpacing: "-0.5px"
          }}>
            SQL Performance Analyzer
          </h1>
          <p style={{ color: "#4b5563", fontSize: "15px", margin: 0 }}>
            Multi-agent RAG system · DiagnosisAgent · FixAgent · ImpactAgent
          </p>
        </div>

        {/* Input Card */}
        <div style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: "12px",
          padding: "24px",
          marginBottom: "24px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.08)"
        }}>
          {/* Mode Selector */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            {MODES.map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  padding: "8px 18px",
                  borderRadius: "6px",
                  border: mode === m ? "2px solid #16a34a" : "1px solid #d1d5db",
                  background: mode === m ? "#f0fdf4" : "#ffffff",
                  color: mode === m ? "#16a34a" : "#374151",
                  fontSize: "13px",
                  fontFamily: "'Courier New', monospace",
                  letterSpacing: "0.5px",
                  fontWeight: mode === m ? "700" : "400",
                  transition: "all 0.2s"
                }}
              >
                {MODE_LABELS[m]}
              </button>
            ))}
          </div>

          {/* Textarea */}
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSubmit()}
            placeholder={"Describe your database performance issue...\ne.g. 'SELECT * FROM policy_data WHERE status = ACTIVE is taking too long'"}
            style={{
              width: "100%",
              background: "#f9fafb",
              border: "1px solid #d1d5db",
              borderRadius: "8px",
              color: "#111827",
              padding: "14px",
              fontSize: "14px",
              resize: "vertical",
              minHeight: "100px",
              fontFamily: "'Segoe UI', sans-serif",
              lineHeight: "1.6"
            }}
          />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
            <span style={{ color: "#6b7280", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
              Press Enter to analyze · Shift+Enter for new line
            </span>
            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              style={{
                background: loading || !question.trim() ? "#e5e7eb" : "#16a34a",
                color: loading || !question.trim() ? "#9ca3af" : "#ffffff",
                border: "none",
                borderRadius: "8px",
                padding: "10px 28px",
                fontSize: "13px",
                fontWeight: "700",
                letterSpacing: "1px",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                gap: "8px"
              }}
            >
              {loading ? (
                <>
                  <div style={{
                    width: "12px", height: "12px",
                    border: "2px solid #d1d5db",
                    borderTop: "2px solid #16a34a",
                    borderRadius: "50%",
                    animation: "spin 0.8s linear infinite"
                  }} />
                  ANALYZING...
                </>
              ) : "ANALYZE →"}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "#fef2f2",
            border: "1px solid #fca5a5",
            borderRadius: "8px",
            padding: "16px",
            color: "#dc2626",
            marginBottom: "24px",
            fontSize: "14px",
            fontWeight: "500"
          }}>
            ⚠️ {error}
          </div>
        )}
        {/* Domain validation rejection */}
{result?.error && result?.status !== "out_of_scope" && (
  <div style={{
    background: "#fef2f2",
    border: "1px solid #fca5a5",
    borderRadius: "8px",
    padding: "20px",
    marginBottom: "24px"
  }}>
    <div style={{ color: "#dc2626", marginBottom: "8px", fontFamily: "'Courier New', monospace", fontSize: "11px", letterSpacing: "2px", fontWeight: "700" }}>
      ❌ NOT DATABASE RELATED
    </div>
    <div style={{ color: "#374151", fontSize: "14px" }}>{result.error}</div>
    <div style={{ color: "#6b7280", fontSize: "12px", marginTop: "8px" }}>
      {result.suggestion}
    </div>
  </div>
)}
        {result?.status === "out_of_scope" && (
  <div style={{
    background: "#fffbeb",
    border: "1px solid #fcd34d",
    borderRadius: "8px",
    padding: "20px",
    marginBottom: "24px"
  }}>
    <div style={{ color: "#d97706", marginBottom: "8px", fontFamily: "'Courier New', monospace", fontSize: "11px", letterSpacing: "2px", fontWeight: "700" }}>
      🔍 NEED MORE DETAILS
    </div>
    <div style={{ color: "#374151", fontSize: "14px", marginBottom: "16px" }}>
      Your question is too general for me to find a specific match. Try being more specific:
    </div>
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {[
        "Why is SELECT * FROM policy_data WHERE status = 'ACTIVE' slow?",
        "My JSON query using JSON_EXTRACT is taking 25 seconds",
        "Query suddenly spiked from 1s to 50s with no code changes",
        "SELECT * FROM large_table with no WHERE clause is very slow"
      ].map((suggestion, i) => (
        <div
          key={i}
          onClick={() => setQuestion(suggestion)}
          style={{
            background: "#ffffff",
            border: "1px solid #fcd34d",
            borderRadius: "6px",
            padding: "10px 14px",
            fontSize: "13px",
            color: "#374151",
            cursor: "pointer",
            fontFamily: "'Courier New', monospace",
            transition: "all 0.2s"
          }}
          onMouseEnter={e => e.target.style.background = "#fef9c3"}
          onMouseLeave={e => e.target.style.background = "#ffffff"}
        >
          → {suggestion}
        </div>
      ))}
    </div>
    <div style={{ color: "#9ca3af", fontSize: "11px", marginTop: "12px" }}>
      Click any suggestion to use it as your query
    </div>
  </div>
)}

        {/* Results */}
        {result?.status === "success" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

            {/* Summary Banner */}
            <div style={{
              background: "#f0fdf4",
              border: "1px solid #86efac",
              borderRadius: "8px",
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              gap: "14px"
            }}>
              <div style={{ fontSize: "24px" }}>
                {mode === "technical" ? "⚙️" : mode === "simple" ? "👤" : "💼"}
              </div>
              <div>
                <div style={{ color: "#16a34a", fontSize: "10px", letterSpacing: "2px", fontFamily: "'Courier New', monospace", marginBottom: "4px", fontWeight: "700" }}>
                  {mode.toUpperCase()} SUMMARY
                </div>
                <div style={{ color: "#111827", fontSize: "15px", lineHeight: "1.5", fontWeight: "500" }}>
                  {result.audience_summary}
                </div>
              </div>
            </div>

            {/* Reasoning Chain */}
            {visibleSteps.length > 0 && <ReasoningChain steps={visibleSteps} />}

            {/* Three Agent Cards */}
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>

              {/* DiagnosisAgent */}
              <AgentCard title="DIAGNOSISAGENT" icon="🔬" color="#3b82f6">
                <Field label="PROBLEM" value={result.diagnosis?.problem} highlight="#1d4ed8" />
                <Field label="ROOT CAUSE" value={result.diagnosis?.root_cause} />
                <Field label="PATTERN MATCHED" value={result.diagnosis?.pattern_matched} />
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "600" }}>
                    CONFIDENCE
                  </div>
                  <ConfidenceDots level={result.diagnosis?.confidence} />
                </div>
                <Field label="SIMILARITY SCORE" value={result.diagnosis?.similarity_score?.toFixed(4)} />
                <div style={{ marginTop: "12px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "600" }}>
                    MATCHED CASES
                  </div>
                  {result.diagnosis?.matched_cases?.map((c, i) => (
                    <div key={i} style={{
                      color: "#3b82f6",
                      fontSize: "12px",
                      fontFamily: "'Courier New', monospace",
                      marginBottom: "4px",
                      fontWeight: "500"
                    }}>
                      [{i + 1}] {c}
                    </div>
                  ))}
                </div>
              </AgentCard>

              {/* FixAgent */}
              <AgentCard title="FIXAGENT" icon="🔧" color="#16a34a">
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "600" }}>
                    SQL EXECUTED
                  </div>
                  <div style={{
                    background: "#1a1a2e",
                    borderRadius: "6px",
                    padding: "12px",
                    fontFamily: "'Courier New', monospace",
                    fontSize: "12px",
                    color: "#4ade80",
                    fontWeight: "600"
                  }}>
                    {result.fix?.sql_executed || "No fix generated"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
                  {result.fix?.safe && <StatusBadge text="✓ SAFE" color="#16a34a" />}
                  {result.fix?.validated_by && <StatusBadge text="✓ VALIDATED" color="#16a34a" />}
                  {result.fix?.already_existed && <StatusBadge text="ALREADY APPLIED" color="#d97706" />}
                </div>
                <Field label="ACTION TAKEN" value={result.fix?.action_taken} />
                <Field label="QUERY BENCHMARKED" value={result.fix?.query_benchmarked} />
                <div style={{ display: "flex", gap: "24px", marginTop: "16px" }}>
                  <div>
                    <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px", fontWeight: "600" }}>BEFORE</div>
                    <div style={{ color: "#dc2626", fontSize: "22px", fontWeight: "800", fontFamily: "'Courier New', monospace" }}>
                      {result.fix?.before_ms}ms
                    </div>
                  </div>
                  {result.fix?.after_ms && (
                    <>
                      <div style={{ color: "#9ca3af", fontSize: "22px", alignSelf: "flex-end", marginBottom: "2px" }}>→</div>
                      <div>
                        <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px", fontWeight: "600" }}>AFTER</div>
                        <div style={{ color: "#16a34a", fontSize: "22px", fontWeight: "800", fontFamily: "'Courier New', monospace" }}>
                          {result.fix?.after_ms}ms
                        </div>
                      </div>
                    </>
                  )}
                </div>
                {result.fix?.improvement && (
                  <div style={{
                    marginTop: "12px",
                    color: "#16a34a",
                    fontSize: "13px",
                    fontFamily: "'Courier New', monospace",
                    fontWeight: "700"
                  }}>
                    ↑ {result.fix.improvement}
                  </div>
                )}
              </AgentCard>

              {/* ImpactAgent */}
              <AgentCard title="IMPACTAGENT" icon="📊" color="#dc2626">
                <Field label="TECHNICAL" value={result.impact?.technical} />
                <Field label="USER FACING" value={result.impact?.user_facing} />
                <Field label="EXECUTIVE" value={result.impact?.executive} />
                <Field label="DAILY COST" value={result.impact?.estimated_daily_cost} highlight="#d97706" />
                <Field label="TRAJECTORY" value={result.impact?.trajectory} highlight="#dc2626" />
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "600" }}>
                    URGENCY
                  </div>
                  <StatusBadge
                    text={result.impact?.urgency?.toUpperCase() || "UNKNOWN"}
                    color={
                      result.impact?.urgency?.toLowerCase().includes("high") ? "#dc2626" :
                      result.impact?.urgency?.toLowerCase().includes("medium") ? "#d97706" : "#16a34a"
                    }
                  />
                </div>
                <Field label="FIX ROI" value={result.impact?.fix_roi} highlight="#16a34a" />
              </AgentCard>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{
          marginTop: "60px",
          paddingTop: "24px",
          borderTop: "1px solid #e5e7eb",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <div style={{ color: "#6b7280", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
            RAG · ChromaDB · LLaMA 3.1 · FastAPI · Multi-Agent Architecture
          </div>
          <div style={{ color: "#6b7280", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
            Built by Abinaya T · 2026
          </div>
        </div>
      </div>
    </div>
  );
}