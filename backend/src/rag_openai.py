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
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

openai.api_key = os.getenv("OPENAI_API_TOKEN")

# ===========================
# Load FAISS + metadata
# ===========================
print("🔍 Loading FAISS index and metadata...")
# Get the project root directory (two levels up from this file)
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
faiss_index_path = os.path.join(project_root, "data", "vector", "disease_faiss.index")
metadata_path = os.path.join(project_root, "data", "vector", "disease_metadata.pkl")

index = faiss.read_index(faiss_index_path)

with open(metadata_path, "rb") as f:
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
            # Ensure native Python floats for JSON serialization
            similarity_f = float(similarity)
            overlap_f = float(overlap_score)
            final_score = float(0.7 * similarity_f + 0.3 * overlap_f)

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
            f"Relevance (semantic similarity): {doc['similarity']:.3f}, "
            f"Token overlap: {doc['overlap']:.3f}, "
            f"Final score: {doc['final_score']:.3f}"
        )
    return "\n".join(formatted)

def extract_normalized_symptoms(user_input):
    """
    Extract and normalize symptoms from user input into clean symptom phrases.
    Example: "Başım ağrıyor ve midem bulanıyor" -> ["baş ağrısı", "mide bulantısı"]
    """
    # Get lemmatized tokens
    lemmas = get_lemmas(user_input)
    
    print(f"🔍 Lemmas from Zemberek: {lemmas}")
    
    # Common symptom patterns in Turkish - expanded with more variations
    symptom_mappings = {
        'baş ağr': 'baş ağrısı',  # More specific match
        'karın ağr': 'karın ağrısı',
        'göğüs ağr': 'göğüs ağrısı',
        'sırt ağr': 'sırt ağrısı',
        'boyun ağr': 'boyun ağrısı',
        'eklem ağr': 'eklem ağrısı',
        'kas ağr': 'kas ağrısı',
        'baş dön': 'baş dönmesi',  # Only match full phrase
        'ışığa duyar': 'ışığa duyarlılık',
        'ışık duyar': 'ışığa duyarlılık',
        'sese duyar': 'sese duyarlılık',
        'ses duyar': 'sese duyarlılık',
        'fotofobi': 'ışığa duyarlılık',
        'fonofobi': 'sese duyarlılık',
        'mide bulant': 'mide bulantısı',
        'bulantı': 'bulantı',
        'bulant': 'bulantı',
        'kusma': 'kusma',
        'kus': 'kusma',
        'kusmak': 'kusma',
        'öksürük': 'öksürük',
        'öksür': 'öksürük',
        'ateş': 'ateş',
        'halsiz': 'halsizlik',
        'yorgun': 'yorgunluk',
        'uyku': 'uyku sorunu',
        'karın': 'karın ağrısı',
        'göğüs': 'göğüs ağrısı',
        'nefes dar': 'nefes darlığı',
        'nefes': 'nefes darlığı',
        'ödem': 'ödem',
        'şiş': 'şişlik',
        'kızarık': 'kızarıklık',
        'kaşıntı': 'kaşıntı',
        'ishal': 'ishal',
        'kabızlık': 'kabızlık',
        'titreme': 'titreme',
        'terle': 'terleme',
        'çarpıntı': 'çarpıntı',
        'hırıltı': 'hırıltı',
        'hapşır': 'hapşırma',
        'ağr': 'ağrı',  # Generic pain - add last so specific ones match first
    }
    
    # Extract symptoms based on lemmas and input text
    symptoms = []
    text_lower = user_input.lower()
    lemmas_lower = [l.lower() for l in lemmas]
    
    print(f"🔍 Looking for symptoms in: {text_lower}")
    print(f"🔍 Lemmas (lowercase): {lemmas_lower}")
    
    for key, symptom_name in symptom_mappings.items():
        # Check if key appears in original text or in any lemma
        found = False
        
        # For multi-word keys (with space), check if both parts exist
        if ' ' in key:
            parts = key.split()
            # Check if all parts appear in text or lemmas
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
                print(f"✅ Found all parts of '{key}' -> {symptom_name}")
        else:
            # Single-word pattern
            if key in text_lower:
                found = True
                print(f"✅ Found '{key}' in text -> {symptom_name}")
            else:
                for lemma in lemmas_lower:
                    if key in lemma:
                        found = True
                        print(f"✅ Found '{key}' in lemma '{lemma}' -> {symptom_name}")
                        break
        
        if found and symptom_name not in symptoms:
            symptoms.append(symptom_name)
    
    # Post-processing: Remove generic "ağrı" if specific pain types exist
    specific_pains = ['baş ağrısı', 'karın ağrısı', 'göğüs ağrısı', 'sırt ağrısı', 
                      'boyun ağrısı', 'eklem ağrısı', 'kas ağrısı']
    has_specific_pain = any(pain in symptoms for pain in specific_pains)
    if has_specific_pain and 'ağrı' in symptoms:
        symptoms.remove('ağrı')
        print(f"🔧 Removed generic 'ağrı' because specific pain type exists")
    
    print(f"✅ Final normalized symptoms: {symptoms}")
    
    # If no specific symptoms found, return the lemmatized tokens as fallback
    if not symptoms:
        symptoms = [lemma.lower() for lemma in lemmas if lemma.lower() not in TURKISH_STOPWORDS]
        print(f"⚠️ No mappings found, using lemmas as fallback: {symptoms}")
    
    return symptoms

