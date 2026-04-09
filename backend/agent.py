import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

class SQLPerformanceAgent:
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0) # Temp 0 for consistency
        self.prompt = ChatPromptTemplate.from_template("""
        You are an Expert Database Reliability Engineer (DBRE).
        Analyze the query performance issue using ONLY the retrieved cases.
        
        RELEVANT CASES:
        {context}
        
        USER QUERY ISSUE:
        {question}
        
        Return ONLY a valid JSON object:
        {{
            "problem": "Name of the issue",
            "root_cause": "Brief technical reason",
            "suggestion": "Specific fix to apply",
            "confidence": "high/medium/low"
        }}
        """)

    def analyze(self, user_query, retrieved_docs):
        # Format the metadata from RAG into a string for the prompt
        context_str = ""
        for i, d in enumerate(retrieved_docs):
            context_str += f"\nCASE {i+1}: {d.metadata['problem']}\nCause: {d.metadata['root_cause']}\nFix: {d.metadata['suggestion']}\n"
        
        chain = self.prompt | self.llm
        response = chain.invoke({"context": context_str, "question": user_query})
        return response.content