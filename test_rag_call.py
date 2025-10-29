import json
from rag_openai import retrieve_relevant_context, normalize_tokens, ask_gpt4


def run_test(symptoms="Başım ağrıyor ve midem bulanıyor"):
    print("Running retrieval test for:", symptoms)
    docs = retrieve_relevant_context(symptoms, k=5)
    print("Retrieved docs:")
    for d in docs:
        print(json.dumps(d, ensure_ascii=False, indent=2))

    try:
        answer, docs2 = ask_gpt4(symptoms)
        print("\nLLM Answer:\n", answer)
    except Exception as e:
        print("LLM call failed:", e)


if __name__ == '__main__':
    run_test()
