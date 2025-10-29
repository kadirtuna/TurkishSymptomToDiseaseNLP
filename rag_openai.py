import os
import faiss
import pickle
import openai
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import re
import snowballstemmer
from zemberek_client import get_lemmas

# ===========================
# Load API key
# ===========================
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_TOKEN")

# ===========================
# Load FAISS + metadata
# ===========================
print("🔍 Loading FAISS index and metadata...")
index = faiss.read_index("data/vector/disease_faiss.index")

with open("data/vector/disease_metadata.pkl", "rb") as f:
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
# Example Turkish stopwords list (you can expand this)
TURKISH_STOPWORDS = {
    "ve", "ile", "mi", "da", "de", "bir", "bu", "şu", "o", "için", "ama", "fakat",
    "veya", "çok", "gibi", "kadar", "eğer", "ise", "daha", "en", "ve", "ki"
}

def normalize_tokens(text):
    """
    Normalize Turkish text for token overlap:
    - Lowercase
    - Remove punctuation and numbers
    - Remove stopwords
    - Lemmatize using Zemberek
    Returns a set of normalized tokens.
    """
    # Step 1: Lemmatize with Zemberek
    lemmas = get_lemmas(text)
    
    normalized_tokens = set()
    for lemma in lemmas:
        # Step 2: Lowercase
        token = lemma.lower()
        # Step 3: Remove punctuation and numbers
        token = re.sub(r'[^a-zığüşöç]', '', token)
        # Step 4: Skip stopwords and empty tokens
        if token and token not in TURKISH_STOPWORDS:
            normalized_tokens.add(token)
    
    return normalized_tokens

def token_overlap(query, doc_text):
    """Compute normalized token overlap."""
    query_tokens = normalize_tokens(query)
    doc_tokens = normalize_tokens(doc_text)

    # Print original texts
    print(f"Query: {query}")
    print(f"Doc text: {doc_text}")
    
    print(f"Query tokens: {query_tokens}")
    print(f"Doc tokens: {doc_tokens}")

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
    patient_symptoms = list(normalize_tokens(user_input))
    retrieved_docs = retrieve_relevant_context(user_input, k=5)
    context_text = format_context(retrieved_docs)

    system_prompt = (
        "Sen bir tıbbi NLP sistemisin. "
        "Aşağıdaki 'veri tabanı içeriği' hastalık, bölüm ve belirtiler bilgisini içerir. "
        "Kullanıcı Türkçe olarak belirtilerini girecektir. "
        "Yanıtını **mutlaka JSON formatında ver** ve başka hiçbir metin ekleme. "
        "JSON yapısı şu şekilde olmalıdır: "
        "{"
        "'patient_symptoms': [ ... ], "
        "'departments': [ ... ], "
        "'extra_symptoms': { 'Departman Adı': [ ... ], 'Hastalık Adı': [ ... ] }, "
        "'disease_probabilities': [{ 'disease': 'Hastalık Adı', 'probability': 0.xx }], "
        "'explanation': '...' "
        "}"
        "Kurallar: "
        "1. 'patient_symptoms' alanında, normalize edilmiş kullanıcı belirtilerini listele. "
        "2. Eğer belirtiler tek bir departmanla yüksek güvenle eşleşiyorsa, 'departments' listesinde sadece o departmanı ver. "
        "3. Eğer belirtiler birden fazla departmanla benzer düzeyde eşleşiyorsa, 'departments' listesinde en ilgili departmanları ver ve "
        "her departman için 'extra_symptoms' listesinde kullanıcıya sorulabilecek ek semptomları ekle. "
        "4. 'disease_probabilities' alanında, **verilen context içinde bulunan TÜM olası hastalıkları** (örneğin top-k = 5 veya 10), "
        "departman eşleşmesinden veya olasılık düzeyinden bağımsız şekilde **tam liste olarak** ver. "
        "Her hastalık için 0.00–0.99 aralığında makul bir olasılık değeri ile doldur (Bunun için Final score'ları kullan), "
        "ve hiçbir hastalığı atlama. "
        "5. 'extra_symptoms' alanında, **departmanlardan bağımsız olarak**, tüm hastalıklar ('disease_probabilities'te bulunan) için kullanıcıya sorulabilecek önemli semptomları ekle. "
        "6. 'explanation' alanında doktorun okuyacağı kısa ama detaylı açıklama olmalı; her hastalık için hangi ek semptomları dikkate alması gerektiğini belirt. "
        "7. Eğer belirtiler context ile eşleşmiyorsa, 'departments' ve 'disease_probabilities' boş listeler, 'extra_symptoms' boş obje, 'explanation' kısa uyarı mesajı olsun."
    )

    user_prompt = f"Veri tabanı kayıtları:\n{context_text}\n\nKullanıcının belirtileri: {user_input}"

    print("\n==================== SYSTEM PROMPT ====================")
    print(system_prompt)
    print("\n==================== USER PROMPT ====================")
    print(user_prompt[:2000])

    response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {
                "role": "user",
                "content": f"Hastanın belirtileri (tokenizasyon ile çıkarılmış): {patient_symptoms}"
            },
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
