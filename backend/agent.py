import os
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

class SQLPerformanceAgent:
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        self.prompt = ChatPromptTemplate.from_template("""
SYSTEM: You are a Database Reliability Engineer. Return ONLY a JSON object. No explanation, no markdown, no extra text.

RETRIEVED_CASES:
{context}

USER_QUERY:
{question}

Return ONLY this JSON:
{{
    "problem": "problem name from matching case",
    "root_cause": "technical root cause",
    "suggestion": "specific actionable fix",
    "confidence": "high/medium/low"
}}
""")

    def analyze(self, user_query, retrieved_docs):
        context_str = "\n\n".join([
            f"Case: {d.metadata['title']}\nProblem: {d.metadata['problem']}\nRoot Cause: {d.metadata['root_cause']}\nSuggestion: {d.metadata['suggestion']}\nSeverity: {d.metadata['severity']}"
            for d in retrieved_docs
        ])
        chain = self.prompt | self.llm
        raw = chain.invoke({"context": context_str, "question": user_query}).content.strip()
        # Strip any markdown fences the LLM sneaks in
        raw = re.sub(r"```json|```", "", raw).strip()
        return raw