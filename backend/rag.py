import json
import os
import re
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

def load_dataset(path="dataset.json"):
    with open(path, "r") as f:
        return json.load(f)

def case_to_text(case):
    return f"""
Title: {case['title']}
Query: {case['query']}
Execution Time: {case['execution_time']}
Frequency: {case['frequency']}
Context: {case['context']}
Problem: {case['problem']}
Root Cause: {case['root_cause']}
Suggestion: {case['suggestion']}
Severity: {case['severity']}
""".strip()

def build_vectordb(dataset_path="dataset.json"):
    dataset = load_dataset(dataset_path)
    documents = []
    for case in dataset:
        text = case_to_text(case)
        doc = Document(
            page_content=text,
            metadata={
                "case_id": case["case_id"],
                "title": case["title"],
                "severity": case["severity"],
                "suggestion": case["suggestion"],
                "root_cause": case["root_cause"],
                "problem": case["problem"]
            }
        )
        documents.append(doc)
    print(f"Loaded {len(documents)} cases into documents")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory="chroma_db"
    )
    print("Vector DB built and saved to chroma_db/")
    return vectordb

def load_vectordb():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )

def search_cases(query, k=3):
    vectordb = load_vectordb()
    return vectordb.similarity_search(query, k=k)