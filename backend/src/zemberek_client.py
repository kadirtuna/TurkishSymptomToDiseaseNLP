import grpc
import zemberek_grpc.morphology_pb2 as z_morphology
import zemberek_grpc.morphology_pb2_grpc as z_morphology_g

# Connect to running Zemberek container
channel = grpc.insecure_channel("localhost:6789")
morphology_stub = z_morphology_g.MorphologyServiceStub(channel)

def get_lemmas(text):
    """
    Lemmatizes a Turkish sentence using Zemberek morphological analysis.
    Returns a list of lemmas.
    """
    response = morphology_stub.AnalyzeSentence(z_morphology.SentenceAnalysisRequest(input=text))
    lemmas = []
    for result in response.results:
        if result.best.lemmas:
            lemmas.extend(result.best.lemmas)
    return lemmas
