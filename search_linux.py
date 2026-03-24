from sentence_transformers import SentenceTransformer
import chromadb
import os

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

client = chromadb.PersistentClient(path=DB_PATH)
print("Using ChromaDB at:", DB_PATH)
collection = client.get_collection("linux_kernel")

query = "How does Linux wake up a sleeping process?"

vec = model.encode(query)

results = collection.query(
    query_embeddings=[vec],
    n_results=5
)

for i, doc in enumerate(results["documents"][0]):
    print("\nRESULT", i+1)
    print(doc[:600])