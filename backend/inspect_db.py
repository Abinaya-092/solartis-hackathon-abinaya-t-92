from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Initialize the same setup
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# Get all data from the collection
data = vectordb.get()

print(f"Total items in DB: {len(data['ids'])}\n")

for i in range(len(data['ids'])):
    print(f"--- DOCUMENT {i+1} ---")
    print(f"ID: {data['ids'][i]}")
    print(f"CONTENT: {data['documents'][i][:100]}...") # Show first 100 chars
    print(f"METADATA: {data['metadatas'][i]}")
    print("-" * 30)
# Add 'embeddings' to the get() call
data = vectordb.get(include=['documents', 'metadatas', 'embeddings'])

# Look at the first document's vector
first_vector = data['embeddings'][0]

print(f"Vector Length: {len(first_vector)}")
print(f"First 5 numbers of the vector: {first_vector[:5]}")