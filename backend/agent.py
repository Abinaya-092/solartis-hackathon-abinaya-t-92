import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
class SQLPerformanceAgent:
    def __init__(self):
        # We use a lower temperature to prevent 'wandering' text
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0) 
        self.prompt = ChatPromptTemplate.from_template("""
        SYSTEM: You are a Database Reliability Engineer. Your only job is to return structured JSON analysis based on provided cases.
        
        INSTRUCTIONS:
        1. Compare the USER_QUERY to the RETRIEVED_CASES.
        2. Select the most technically relevant case.
        3. Output ONLY the JSON object. Do not explain your reasoning outside the JSON.
        
        RETRIEVED_CASES:
        {context}
        
        USER_QUERY:
        {question}
        
        EXPECTED_OUTPUT_FORMAT:
        {{
            "problem": "Name from the matching case",
            "root_cause": "Technical reason from the matching case",
            "suggestion": "Specific fix from the matching case",
            "confidence": "high/medium/low"
        }}
        """)

    def analyze(self, user_query, retrieved_docs):
        # Professional move: Extract and clean context explicitly
        context_str = "\n".join([
            f"Case Match: {d.page_content}\nMetadata: {d.metadata}" 
            for d in retrieved_docs
        ])
        
        chain = self.prompt | self.llm
        response = chain.invoke({"context": context_str, "question": user_query})
        
        # Strip any accidental whitespace or markdown markers
        return response.content.strip().replace("```json", "").replace("```", "")