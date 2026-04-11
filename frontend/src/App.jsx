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
        🧠 AI REASONING CHAIN
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
                 step.includes("skipped") ? "#fbbf24" :
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

function AgentCard({ title, subtitle, color, children }) {
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
      <div style={{ marginBottom: "4px" }}>
        <span style={{
          color,
          fontSize: "11px",
          letterSpacing: "2px",
          fontFamily: "'Courier New', monospace",
          fontWeight: "700"
        }}>
          {title}
        </span>
      </div>
      <div style={{
        color: "#111827",
        fontSize: "17px",
        fontWeight: "700",
        marginBottom: "16px",
        letterSpacing: "-0.3px"
      }}>
        {subtitle}
      </div>
      <div style={{ borderTop: `1px solid ${color}22`, paddingTop: "16px" }}>
        {children}
      </div>
    </div>
  );
}

function Field({ label, value, highlight }) {
  if (!value) return null;
  return (
    <div style={{ marginBottom: "14px" }}>
      <div style={{
        color: "#6b7280",
        fontSize: "10px",
        letterSpacing: "1px",
        fontFamily: "'Courier New', monospace",
        marginBottom: "4px",
        fontWeight: "700",
        textTransform: "uppercase"
      }}>
        {label}
      </div>
      <div style={{
        color: highlight || "#1f2937",
        fontSize: "14px",
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
        fontSize: "12px",
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
      padding: "4px 12px",
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
  const [dynamicSuggestions, setDynamicSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  const animateChain = (steps) => {
    setVisibleSteps([]);
    steps.forEach((step, i) => {
      setTimeout(() => {
        setVisibleSteps(prev => [...prev, step]);
      }, i * 200);
    });
  };

  const fetchDynamicSuggestions = async (userQuestion) => {
    setLoadingSuggestions(true);
    try {
      const res = await fetch(`${API_BASE}/suggest/similar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userQuestion })
      });
      const data = await res.json();
      setDynamicSuggestions(data.suggestions || []);
    } catch {
      setDynamicSuggestions([
        "Why is SELECT * FROM policy_data WHERE status = 'ACTIVE' slow?",
        "My JSON query using JSON_EXTRACT is taking 25 seconds",
        "Query suddenly spiked from 1s to 50s with no code changes",
        "SELECT * FROM large_table with no WHERE clause is very slow"
      ]);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setVisibleSteps([]);
    setDynamicSuggestions([]);
    try {
      const res = await fetch(`${API_BASE}/analyze/full`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, mode })
      });
      const data = await res.json();
      setResult(data);
      if (data.reasoning_chain) animateChain(data.reasoning_chain);

      // Fetch dynamic suggestions if out of scope or uncertain
      if (data.status === "out_of_scope" || data.is_uncertain) {
        fetchDynamicSuggestions(question);
      }
    } catch (e) {
      setError("Failed to connect to API. Make sure the backend server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const isUncertain = result?.is_uncertain;

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

        {/* Connection Error */}
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

        {/* Not DB related */}
        {result?.error && !result?.status && (
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
            <div style={{ color: "#374151", fontSize: "14px", marginBottom: "4px" }}>{result.error}</div>
            <div style={{ color: "#6b7280", fontSize: "13px" }}>{result.suggestion}</div>
          </div>
        )}

        {/* Out of scope — needs more details */}
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
              Your question is too general. {loadingSuggestions ? "Finding similar examples..." : "Try one of these:"}
            </div>
            {loadingSuggestions ? (
              <div style={{ color: "#d97706", fontFamily: "'Courier New', monospace", fontSize: "13px" }}>
                ⏳ Generating personalized suggestions...
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {dynamicSuggestions.map((s, i) => (
                  <div
                    key={i}
                    onClick={() => setQuestion(s)}
                    style={{
                      background: "#ffffff",
                      border: "1px solid #fcd34d",
                      borderRadius: "6px",
                      padding: "10px 14px",
                      fontSize: "13px",
                      color: "#374151",
                      cursor: "pointer",
                      fontFamily: "'Courier New', monospace",
                      transition: "background 0.2s"
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = "#fef9c3"}
                    onMouseLeave={e => e.currentTarget.style.background = "#ffffff"}
                  >
                    → {s}
                  </div>
                ))}
              </div>
            )}
            <div style={{ color: "#9ca3af", fontSize: "11px", marginTop: "12px" }}>
              Click any suggestion to use it
            </div>
          </div>
        )}

        {/* Success Results */}
        {result?.status === "success" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

            {/* Low confidence warning */}
            {isUncertain && (
              <div style={{
                background: "#fffbeb",
                border: "1px solid #fcd34d",
                borderRadius: "8px",
                padding: "16px 20px",
                display: "flex",
                flexDirection: "column",
                gap: "12px"
              }}>
                <div style={{ color: "#d97706", fontFamily: "'Courier New', monospace", fontSize: "11px", letterSpacing: "2px", fontWeight: "700" }}>
                  ⚠️ LOW CONFIDENCE MATCH
                </div>
                <div style={{ color: "#374151", fontSize: "14px" }}>
                  I found a possible match but I'm not confident enough to execute fixes safely.
                  The diagnosis below is my best guess — please verify before acting on it.
                </div>
                {loadingSuggestions ? (
                  <div style={{ color: "#d97706", fontFamily: "'Courier New', monospace", fontSize: "13px" }}>
                    ⏳ Generating personalized suggestions...
                  </div>
                ) : dynamicSuggestions.length > 0 && (
                  <div>
                    <div style={{ color: "#6b7280", fontSize: "12px", marginBottom: "8px", fontFamily: "'Courier New', monospace" }}>
                      DID YOU MEAN ONE OF THESE?
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {dynamicSuggestions.map((s, i) => (
                        <div
                          key={i}
                          onClick={() => setQuestion(s)}
                          style={{
                            background: "#ffffff",
                            border: "1px solid #fcd34d",
                            borderRadius: "6px",
                            padding: "8px 14px",
                            fontSize: "13px",
                            color: "#374151",
                            cursor: "pointer",
                            fontFamily: "'Courier New', monospace",
                            transition: "background 0.2s"
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = "#fef9c3"}
                          onMouseLeave={e => e.currentTarget.style.background = "#ffffff"}
                        >
                          → {s}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Three Agent Cards — FIRST */}
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>

              {/* DiagnosisAgent — What's Wrong? */}
              <AgentCard title="DIAGNOSISAGENT" subtitle="🔬 What's Wrong?" color="#3b82f6">
                <Field label="Problem" value={result.diagnosis?.problem} highlight="#1d4ed8" />
                <Field label="Root Cause" value={result.diagnosis?.root_cause} />
                <Field label="Pattern Matched" value={result.diagnosis?.pattern_matched} />
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "700" }}>
                    CONFIDENCE
                  </div>
                  <ConfidenceDots level={result.diagnosis?.confidence} />
                </div>
                <Field label="Similarity Score" value={result.diagnosis?.similarity_score?.toFixed(4)} />
                <div style={{ marginTop: "14px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "8px", fontWeight: "700" }}>
                    MATCHED CASES
                  </div>
                  {result.diagnosis?.matched_cases?.map((c, i) => (
                    <div key={i} style={{
                      color: "#3b82f6",
                      fontSize: "13px",
                      fontFamily: "'Courier New', monospace",
                      marginBottom: "4px",
                      fontWeight: "500"
                    }}>
                      [{i + 1}] {c}
                    </div>
                  ))}
                </div>
              </AgentCard>

              {/* FixAgent — How to Fix? */}
              <AgentCard
                title="FIXAGENT"
                subtitle={isUncertain ? "🔧 Fix Skipped" : "🔧 How to Fix?"}
                color={isUncertain ? "#d97706" : "#16a34a"}
              >
                {isUncertain ? (
                  <div style={{
                    background: "#fffbeb",
                    border: "1px solid #fcd34d",
                    borderRadius: "8px",
                    padding: "16px",
                    color: "#92400e",
                    fontSize: "14px",
                    lineHeight: "1.6"
                  }}>
                    ⚠️ Fix execution was skipped because the RAG confidence is too low.
                    Executing an uncertain fix could make things worse.
                    Please provide a more specific query to enable safe fix execution.
                  </div>
                ) : (
                  <>
                    <div style={{ marginBottom: "14px" }}>
                      <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px", fontWeight: "700" }}>
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
                    <div style={{ display: "flex", gap: "8px", marginBottom: "14px", flexWrap: "wrap" }}>
                      {result.fix?.safe && <StatusBadge text="✓ SAFE" color="#16a34a" />}
                      {result.fix?.validated_by && <StatusBadge text="✓ VALIDATED" color="#16a34a" />}
                      {result.fix?.already_existed && <StatusBadge text="ALREADY APPLIED" color="#d97706" />}
                    </div>
                    <Field label="Action Taken" value={result.fix?.action_taken} />
                    <Field label="Query Benchmarked" value={result.fix?.query_benchmarked} />
                    <div style={{ display: "flex", gap: "24px", marginTop: "16px" }}>
                      {result.fix?.before_ms && (
                        <div>
                          <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px", fontWeight: "700" }}>BEFORE</div>
                          <div style={{ color: "#dc2626", fontSize: "22px", fontWeight: "800", fontFamily: "'Courier New', monospace" }}>
                            {result.fix.before_ms}ms
                          </div>
                        </div>
                      )}
                      {result.fix?.after_ms && (
                        <>
                          <div style={{ color: "#9ca3af", fontSize: "22px", alignSelf: "flex-end", marginBottom: "2px" }}>→</div>
                          <div>
                            <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px", fontWeight: "700" }}>AFTER</div>
                            <div style={{ color: "#16a34a", fontSize: "22px", fontWeight: "800", fontFamily: "'Courier New', monospace" }}>
                              {result.fix.after_ms}ms
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                    {result.fix?.improvement && (
                      <div style={{
                        marginTop: "12px",
                        color: "#16a34a",
                        fontSize: "14px",
                        fontFamily: "'Courier New', monospace",
                        fontWeight: "700"
                      }}>
                        ↑ {result.fix.improvement}
                      </div>
                    )}
                  </>
                )}
              </AgentCard>

              {/* ImpactAgent — What's the Impact? */}
              <AgentCard title="IMPACTAGENT" subtitle="📊 What's the Impact?" color="#dc2626">
                                {isUncertain && (
                  <div style={{
                    background: "#fffbeb",
                    border: "1px solid #fcd34d",
                    borderRadius: "6px",
                    padding: "10px 12px",
                    marginBottom: "14px",
                    color: "#92400e",
                    fontSize: "12px",
                    fontFamily: "'Courier New', monospace"
                  }}>
                    ⚠️ Impact estimated from closest match — may not be accurate. Verify with a more specific query.
                  </div>
                )}
<Field label="Technical Impact" value={result.impact?.technical} highlight={mode === "technical" ? "#1d4ed8" : null} />
<Field label="User Impact" value={result.impact?.user_facing} highlight={mode === "simple" ? "#16a34a" : null} />
<Field label="Business Impact" value={result.impact?.executive} highlight={mode === "executive" ? "#dc2626" : null} /><Field label="Daily Cost" value={result.impact?.estimated_daily_cost} highlight="#d97706" />
                <Field label="Trajectory" value={result.impact?.trajectory} highlight="#dc2626" />
                <div style={{ marginBottom: "14px" }}>
                  <div style={{ color: "#6b7280", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "8px", fontWeight: "700" }}>
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
                <Field label="Fix ROI" value={result.impact?.fix_roi} highlight="#16a34a" />
              </AgentCard>
            </div>
{/* Mode Summary */}
<div style={{
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "12px 16px",
  background: "#f0fdf4",
  border: "1px solid #86efac",
  borderRadius: "8px",
  fontSize: "14px",
  color: "#111827",
  fontWeight: "500"
}}>
  <span style={{ fontSize: "18px" }}>
    {mode === "technical" ? "⚙️" : mode === "simple" ? "👤" : "💼"}
  </span>
  <div>
    <span style={{ color: "#16a34a", fontFamily: "'Courier New', monospace", fontSize: "11px", fontWeight: "700", letterSpacing: "1px" }}>
      {mode.toUpperCase()} MODE — AUDIENCE SUMMARY
    </span>
    <div style={{ marginTop: "2px" }}>{result.audience_summary}</div>
  </div>
</div>

{/* Reasoning Chain — AFTER cards */}
            {/* Reasoning Chain — AFTER cards */}
            {visibleSteps.length > 0 && <ReasoningChain steps={visibleSteps} />}

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