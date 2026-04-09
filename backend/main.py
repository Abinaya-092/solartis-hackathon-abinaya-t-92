import os
from dotenv import load_dotenv
from rag import RAGManager
from agent import SQLPerformanceAgent

load_dotenv()

def run_system():
    # 1. Setup RAG
    rag = RAGManager()
    # Check if DB exists, if not, create it from your json
    if not os.path.exists("./chroma_db"):
        rag.initialize_from_json("../dataset.json")
    
    # 2. Setup Agent
    agent = SQLPerformanceAgent()
    
    # 3. Execution Loop
    print("\n🚀 Solartis SQL Performance Analyzer Active")
    while True:
        query = input("\nDescribe your query issue (or 'exit'): ")
        if query.lower() == 'exit': break
        
        # Step A: Retrieve
        docs = rag.retrieve_context(query)
        
        # Step B: Analyze
        analysis = agent.analyze(query, docs)
        
        print("\n--- ANALYSIS RESULT ---")
        print(analysis)

if __name__ == "__main__":
    run_system()