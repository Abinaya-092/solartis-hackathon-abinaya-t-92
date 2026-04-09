import json
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

class RAGManager:
    def __init__(self, db_path="./chroma_db"):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.db_path = db_path
        self.vectordb = None

    def initialize_from_json(self, json_file):
        with open(json_file, "r") as f:
            data = json.load(f)
        
        documents = []
        for case in data:
            # We search based on the query and context
            content = f"Query: {case['query']}\nContext: {case['context']}"
            
            # Metadata allows the LLM to 'see' the diagnosis directly
            metadata = {
                "problem": case["problem"],
                "root_cause": case["root_cause"],
                "suggestion": case["suggestion"],
                "severity": case["severity"]
            }
            documents.append(Document(page_content=content, metadata=metadata))
        
        self.vectordb = Chroma.from_documents(
            documents, 
            self.embeddings, 
            persist_directory=self.db_path
        )
        print(f"✅ RAG initialized with {len(data)} scenarios.")

    def retrieve_context(self, user_query, k=2):
        if not self.vectordb:
            self.vectordb = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
        
        docs = self.vectordb.similarity_search(user_query, k=k)
        return docs