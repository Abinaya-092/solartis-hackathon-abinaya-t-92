import json
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
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

def search_cases_with_confidence(query, k=3):
    """
    Searches with similarity scoring.
    Returns results WITH confidence level based on distance scores.
    
    Chroma returns L2 distance — lower = more similar:
    < 1.2  → high confidence
    1.2-1.5 → low confidence, warn user
    > 1.5  → outside knowledge base, reject
    """
    vectordb = load_vectordb()
    results = vectordb.similarity_search_with_score(query, k=k)

    CONFIDENT_THRESHOLD = 1.2
    UNCERTAIN_THRESHOLD = 1.5

    best_score = results[0][1] if results else 999

    if best_score > UNCERTAIN_THRESHOLD:
        return {
            "docs": [],
            "confidence_level": "out_of_scope",
            "best_score": round(best_score, 4),
            "warning": "Query is outside the knowledge base. No reliable match found."
        }
    elif best_score > CONFIDENT_THRESHOLD:
        return {
            "docs": [doc for doc, score in results],
            "confidence_level": "uncertain",
            "best_score": round(best_score, 4),
            "warning": "Low confidence match. Diagnosis may be inaccurate."
        }
    else:
        return {
            "docs": [doc for doc, score in results],
            "confidence_level": "confident",
            "best_score": round(best_score, 4),
            "warning": None
        }