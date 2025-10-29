import faiss
import pickle
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Load the raw FAISS index
index = faiss.read_index("disease_faiss.index")

# Load metadata
with open("disease_metadata.pkl", "rb") as f:
    metadata = pickle.load(f)

# Create documents from metadata
documents = []
for i, (text, disease, department) in enumerate(zip(metadata["texts"], metadata["diseases"], metadata["departments"])):
    doc = Document(
        page_content=text,
        metadata={"disease": disease, "department": department}
    )
    documents.append(doc)

# Initialize embeddings
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base")

# Create FAISS vectorstore from documents
db = FAISS.from_documents(documents, embeddings)

# Save in LangChain format
db.save_local("faiss_index")

print("✅ FAISS index converted to LangChain format and saved as 'faiss_index'")