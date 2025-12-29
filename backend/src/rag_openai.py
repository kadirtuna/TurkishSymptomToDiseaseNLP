import faiss
import pickle
import openai
from sentence_transformers import SentenceTransformer
from config_loader import config
import json

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
# 3. Helper Functions
# ===========================
def extract_symptoms_from_text(text):
    """
    Extract symptoms from text. Handles both:
    - Full document format: "Hastalık: X. Bölüm: Y. Belirtiler: symptom1, symptom2"
    - Simple comma-separated format: "symptom1, symptom2"
    """
    # Check if it's a full document with "Belirtiler:" section
    if "Belirtiler:" in text:
        # Extract everything after "Belirtiler:"
        symptoms_part = text.split("Belirtiler:")[-1].strip()
    else:
        # Already a simple symptom list
        symptoms_part = text
    
    # Split by comma, strip whitespace, and lowercase
    symptoms = {s.strip().lower() for s in symptoms_part.split(",") if s.strip()}
    return symptoms

def token_overlap(query, doc_text):
    """Compute token overlap between comma-separated symptom lists."""
    query_symptoms = extract_symptoms_from_text(query)
    doc_symptoms = extract_symptoms_from_text(doc_text)
    
    # Uncomment for debugging
    # print(f"Query symptoms: {query_symptoms}")
    # print(f"Doc symptoms: {doc_symptoms}")

    return len(query_symptoms & doc_symptoms) / max(len(query_symptoms), 1)

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

def extract_symptoms_via_llm(user_input):
    """
    Extracts symptoms from user input using LLM.
    Returns a list of normalized symptom names.
    """
    system_prompt = (
        "Sen bir tıbbi belirtileri çıkaran sistemsin. "
        "Kullanıcının Türkçe olarak girdiği metinden tüm sağlık belirtilerini (semptomları) çıkarmalısın. "
        "Yanıtını **mutlaka JSON formatında ver** ve başka hiçbir metin ekleme. "
        "JSON yapısı şu şekilde olmalıdır (ÇİFT TIRNAK KULLAN): "
        '{ "symptoms": ["belirti1", "belirti2"] } '
        "Kurallar: "
        "1. Sadece tıbbi belirtileri listele (ateş, baş ağrısı, öksürük, bulantı, vb.). "
        "2. Her belirtiyi normalize edilmiş, standart Türkçe adıyla ver. "
        "3. Eğer kullanıcı 'başım ağrıyor' diyorsa 'baş ağrısı' olarak normalize et. "
        '4. Eğer hiç belirti yoksa boş liste döndür: { "symptoms": [] } '
        "5. MUTLAKA çift tırnak kullan, tek tırnak kullanma!"
    )
    
    user_prompt = f"Kullanıcının metni: {user_input}"
    
    response = openai.chat.completions.create(
        model=config.llm_model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,  # Lower temperature for more deterministic extraction
    )
    
    result_text = response.choices[0].message.content.strip()
    print(f"🤖 LLM Extraction Response: {result_text}")
    
    try:
        # Try to replace single quotes with double quotes if needed
        result_text_fixed = result_text.replace("'", '"')
        result_json = json.loads(result_text_fixed)
        symptoms = result_json.get('symptoms', [])
        print(f"✅ Extracted Symptoms: {symptoms}")
        return symptoms
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e}")
        print(f"⚠️ Using simple extraction as fallback")
        # Simple fallback: extract words from input
        import re
        words = re.findall(r'[a-zığüşöçA-ZİĞÜŞÖÇ\s]+', user_input)
        return [w.strip().lower() for w in words if w.strip()]


# ===========================
# 5. Core RAG Logic
# ===========================
def ask_gpt4(user_input):
    normalized_symptoms = extract_symptoms_via_llm(user_input)
    normalized_query = ", ".join(normalized_symptoms)
    
    print(f"🔍 Normalized Query: {normalized_query}")
    
    # Retrieve
    retrieved_docs = retrieve_relevant_context(normalized_query)
    context_text = format_context(retrieved_docs)

    system_prompt = (
        "Sen bir tıbbi NLP sistemisin. "
        "Aşağıdaki 'veri tabanı içeriği' hastalık, bölüm, belirtiler ve eşleşme skorları bilgisini içerir. "
        "Kullanıcı Türkçe olarak belirtilerini girecektir. "
        "Yanıtını **mutlaka JSON formatında ver** ve başka hiçbir metin ekleme. "
        "JSON yapısı şu şekilde olmalıdır (ÇİFT TIRNAK KULLAN): "
        '{ "patient_symptoms": [...], "departments": [...], "symptoms_to_ask": [...], '
        '"disease_probabilities": [{"disease": "...", "probability": 0.xx}], "explanation": "..." }'
        "\n\nKurallar: "
        "1. 'patient_symptoms' alanında, normalize edilmiş kullanıcı belirtilerini listele. "
        "2. Eğer belirtiler tek bir departmanla yüksek güvenle eşleşiyorsa, 'departments' listesinde sadece o departmanı ver. "
        "3. Eğer belirtiler birden fazla departmanla benzer düzeyde eşleşiyorsa, 'departments' listesinde en ilgili departmanları ver. "
        "4. 'symptoms_to_ask' alanında, hastaya sorulabilecek ek belirtileri listele. "
        "   - Sadece hafif-orta şiddette belirtileri sor. "
        "   - Hastanın girmediği belirtileri sor. "
        "   - Maksimum 10 belirti. "
        "5. 'disease_probabilities' alanında, veri tabanı kayıtlarında verilen 'Score' değerlerini AYNEN kullan. "
        "   - Her hastalığın olasılığını (probability) Score / 100 olarak hesapla. "
        "   - Örnek: Score: 0.646 ise probability: 0.646 yaz. "
        "   - Hastalıkları Score değerine göre azalan sırada listele. "
        "6. 'explanation' alanında kısa ve detaylı açıklama yap. "
        "7. MUTLAKA çift tırnak kullan, tek tırnak kullanma!"
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