# ===========================
# Ask GPT-4
# ===========================
def ask_gpt4(user_input):
    # Extract normalized symptoms from user input
    normalized_symptoms = extract_normalized_symptoms(user_input)
    normalized_query = ", ".join(normalized_symptoms)
    
    print(f"\n🔍 Original input: {user_input}")
    print(f"🔍 Normalized symptoms: {normalized_symptoms}")
    print(f"🔍 Normalized query: {normalized_query}")
    
    # Use normalized query for retrieval
    retrieved_docs = retrieve_relevant_context(normalized_query, k=5)
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
        "4. 'symptoms_to_ask' alanında, hastaya sorulabilecek ek belirtileri listele. **ÇOK ÖNEMLİ:** "
        "   - SADECE belirtileri ekle (ağrı, bulantı, öksürük gibi), departman veya hastalık adı ASLA ekleme. "
        "   - Hastanın GİRMEDİĞİ belirtileri sor. "
        "   - Ağır/ciddi belirtileri (felç, sara nöbeti, bayılma, bilinç kaybı, şok gibi) ASLA sorma çünkü bu belirtileri yaşayan hasta zaten cevap veremez. "
        "   - Sadece hafif-orta şiddette, günlük yaşamda fark edilebilecek belirtileri sor (baş ağrısı, bulantı, halsizlik, öksürük, ateş gibi). "
        "   - Her belirtiyi kısa ve net sor (örn: 'baş ağrısı', 'mide bulantısı', 'ışığa duyarlılık'). Unutma, semptomlar sana verdiğim hastalık kayıtlarından gelmeli. "
        "   - En fazla 10 belirtiyi listeye ekle, önem sırasına göre. "
        "5. 'disease_probabilities' alanında, **verilen context içinde bulunan TÜM olası hastalıkları** (örneğin top-k = 5), "
        "departman eşleşmesinden veya olasılık düzeyinden bağımsız şekilde **tam liste olarak** ver. "
        "Her hastalık için 0.00–0.99 aralığında makul bir olasılık değeri ile doldur (Bunun için Final score'ları kullan). "
        "6. 'explanation' alanında doktorun okuyacağı kısa ama detaylı açıklama olmalı; her hastalık için hangi ek semptomları dikkate alması gerektiğini belirt. "
        "7. Eğer belirtiler context ile eşleşmiyorsa, 'departments' ve 'disease_probabilities' boş listeler, 'symptoms_to_ask' boş liste, 'explanation' kısa uyarı mesajı olsun."
    )

    user_prompt = f"Veri tabanı kayıtları:\n{context_text}\n\nKullanıcının belirtileri: {normalized_query}"

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
                "content": f"Hastanın normalize edilmiş belirtileri: {normalized_symptoms}"
            },
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content, retrieved_docs, normalized_symptoms

# ===========================
# Run example
# ===========================
if __name__ == "__main__":
    print("\n🤖 RAG-based Disease Prediction System\n")
    user_input = "Başım ağrıyor ve midem bulanıyor"

    answer, docs = ask_gpt4(user_input)

    print("\n==================== AI YANITI ====================")
    print(answer)
