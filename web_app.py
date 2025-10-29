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
  """JSON API: accepts {'symptoms': '...'} and returns JSON with 'answer' and 'retrieved_docs'.
  If the LLM call fails, returns a fallback using the retrieval results."""
  data = request.get_json(force=True, silent=True) or {}
  symptoms = (data.get('symptoms') or '').strip()
  if not symptoms:
    return jsonify({'error': 'symptoms required'}), 400

  rag = None
  try:
    rag = get_rag_module()
  except Exception as e:
    # If rag module can't be imported, return an error
    return jsonify({'error': 'Could not load RAG module', 'detail': str(e)}), 500

  # Retrieve context
  try:
    retrieved = rag.retrieve_relevant_context(symptoms, k=5)
  except Exception as e:
    return jsonify({'error': 'Retrieval failed', 'detail': str(e)}), 500

  # Attempt LLM call with timeout; if fails return fallback
  try:
    answer, docs = rag.ask_gpt4(symptoms)
    # Try to parse the answer (LLM returns a JSON string). If parse succeeds, return object.
    parsed = None
    if isinstance(answer, str):
      try:
        parsed = json.loads(answer)
      except Exception:
        parsed = None

    return jsonify({'answer': parsed if parsed is not None else answer, 'retrieved_docs': retrieved})
  except Exception as e:
    # Fallback: construct a simple JSON response from retrieved docs
    fallback = {
      'patient_symptoms': rag.normalize_tokens(symptoms),
      'departments': list({d['Department'] for d in retrieved}),
      'extra_symptoms': {},
      'disease_probabilities': [
        {'disease': d['Disease'], 'probability': round(d['final_score'], 2)} for d in retrieved
      ],
      'explanation': 'LLM çağrısı başarısız oldu, retrieval tabanlı tahminler döndürüldü.'
    }
    return jsonify({'answer': None, 'retrieved_docs': retrieved, 'fallback': fallback, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
