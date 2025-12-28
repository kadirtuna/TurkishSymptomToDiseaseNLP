import os
# Set to use pure-Python protobuf implementation for compatibility with zemberek-grpc
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import json

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Lazy import to avoid loading heavy models at start
def get_rag_module():
  import importlib
  return importlib.import_module('rag_openai')

@app.route('/health', methods=['GET'])
def health():
  return jsonify({'status': 'ok'})


@app.route('/api/ask', methods=['POST'])
def api_ask():
  print("api_ask called")
  """JSON API: accepts {'symptoms': '...', 'skip_llm': false} and returns JSON with 'answer' and 'retrieved_docs'.
  If skip_llm is true, only does RAG retrieval without calling LLM."""
  data = request.get_json(force=True, silent=True) or {}
  symptoms = (data.get('symptoms') or '').strip()
  skip_llm = data.get('skip_llm', False)
  if not symptoms:
    return jsonify({'error': 'symptoms required'}), 400

  rag = None
  try:
    rag = get_rag_module()
  except Exception as e:
    # If rag module can't be imported, return an error
    print(f"Error loading RAG module: {e}")
    traceback.print_exc()
    return jsonify({'error': 'Could not load RAG module', 'detail': str(e), 'traceback': traceback.format_exc()}), 500

  # Retrieve context
  try:
    if skip_llm:
      # Only do RAG retrieval, skip LLM
      print("Skipping LLM, only doing RAG retrieval")
      normalized_symptoms = rag.extract_normalized_symptoms(symptoms)
      normalized_query = ", ".join(normalized_symptoms)
      docs = rag.retrieve_relevant_context(normalized_query, k=5)
      return jsonify({
        'retrieved_docs': docs,
        'normalized_symptoms': normalized_symptoms
      })
    else:
      # Full pipeline with LLM
      answer, docs, normalized_symptoms = rag.ask_gpt4(symptoms)
      print("="*20)
      print(f"Answer: {answer}")
      print(f"Docs: {docs}")
      print(f"Normalized symptoms: {normalized_symptoms}")
      
      # Try to parse the answer (LLM returns a JSON string). If parse succeeds, return object.
      parsed = None
      if isinstance(answer, str):
        try:
          parsed = json.loads(answer)
        except Exception:
          parsed = None

      return jsonify({
        'answer': parsed if parsed is not None else answer, 
        'retrieved_docs': docs,
        'normalized_symptoms': normalized_symptoms
      })
  except Exception as e:
    print(f"Error in RAG processing: {e}")
    traceback.print_exc()
    return jsonify({'error': 'RAG processing failed', 'detail': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
