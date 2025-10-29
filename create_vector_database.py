from sentence_transformers import SentenceTransformer
import pandas as pd
import faiss
import numpy as np
import pickle

# ==============================
# Step 1 — Load Dataset
# ==============================
df = pd.read_csv("hastalik_with_text.csv", encoding="utf-8")

# Ensure 'text' column exists
if "text" not in df.columns:
    raise ValueError("❌ 'text' column not found. Run the concatenation step first.")

texts = df["text"].tolist()

# ==============================
# Step 2 — Load Embedding Model
# ==============================
model_name = "intfloat/multilingual-e5-base"
model = SentenceTransformer(model_name)

# ==============================
# Step 3 — Generate Embeddings
# ==============================
# Add "passage: " prefix (recommended for E5 model)
texts_for_embedding = [f"passage: {t}" for t in texts]
embeddings = model.encode(texts_for_embedding, convert_to_numpy=True, show_progress_bar=True, batch_size=32)

# ==============================
# Step 4 — Build FAISS Index
# ==============================
embedding_dim = embeddings.shape[1]
index = faiss.IndexFlatL2(embedding_dim)
index.add(embeddings)

# ==============================
# Step 5 — Save Index + Metadata
# ==============================
faiss.write_index(index, "disease_faiss.index")

# Save metadata (to map results back later)
metadata = {
    "texts": texts,
    "diseases": df["Disease"].tolist(),
    "departments": df["Department"].tolist()
}
with open("disease_metadata.pkl", "wb") as f:
    pickle.dump(metadata, f)

print("✅ FAISS index and metadata saved successfully!")
print(f"Total entries indexed: {len(texts)}")
