import os
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Load PDF
loader = PyPDFLoader("sample_policy.pdf")
documents = loader.load()

# Split into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)
print(f"Total chunks: {len(chunks)}")

# Embed + store in Chroma
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma.from_documents(chunks, embeddings)
print("Vector DB ready!")

# Retrieve relevant chunks
query = "What does this policy cover?"
docs = vectordb.similarity_search(query, k=3)
context = "\n\n".join([d.page_content for d in docs])

# Ask LLM with context
llm = ChatGroq(model="llama-3.1-8b-instant")
prompt = ChatPromptTemplate.from_template("""
You are an insurance assistant. Answer using only the context below.

Context: {context}

Question: {question}
""")
chain = prompt | llm
response = chain.invoke({"context": context, "question": query})
print("\nAnswer:", response.content)