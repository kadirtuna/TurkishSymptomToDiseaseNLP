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
  # Directly call the RAG pipeline's ask_gpt4 (no fallback logic)
  answer, docs = rag.ask_gpt4(symptoms)

  # Try to parse the answer (LLM returns a JSON string). If parse succeeds, return object.
  parsed = None
  if isinstance(answer, str):
    try:
      parsed = json.loads(answer)
    except Exception:
      parsed = None

  return jsonify({'answer': parsed if parsed is not None else answer, 'retrieved_docs': docs})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
