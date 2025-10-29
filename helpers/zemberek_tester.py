import grpc
import zemberek_grpc.morphology_pb2 as z_morphology
import zemberek_grpc.morphology_pb2_grpc as z_morphology_g

channel = grpc.insecure_channel("localhost:6789")
morphology_stub = z_morphology_g.MorphologyServiceStub(channel)

test_sentence = "Başım ağrıyor ve midem bulanıyor"

response = morphology_stub.AnalyzeSentence(
    z_morphology.SentenceAnalysisRequest(input=test_sentence)
)

for result in response.results:
    print(f"Word: {result.token}, Lemmas: {result.best.lemmas}, POS: {result.best.pos}")
