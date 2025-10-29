import os
import faiss
import pickle
import openai
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import re
import snowballstemmer

# ===========================
# Load API key
# ===========================
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_TOKEN")

# ===========================
# Load FAISS + metadata
# ===========================
print("🔍 Loading FAISS index and metadata...")
index = faiss.read_index("disease_faiss.index")

with open("disease_metadata.pkl", "rb") as f:
    metadata = pickle.load(f)  # {"texts": [...], "diseases": [...], "departments": [...]}

# ===========================
# Load embedding model
# ===========================
print("🧠 Loading embedding model...")
embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")

# ===========================
# Normalization
# ===========================
stemmer = snowballstemmer.stemmer('turkish')

def normalize_tokens(text):
    # Lowercase and remove non-alphabetic characters
    tokens = re.findall(r'\b[a-zA-ZığüşöçİĞÜŞÖÇ]+\b', text.lower())
    return set(stemmer.stemWord(t) for t in tokens)

def token_overlap(query, doc_text):
    """Compute normalized token overlap."""
    query_tokens = normalize_tokens(query)
    doc_tokens = normalize_tokens(doc_text)
    return len(query_tokens & doc_tokens) / max(len(query_tokens), 1)

# ===========================
# Retrieve relevant context
# ===========================
def retrieve_relevant_context(query, k=5):
    query_emb = embedding_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_emb, k)

    retrieved = []
    for idx, dist in zip(indices[0], distances[0]):
        i = int(idx)
        if i < len(metadata["texts"]):
            doc_text = metadata["texts"][i]
            similarity = 1 / (1 + dist)
            overlap_score = token_overlap(query, doc_text)
            # Hybrid score: 70% semantic, 30% token overlap
            final_score = 0.7 * similarity + 0.3 * overlap_score

            retrieved.append({
                "text": doc_text,
                "Disease": metadata["diseases"][i],
                "Department": metadata["departments"][i],
                "similarity": similarity,
                "overlap": overlap_score,
                "final_score": final_score
            })

    retrieved = sorted(retrieved, key=lambda x: x["final_score"], reverse=True)
    return retrieved[:k]

def format_context(docs):
    formatted = []
    for i, doc in enumerate(docs, 1):
        formatted.append(
            f"{i}. Hastalık: {doc['Disease']}\n"
            f"Bölüm: {doc['Department']}\n"
            f"Belirtiler: {doc['text']}\n"
            f"Relevance (semantic similarity): {doc['similarity']:.3f}, "
            f"Token overlap: {doc['overlap']:.3f}, "
            f"Final score: {doc['final_score']:.3f}"
        )
    return "\n".join(formatted)

# ===========================
# Ask GPT-4
# ===========================
def ask_gpt4(user_input):
    retrieved_docs = retrieve_relevant_context(user_input, k=5)
    context_text = format_context(retrieved_docs)

    system_prompt = (
        "Sen bir tıbbi NLP sistemisin. "
        "Aşağıdaki 'veri tabanı içeriği' hastalık, bölüm ve belirtiler bilgisini içerir. "
        "Kullanıcı Türkçe olarak belirtilerini girecektir. "
        "Sadece context içindeki bilgilerden yararlan. "
        "Context dışında bilgi üretme. "
        "Eğer belirtiler context ile eşleşmiyorsa 'Verilen veri tabanında uygun hastalık bulunamadı' yaz.\n"
        "Cevabı formatla:\n"
        "- Olası hastalıklar (context'ten alınmış):\n"
        "- Önerilen hastane bölümü:\n"
        "- Açıklama (context'e dayalı, 1-2 cümle):"
    )

    user_prompt = f"Veri tabanı kayıtları:\n{context_text}\n\nKullanıcının belirtileri: {user_input}"

    print("\n==================== SYSTEM PROMPT ====================")
    print(system_prompt)
    print("\n==================== USER PROMPT ====================")
    print(user_prompt[:2000])

    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content, retrieved_docs

# ===========================
# Run example
# ===========================
if __name__ == "__main__":
    print("\n🤖 RAG-based Disease Prediction System\n")
    user_input = "Başım ağrıyor ve midem bulanıyor"

    answer, docs = ask_gpt4(user_input)

    print("\n==================== AI YANITI ====================")
    print(answer)

    print("\n==================== İLGİLİ KAYITLAR ====================")
    for i, doc in enumerate(docs):
        print(f"\n{i+1}. {doc['text'][:250]}...")
