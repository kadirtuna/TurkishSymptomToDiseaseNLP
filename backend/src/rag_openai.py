import os
import faiss
import pickle
import openai
from sentence_transformers import SentenceTransformer
import re
import snowballstemmer
from zemberek_client import get_lemmas
from config_loader import config

# ===========================
# 1. Setup & Initialization
# ===========================
print("⚙️ System initializing...")

# Get API Key from Config
openai.api_key = config.get_openai_api_key()

# ===========================
# 2. Load Data & Models
# ===========================
print("🔍 Loading FAISS index and metadata...")
# Paths come from config.yaml
index = faiss.read_index(config.faiss_index_path)

with open(config.metadata_path, "rb") as f:
    metadata = pickle.load(f)

print(f"🧠 Loading embedding model: {config.embedding_model_name}...")
embedding_model = SentenceTransformer(config.embedding_model_name)

# ===========================
# 3. Load Mappings
# ===========================
print("📂 Loading static assets...")
TURKISH_STOPWORDS = config.load_stopwords()
SYMPTOM_MAPPINGS = config.load_symptom_mappings()

# ===========================
# 4. Helper Functions
# ===========================
stemmer = snowballstemmer.stemmer('turkish')

def normalize_tokens(text):
    """
    Normalize Turkish text for token overlap using loaded stopwords.
    """
    lemmas = get_lemmas(text)
    
    normalized_tokens = set()
    for lemma in lemmas:
        token = lemma.lower()
        token = re.sub(r'[^a-zığüşöç]', '', token)
        
        if token and token not in TURKISH_STOPWORDS:
            normalized_tokens.add(token)
    
    return normalized_tokens

def token_overlap(query, doc_text):
    """Compute normalized token overlap."""
    query_tokens = normalize_tokens(query)
    doc_tokens = normalize_tokens(doc_text)
    
    # Prints to be able to debug; can be disabled in production
    # print(f"Query tokens: {query_tokens}")
    # print(f"Doc tokens: {doc_tokens}")

    return len(query_tokens & doc_tokens) / max(len(query_tokens), 1)

def retrieve_relevant_context(query, k=None):
    """
    Retrieve documents using hybrid search (Semantic + Token Overlap).
    Weights are pulled from config.yaml.
    """
    # Read k from config if not provided
    if k is None:
        k = config.retrieval_k

    query_emb = embedding_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_emb, k)

    retrieved = []
    
    # Get weights from config
    w_semantic = config.semantic_weight
    w_overlap = config.overlap_weight

    for idx, dist in zip(indices[0], distances[0]):
        i = int(idx)
        if i < len(metadata["texts"]):
            doc_text = metadata["texts"][i]
            similarity = 1 / (1 + dist)
            overlap_score = token_overlap(query, doc_text)
            
            # Hybrid Score Calculation
            similarity_f = float(similarity)
            overlap_f = float(overlap_score)
            final_score = float(w_semantic * similarity_f + w_overlap * overlap_f)

            retrieved.append({
                "text": str(doc_text),
                "Disease": str(metadata["diseases"][i]),
                "Department": str(metadata["departments"][i]),
                "similarity": similarity_f,
                "overlap": overlap_f,
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
            f"Score: {doc['final_score']:.3f}"
        )
    return "\n".join(formatted)

def extract_normalized_symptoms(user_input):
    """
    Extracts symptoms using the loaded SYMPTOM_MAPPINGS dictionary.
    """
    lemmas = get_lemmas(user_input)
    print(f"🔍 Lemmas: {lemmas}")
    
    symptoms = []
    text_lower = user_input.lower()
    lemmas_lower = [l.lower() for l in lemmas]
    
    # Pre processing: Control for multi-word keys
    for key, symptom_name in SYMPTOM_MAPPINGS.items():
        found = False
        
        # Multi-word key check
        if ' ' in key:
            parts = key.split()
            all_parts_found = True
            for part in parts:
                part_found = False
                if part in text_lower:
                    part_found = True
                else:
                    for lemma in lemmas_lower:
                        if part in lemma:
                            part_found = True
                            break
                if not part_found:
                    all_parts_found = False
                    break
            if all_parts_found:
                found = True
        else:
            # Single-word key check
            if key in text_lower:
                found = True
            else:
                for lemma in lemmas_lower:
                    if key in lemma:
                        found = True
                        break
        
        if found and symptom_name not in symptoms:
            symptoms.append(symptom_name)
    
    # Post-processing: "Ağrı" filtresi (Special filter for "ağrı")
    specific_pains = ['baş ağrısı', 'karın ağrısı', 'göğüs ağrısı', 'sırt ağrısı', 
                      'boyun ağrısı', 'eklem ağrısı', 'kas ağrısı']
    
    has_specific_pain = any(pain in symptoms for pain in specific_pains)
    if has_specific_pain and 'ağrı' in symptoms:
        symptoms.remove('ağrı')
    
    if not symptoms:
        symptoms = [lemma.lower() for lemma in lemmas if lemma.lower() not in TURKISH_STOPWORDS]
        print(f"⚠️ Fallback to lemmas: {symptoms}")
    
    return symptoms

# ===========================
# 5. Core RAG Logic
# ===========================
def ask_gpt4(user_input):
    normalized_symptoms = extract_normalized_symptoms(user_input)
    normalized_query = ", ".join(normalized_symptoms)
    
    print(f"🔍 Normalized Query: {normalized_query}")
    
    # Retrieve
    retrieved_docs = retrieve_relevant_context(normalized_query)
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
        "'symptoms_to_ask': [ ... ], "
        "'disease_probabilities': [{ 'disease': 'Hastalık Adı', 'probability': 0.xx }], "
        "'explanation': '...' "
        "}"
        "Kurallar: "
        "1. 'patient_symptoms' alanında, normalize edilmiş kullanıcı belirtilerini listele. "
        "2. Eğer belirtiler tek bir departmanla yüksek güvenle eşleşiyorsa, 'departments' listesinde sadece o departmanı ver. "
        "3. Eğer belirtiler birden fazla departmanla benzer düzeyde eşleşiyorsa, 'departments' listesinde en ilgili departmanları ver. "
        "4. 'symptoms_to_ask' alanında, hastaya sorulabilecek ek belirtileri listele. "
        "   - Sadece hafif-orta şiddette belirtileri sor. "
        "   - Hastanın girmediği belirtileri sor. "
        "   - Maksimum 10 belirti. "
        "5. 'disease_probabilities' alanında olası hastalıkları ve olasılıklarını listele. "
        "6. 'explanation' alanında kısa ve detaylı açıklama yap. "
    )

    user_prompt = f"Veri tabanı kayıtları:\n{context_text}\n\nKullanıcının belirtileri: {normalized_query}"

    response = openai.chat.completions.create(
        model=config.llm_model_name,  # Get model name from Config (gpt-4o-mini)
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.temperature, # Get temperature from Config (0.2)
    )

    return response.choices[0].message.content, retrieved_docs, normalized_symptoms

# ===========================
# Main Execution
# ===========================
# Test the RAG system
if __name__ == "__main__":
    print("\n🤖 RAG-based Disease Prediction System (Refactored)\n")
    user_input = "Başım ağrıyor ve midem bulanıyor"
    
    answer, docs, symptoms = ask_gpt4(user_input)
    
    print("\n==================== AI YANITI ====================")
    print(answer)