import { useState } from "react";

const API_BASE = "http://localhost:8000";

const MODES = ["technical", "simple", "executive"];

const MODE_LABELS = {
  technical: "⚙️ Technical",
  simple: "👤 Simple",
  executive: "💼 Executive",
};

const CONFIDENCE_COLORS = {
  high: "#00ff9d",
  medium: "#ffcc00",
  low: "#ff4444",
};

function ReasoningChain({ steps }) {
  return (
    <div style={{
      background: "#f0f0f0",
      border: "1px solid #e0e0e0",
      borderRadius: "8px",
      padding: "16px",
      fontFamily: "'Courier New', monospace",
      fontSize: "13px",
    }}>
      <div style={{ color: "#999", marginBottom: "12px", fontSize: "11px", letterSpacing: "2px" }}>
        REASONING CHAIN
      </div>
      {steps.map((step, i) => (
        <div key={i} style={{
          display: "flex",
          gap: "8px",
          marginBottom: "6px",
          animation: `fadeIn 0.3s ease ${i * 0.1}s both`,
          color: step.includes("failed") ? "#ff4444" :
                 step.includes("CONFIDENT") ? "#00ff9d" :
                 step.includes("uncertain") ? "#ffcc00" :
                 step.includes("Delegating") ? "#4da6ff" :
                 step.includes("returned") || step.includes("generated") ? "#00ff9d" :
                 "#888"
        }}>
          <span style={{ color: "#ddd" }}>{">"}</span>
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
      border: `1px solid ${color}22`,
      borderTop: `2px solid ${color}`,
      borderRadius: "8px",
      padding: "20px",
      flex: 1,
      minWidth: "250px",
    }}>
      <div style={{
        color,
        fontSize: "11px",
        letterSpacing: "2px",
        marginBottom: "16px",
        fontFamily: "'Courier New', monospace"
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
        color: "#999",
        fontSize: "10px",
        letterSpacing: "1px",
        fontFamily: "'Courier New', monospace",
        marginBottom: "4px"
      }}>
        {label}
      </div>
      <div style={{
        color: highlight || "#333",
        fontSize: "13px",
        lineHeight: "1.5"
      }}>
        {value}
      </div>
    </div>
  );
}

function ConfidenceDots({ level }) {
  const color = CONFIDENCE_COLORS[level] || "#888";
  const filled = level === "high" ? 3 : level === "medium" ? 2 : 1;
  return (
    <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          background: i < filled ? color : "#ddd",
          border: `1px solid ${color}44`
        }} />
      ))}
      <span style={{ color, fontSize: "11px", marginLeft: "6px", fontFamily: "'Courier New', monospace" }}>
        {level?.toUpperCase()}
      </span>
    </div>
  );
}

