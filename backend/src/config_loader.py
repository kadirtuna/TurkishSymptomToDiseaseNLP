import os
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv

# ===========================
# 1. Environment & Base Paths
# ===========================

current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent  # Points to 'backend' folder

# Load .env file
load_dotenv(project_root / ".env")

class ProjectConfig:
    """
    Central configuration management using config.yaml.
    """
    def __init__(self, config_file="config.yaml"):
        self.backend_root = project_root
        config_path = self.backend_root / config_file

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found at: {config_path}")

        # YAML dosyasını oku
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)

    # ===========================
    # 2. Path Getters (Dynamic from YAML)
    # ===========================
    
    def _get_abs_path(self, relative_path_key):
        """Helper to convert YAML relative path to absolute system path."""
        rel_path = self.cfg['paths'][relative_path_key]
        return self.backend_root / rel_path

    @property
    def faiss_index_path(self):
        # FAISS genelde string path ister
        return str(self._get_abs_path('faiss_index'))

    @property
    def metadata_path(self):
        return str(self._get_abs_path('metadata'))

    @property
    def symptom_mappings_path(self):
        return self._get_abs_path('symptom_mappings')

    @property
    def stopwords_path(self):
        return self._get_abs_path('stopwords')

    # ===========================
    # 3. Parameter Getters (From YAML)
    # ===========================
    
    @property
    def embedding_model_name(self):
        return self.cfg['models']['embedding']

    @property
    def llm_model_name(self):
        return self.cfg['models']['llm']
    
    @property
    def retrieval_k(self):
        return self.cfg['parameters']['retrieval_k']
        
    @property
    def semantic_weight(self):
        return self.cfg['parameters']['semantic_weight']

    @property
    def overlap_weight(self):
        return self.cfg['parameters']['overlap_weight']

    @property
    def temperature(self):
        return self.cfg['parameters']['temperature']

    # ===========================
    # 4. Data Loaders
    # ===========================

    def load_symptom_mappings(self):
        path = self.symptom_mappings_path
        if not path.exists():
            raise FileNotFoundError(f"Symptoms JSON not found at {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_stopwords(self):
        path = self.stopwords_path
        if not path.exists():
            raise FileNotFoundError(f"Stopwords file not found at {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())

    def get_openai_api_key(self):
        key = os.getenv("OPENAI_API_TOKEN")
        if not key:
            raise ValueError("OPENAI_API_TOKEN not found in .env file.")
        return key

# ===========================
# Singleton Instance
# ===========================
config = ProjectConfig()

if __name__ == "__main__":
    # Run this file to test configuration loading
    print(f"Backend Root: {config.backend_root}")
    print(f"Loading config from: config.yaml")
    
    print(f"\n--- Paths ---")
    print(f"FAISS Path: {config.faiss_index_path}")
    print(f"Symptom Path: {config.symptom_mappings_path}")
    
    print(f"\n--- Parameters ---")
    print(f"Model: {config.embedding_model_name}")
    print(f"Weights: Semantic={config.semantic_weight}, Overlap={config.overlap_weight}")
    
    try:
        symptoms = config.load_symptom_mappings()
        print(f"\n✅ Successfully loaded {len(symptoms)} symptom mappings.")
    except Exception as e:
        print(f"\n❌ Error: {e}")