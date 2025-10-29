# ==============================
# IMPORTS
# ==============================
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ==============================
# STEP 1 — Embedding Model (Same as for FAISS)
# ==============================
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")

# Load existing FAISS index (created earlier)
db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)

# Build retriever (retrieve top 5 closest matches)
retriever = db.as_retriever(search_kwargs={"k": 5})

# ==============================
# STEP 2 — LLM Setup
# ==============================
# Use an instruction-tuned multilingual model (supports Turkish)
# You can use HuggingFace Inference API or local model if downloaded
llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",  # Strong open model
    temperature=0.2,
    max_new_tokens=300
)

# ==============================
# STEP 3 — Prompt Template (Domain Specific)
# ==============================
template = """
Sen bir tıbbi asistan sistemisin. Aşağıdaki belirtilere göre olası hastalıkları
ve ilgili hastane bölümlerini öner.

Context (bilgi tabanı):
{context}

Soru:
{question}

Yanıt:
Lütfen aşağıdaki formatta cevap ver:
- Olası hastalıklar ve tahmini olasılıkları (%)
- Önerilen hastane bölümü
- Kısa açıklama (neden bu sonucu önerdiğin)

Yanıt Türkçe olmalıdır.
"""

prompt = ChatPromptTemplate.from_template(template)

# ==============================
# STEP 4 — RAG Chain
# ==============================
def format_docs(docs):
    """Combine retrieved documents into a single context string."""
    return "\n".join(doc.page_content for doc in docs)

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# ==============================
# STEP 5 — Example Query
# ==============================
query = "Başım ağrıyor ve midem bulanıyor, hangi bölüme gitmeliyim?"
response = chain.invoke(query)

print("\n🩺 Model Yanıtı:\n", response)

# ==============================
# STEP 6 — Optional Debug Output (Retrieve Top Docs)
# ==============================
docs = retriever.invoke(query)
print("\n📚 En Benzer Kayıtlar (FAISS'den):")
for i, doc in enumerate(docs[:3]):
    print(f"\n{i+1}. {doc.page_content[:180]}...")
