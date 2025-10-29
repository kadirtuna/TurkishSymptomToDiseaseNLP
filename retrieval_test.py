import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np

# Load everything
index = faiss.read_index("disease_faiss.index")
with open("disease_metadata.pkl", "rb") as f:
    metadata = pickle.load(f)
model = SentenceTransformer("intfloat/multilingual-e5-base")

# Query
user_query = "Benim başım ağrıyor ve midem bulanıyor"
query_emb = model.encode([f"query: {user_query}"], convert_to_numpy=True)

# Search top 5 similar entries
k = 5
distances, indices = index.search(query_emb, k)

print("\n🔍 En benzer 5 hastalık:")
for i, idx in enumerate(indices[0]):
    print(f"{i+1}. {metadata['diseases'][idx]} ({metadata['departments'][idx]}) - distance: {distances[0][i]:.4f}")
    print(f"   → {metadata['texts'][idx][:120]}...\n")
