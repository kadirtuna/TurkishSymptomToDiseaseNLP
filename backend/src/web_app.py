import os
# Set to use pure-Python protobuf implementation for compatibility with zemberek-grpc
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback
import json

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Load RAG module once at startup (not lazy)
print("🚀 Loading RAG module at startup...")
import rag_openai as rag
print("✅ RAG module loaded successfully!")

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

  # Retrieve context
  try:
    if skip_llm:
      # Only do RAG retrieval, skip LLM
      print("Skipping LLM, only doing RAG retrieval")
      normalized_symptoms = rag.extract_symptoms_via_llm(symptoms)
      normalized_query = ", ".join(normalized_symptoms)
      docs = rag.retrieve_relevant_context(normalized_query, k=5)
      
      # Check score confidence even in skip_llm mode
      should_skip_questions = False
      if docs and len(docs) > 0:
        top_score = docs[0].get('final_score', 0)
        other_scores = [doc.get('final_score', 0) for doc in docs[1:]]
        
        # Log top 3 scores for debugging
        top_3_info = [(doc.get('Disease', 'Unknown'), doc.get('final_score', 0)) for doc in docs[:3]]
        print(f"📊 Top 3 Scores: {', '.join([f'{disease}: {score:.3f}' for disease, score in top_3_info])}")
        
        # If top score > 0.7 AND all others < 0.7, we have high confidence
        if top_score > 0.7 and all(score < 0.7 for score in other_scores):
          should_skip_questions = True
          print(f"🎯 High confidence decision: top={top_score:.3f}, all others < 0.7, skipping questions")
        else:
          others_above_threshold = [score for score in other_scores if score >= 0.7]
          print(f"❓ Low confidence: top={top_score:.3f}, {len(others_above_threshold)} other(s) >= 0.7, will ask questions")
      
      return jsonify({
        'retrieved_docs': docs,
        'normalized_symptoms': normalized_symptoms,
        'should_skip_questions': should_skip_questions
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

      # Check score confidence to decide if we should ask more questions
      should_skip_questions = False
      if docs and len(docs) > 0:
        top_score = docs[0].get('final_score', 0)
        other_scores = [doc.get('final_score', 0) for doc in docs[1:]]
        
        # Log top 3 scores for debugging
        top_3_info = [(doc.get('Disease', 'Unknown'), doc.get('final_score', 0)) for doc in docs[:3]]
        print(f"📊 Top 3 Scores: {', '.join([f'{disease}: {score:.3f}' for disease, score in top_3_info])}")
        
        # If top score > 0.7 AND all others < 0.7, we have high confidence
        if top_score > 0.7 and all(score < 0.7 for score in other_scores):
          should_skip_questions = True
          print(f"🎯 High confidence decision: top={top_score:.3f}, all others < 0.7, skipping questions")
        else:
          others_above_threshold = [score for score in other_scores if score >= 0.7]
          print(f"❓ Low confidence: top={top_score:.3f}, {len(others_above_threshold)} other(s) >= 0.7, will ask questions")
      
      # Modify parsed response to include skip_questions flag
      if parsed and isinstance(parsed, dict):
        parsed['should_skip_questions'] = should_skip_questions
        # If skipping questions, clear symptoms_to_ask
        if should_skip_questions:
          parsed['symptoms_to_ask'] = []

      return jsonify({
        'answer': parsed if parsed is not None else answer, 
        'retrieved_docs': docs,
        'normalized_symptoms': normalized_symptoms,
        'should_skip_questions': should_skip_questions
      })
  except Exception as e:
    print(f"Error in RAG processing: {e}")
    traceback.print_exc()
    return jsonify({'error': 'RAG processing failed', 'detail': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