function StatusBadge({ text, color }) {
  return (
    <span style={{
      background: `${color}22`,
      border: `1px solid ${color}44`,
      color,
      padding: "2px 8px",
      borderRadius: "4px",
      fontSize: "11px",
      fontFamily: "'Courier New', monospace"
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
      if (data.reasoning_chain) {
        animateChain(data.reasoning_chain);
      }
    } catch (e) {
      setError("Failed to connect to API. Make sure the server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#f5f5f5",
      color: "#111",
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
          50% { opacity: 0.4; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        * { box-sizing: border-box; }
        textarea:focus { outline: none; }
        button:hover { opacity: 0.85; cursor: pointer; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #f0f0f0; }
        ::-webkit-scrollbar-thumb { background: #ddd; border-radius: 2px; }
      `}</style>

      {/* Header */}
      <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
        <div style={{ marginBottom: "40px" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "8px"
          }}>
            <div style={{
              width: "8px", height: "8px", borderRadius: "50%",
              background: "#00ff9d",
              animation: "pulse 2s infinite"
            }} />
            <span style={{
              color: "#00ff9d",
              fontSize: "11px",
              letterSpacing: "3px",
              fontFamily: "'Courier New', monospace"
            }}>
              SOLARTIS AI DATABASE ENGINEER — LIVE
            </span>
          </div>
          <h1 style={{
            fontSize: "32px",
            fontWeight: "700",
            margin: "0 0 8px 0",
            letterSpacing: "-0.5px"
          }}>
            SQL Performance Analyzer
          </h1>
          <p style={{ color: "#777", fontSize: "14px", margin: 0 }}>
            Multi-agent RAG system · DiagnosisAgent · FixAgent · ImpactAgent
          </p>
        </div>

        {/* Input Section */}
        <div style={{
          background: "#ffffff",
          border: "1px solid #e0e0e0",
          borderRadius: "12px",
          padding: "24px",
          marginBottom: "24px"
        }}>
          {/* Mode Selector */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            {MODES.map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  padding: "6px 16px",
                  borderRadius: "6px",
                  border: mode === m ? "1px solid #00ff9d" : "1px solid #ddd",
                  background: mode === m ? "#00ff9d11" : "transparent",
                  color: mode === m ? "#00ff9d" : "#777",
                  fontSize: "12px",
                  fontFamily: "'Courier New', monospace",
                  letterSpacing: "1px",
                  transition: "all 0.2s"
                }}
              >
                {MODE_LABELS[m]}
              </button>
            ))}
          </div>

          {/* Text Input */}
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSubmit()}
            placeholder="Describe your database performance issue...&#10;e.g. 'SELECT * FROM policy_data WHERE status = ACTIVE is taking too long'"
            style={{
              width: "100%",
              background: "#f5f5f5",
              border: "1px solid #e0e0e0",
              borderRadius: "8px",
              color: "#111",
              padding: "16px",
              fontSize: "14px",
              resize: "vertical",
              minHeight: "100px",
              fontFamily: "'Segoe UI', sans-serif",
              lineHeight: "1.6"
            }}
          />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
            <span style={{ color: "#ddd", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
              Press Enter to analyze · Shift+Enter for new line
            </span>
            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              style={{
                background: loading ? "#eee" : "#00ff9d",
                color: loading ? "#777" : "#000",
                border: "none",
                borderRadius: "8px",
                padding: "10px 24px",
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
                    border: "2px solid #ddd",
                    borderTop: "2px solid #00ff9d",
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
            background: "#ff444411",
            border: "1px solid #ff444444",
            borderRadius: "8px",
            padding: "16px",
            color: "#ff4444",
            marginBottom: "24px",
            fontSize: "13px"
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Out of scope */}
        {result?.status === "out_of_scope" && (
          <div style={{
            background: "#ffcc0011",
            border: "1px solid #ffcc0044",
            borderRadius: "8px",
            padding: "20px",
            marginBottom: "24px"
          }}>
            <div style={{ color: "#ffcc00", marginBottom: "8px", fontFamily: "'Courier New', monospace", fontSize: "11px", letterSpacing: "2px" }}>
              ⚠️ OUT OF SCOPE
            </div>
            <div style={{ color: "#333", fontSize: "14px" }}>{result.error}</div>
            <div style={{ color: "#888", fontSize: "12px", marginTop: "8px" }}>
              Similarity score: {result.similarity_score}
            </div>
          </div>
        )}

        {/* Results */}
        {result?.status === "success" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

            {/* Audience Summary Banner */}
            <div style={{
              background: "#00ff9d11",
              border: "1px solid #00ff9d33",
              borderRadius: "8px",
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              gap: "12px"
            }}>
              <div style={{ fontSize: "20px" }}>
                {mode === "technical" ? "⚙️" : mode === "simple" ? "👤" : "💼"}
              </div>
              <div>
                <div style={{ color: "#00ff9d", fontSize: "10px", letterSpacing: "2px", fontFamily: "'Courier New', monospace", marginBottom: "4px" }}>
                  {mode.toUpperCase()} SUMMARY
                </div>
                <div style={{ color: "#111", fontSize: "15px", lineHeight: "1.5" }}>
                  {result.audience_summary}
                </div>
              </div>
            </div>

            {/* Reasoning Chain */}
            {visibleSteps.length > 0 && <ReasoningChain steps={visibleSteps} />}

            {/* Three Agent Cards */}
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>

              {/* Diagnosis Agent */}
              <AgentCard title="DIAGNOSISAGENT" icon="🔬" color="#4da6ff">
                <Field label="PROBLEM" value={result.diagnosis?.problem} highlight="#111" />
                <Field label="ROOT CAUSE" value={result.diagnosis?.root_cause} />
                <Field label="PATTERN MATCHED" value={result.diagnosis?.pattern_matched} />
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px" }}>
                    CONFIDENCE
                  </div>
                  <ConfidenceDots level={result.diagnosis?.confidence} />
                </div>
                <Field label="SIMILARITY SCORE" value={result.diagnosis?.similarity_score?.toFixed(4)} />
                <div style={{ marginTop: "12px" }}>
                  <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px" }}>
                    MATCHED CASES
                  </div>
                  {result.diagnosis?.matched_cases?.map((c, i) => (
                    <div key={i} style={{
                      color: "#4da6ff",
                      fontSize: "12px",
                      fontFamily: "'Courier New', monospace",
                      marginBottom: "4px"
                    }}>
                      [{i + 1}] {c}
                    </div>
                  ))}
                </div>
              </AgentCard>

              {/* Fix Agent */}
              <AgentCard title="FIXAGENT" icon="🔧" color="#00ff9d">
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px" }}>
                    SQL EXECUTED
                  </div>
                  <div style={{
                    background: "#f5f5f5",
                    border: "1px solid #e0e0e0",
                    borderRadius: "4px",
                    padding: "10px",
                    fontFamily: "'Courier New', monospace",
                    fontSize: "12px",
                    color: "#00ff9d"
                  }}>
                    {result.fix?.sql_executed || "No fix generated"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
                  {result.fix?.safe && <StatusBadge text="✓ SAFE" color="#00ff9d" />}
                  {result.fix?.validated_by && <StatusBadge text="✓ VALIDATED" color="#00ff9d" />}
                  {result.fix?.already_existed && <StatusBadge text="ALREADY APPLIED" color="#ffcc00" />}
                </div>
                <Field label="ACTION TAKEN" value={result.fix?.action_taken} />
                <Field label="QUERY BENCHMARKED" value={result.fix?.query_benchmarked} />
                <div style={{ display: "flex", gap: "16px", marginTop: "12px" }}>
                  <div>
                    <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px" }}>BEFORE</div>
                    <div style={{ color: "#ff4444", fontSize: "18px", fontWeight: "700", fontFamily: "'Courier New', monospace" }}>
                      {result.fix?.before_ms}ms
                    </div>
                  </div>
                  {result.fix?.after_ms && (
                    <>
                      <div style={{ color: "#ddd", fontSize: "20px", alignSelf: "flex-end", marginBottom: "2px" }}>→</div>
                      <div>
                        <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "4px" }}>AFTER</div>
                        <div style={{ color: "#00ff9d", fontSize: "18px", fontWeight: "700", fontFamily: "'Courier New', monospace" }}>
                          {result.fix?.after_ms}ms
                        </div>
                      </div>
                    </>
                  )}
                </div>
                {result.fix?.improvement && (
                  <div style={{
                    marginTop: "12px",
                    color: "#00ff9d",
                    fontSize: "13px",
                    fontFamily: "'Courier New', monospace"
                  }}>
                    ↑ {result.fix.improvement}
                  </div>
                )}
              </AgentCard>

              {/* Impact Agent */}
              <AgentCard title="IMPACTAGENT" icon="📊" color="#ff6b6b">
                <Field label="TECHNICAL" value={result.impact?.technical} />
                <Field label="USER FACING" value={result.impact?.user_facing} />
                <Field label="EXECUTIVE" value={result.impact?.executive} />
                <Field label="DAILY COST" value={result.impact?.estimated_daily_cost} highlight="#ffcc00" />
                <Field label="TRAJECTORY" value={result.impact?.trajectory} highlight="#ff6b6b" />
                <div style={{ marginBottom: "12px" }}>
                  <div style={{ color: "#999", fontSize: "10px", letterSpacing: "1px", fontFamily: "'Courier New', monospace", marginBottom: "6px" }}>
                    URGENCY
                  </div>
                  <StatusBadge
                    text={result.impact?.urgency?.toUpperCase() || "UNKNOWN"}
                    color={result.impact?.urgency?.includes("high") ? "#ff4444" :
                           result.impact?.urgency?.includes("medium") ? "#ffcc00" : "#00ff9d"}
                  />
                </div>
                <Field label="FIX ROI" value={result.impact?.fix_roi} highlight="#00ff9d" />
              </AgentCard>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{
          marginTop: "60px",
          paddingTop: "24px",
          borderTop: "1px solid #eee",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <div style={{ color: "#aaa", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
            RAG · ChromaDB · LLaMA 3.1 · FastAPI · Multi-Agent Architecture
          </div>
          <div style={{ color: "#aaa", fontSize: "12px", fontFamily: "'Courier New', monospace" }}>
            Built by Nova · Solartis Hackathon 2026
          </div>
        </div>
      </div>
    </div>
  );
}