import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Logo from './assets/logo.svg';

function PatientView({ onNavigateToDepartment }) {
  // Helper function to normalize symptoms for comparison
  const normalizeSymptom = (symptom) => {
    if (!symptom) return '';
    return symptom.toLowerCase().trim().replace(/\s+/g, ' ');
  };
  
  const [symptoms, setSymptoms] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentSymptoms, setCurrentSymptoms] = useState([]);
  const [normalizedSymptomsList, setNormalizedSymptomsList] = useState([]);
  const [surveyMode, setSurveyMode] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [retrievedDocs, setRetrievedDocs] = useState([]);
  const [negativeCount, setNegativeCount] = useState(0);
  const [questionCount, setQuestionCount] = useState(0);
  const [askedSymptoms, setAskedSymptoms] = useState(new Set());
  const [availableSymptomsToAsk, setAvailableSymptomsToAsk] = useState([]);
  const [isProcessingAnswer, setIsProcessingAnswer] = useState(false);

  const [loadingMsgIndex, setLoadingMsgIndex] = useState(0);
  const loadingMessages = [
    'Semptomlarına uygun bölümü buluyoruz',
    'Benzer kayıtları arıyoruz',
    'Seni en uygun bölüme yönlendireceğiz',
    'Kısa bir süre içinde sonuç gösterilecek'
  ];

  useEffect(() => {
    if (!loading) return;
    setLoadingMsgIndex(0);
    const t = setInterval(() => {
      setLoadingMsgIndex(i => (i + 1) % loadingMessages.length);
    }, 3000);
    return () => clearInterval(t);
  }, [loading]);

  const getDoctorInfo = async (symptomsText) => {
    try {
      const res = await axios.post('/api/ask', { symptoms: symptomsText });
      const answer = res.data.answer;
      
      console.log('LLM Raw Response:', answer);
      console.log('Response type:', typeof answer);
      
      // If answer is already an object (parsed by backend), return it
      if (answer && typeof answer === 'object') {
        console.log('Answer is already an object:', answer);
        return answer;
      }
      
      // Try to parse JSON from LLM response if it's a string
      if (answer && typeof answer === 'string') {
        try {
          // Try to parse the entire string first
          const parsed = JSON.parse(answer);
          console.log('Parsed entire response as JSON:', parsed);
          return parsed;
        } catch (e1) {
          // If that fails, try to extract JSON from response
          try {
            const jsonMatch = answer.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
              const parsed = JSON.parse(jsonMatch[0]);
              console.log('Extracted and parsed JSON from response:', parsed);
              return parsed;
            }
          } catch (e2) {
            console.warn('Could not parse LLM response as JSON:', e2);
            console.log('Returning explanation as fallback');
          }
        }
        // If we have a string but couldn't parse it, return as explanation
        return { explanation: answer };
      }
      
      return { explanation: answer || 'Analiz bilgisi alınamadı' };
    } catch (e) {
      console.error('Error getting doctor info:', e);
      return { explanation: 'Hata oluştu: ' + e.message };
    }
  };

  const analyzeSymptoms = async (symptomsText) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post('/api/ask', { symptoms: symptomsText });
      console.log('API response:', res.data);
      
      const docs = res.data.retrieved_docs || [];
      const answer = res.data.answer || {};
      const normalized = res.data.normalized_symptoms || [];
      const shouldSkipQuestions = res.data.should_skip_questions || false;
      
      setRetrievedDocs(docs);
      
      // Update normalized symptoms list
      setNormalizedSymptomsList(normalized);

      // Check if no documents have final_score > 0.6
      const hasRelevantSymptom = docs.some(d => d.final_score > 0.6);
      if (!hasRelevantSymptom) {
        setError('Herhangi bir hastalık semptomu girmediniz');
        return;
      }

      // Check if backend says we should skip questions (high confidence)
      // OR if the first doc has final_score > 0.7 and others are < 0.7
      if (shouldSkipQuestions || (docs.length > 0 && docs[0].final_score > 0.7 && docs.slice(1).every(d => d.final_score < 0.7))) {
        // Navigate to department with doctor info
        const normalizedText = normalized.join(', ');
        const doctorInfo = await getDoctorInfo(symptomsText);
        onNavigateToDepartment(docs[0].Department, normalizedText, doctorInfo, docs);
        return;
      }

      // If we reach here, we need to ask survey questions
      // Use LLM-provided symptoms_to_ask and store normalized form
      // Deduplicate the symptoms list using normalized comparison
      const rawSymptomsToAsk = answer.symptoms_to_ask || [];
      const symptomsToAsk = [];
      const seenNormalized = new Set();
      
      for (const symptom of rawSymptomsToAsk) {
        const normalized = normalizeSymptom(symptom);
        if (!seenNormalized.has(normalized)) {
          seenNormalized.add(normalized);
          symptomsToAsk.push(symptom);
        }
      }
      
      console.log('Raw symptoms from LLM:', rawSymptomsToAsk);
      console.log('Deduplicated symptoms:', symptomsToAsk);
      console.log('Should skip questions:', shouldSkipQuestions);
      
      setAvailableSymptomsToAsk(symptomsToAsk);
      const normalizedText = normalized.join(', ');
      startSurvey(docs, normalizedText, symptomsToAsk);
    } catch (e) {
      console.error('API error', e);
      setError(e.message || 'API error');
    } finally {
      setLoading(false);
    }
  };

  const startSurvey = async (docs, symptomsText, symptomsToAsk) => {
    // Check if we've already asked 4 questions
    if (questionCount >= 4) {
      // Stop asking questions, navigate to top department
      if (docs.length > 0) {
        const doctorInfo = await getDoctorInfo(symptomsText);
        onNavigateToDepartment(docs[0].Department, symptomsText, doctorInfo, docs);
      }
      return;
    }
    
    // Use LLM-provided symptoms, filter out already asked ones AND patient's current symptoms
    const currentSymptomsNormalized = normalizedSymptomsList.map(s => normalizeSymptom(s));
    const availableSymptoms = symptomsToAsk.filter(s => {
      const normalized = normalizeSymptom(s);
      const alreadyAsked = Array.from(askedSymptoms).some(asked => normalizeSymptom(asked) === normalized);
      const alreadyHas = currentSymptomsNormalized.some(current => current === normalized);
      return !alreadyAsked && !alreadyHas;
    });
    
    if (availableSymptoms.length > 0) {
      setSurveyMode(true);
      setCurrentQuestion(availableSymptoms[0]);
      setCurrentSymptoms(symptomsText);
    } else {
      // No additional symptoms to ask, navigate to top department
      if (docs.length > 0) {
        const doctorInfo = await getDoctorInfo(symptomsText);
        onNavigateToDepartment(docs[0].Department, symptomsText, doctorInfo, docs);
      }
    }
  };

  const handleSurveyAnswer = async (hasSymptom) => {
    // Prevent multiple clicks
    if (isProcessingAnswer) {
      console.log('Already processing answer, ignoring click');
      return;
    }
    
    setIsProcessingAnswer(true);
    
    const updatedAskedSymptoms = new Set([...askedSymptoms, currentQuestion]);
    setAskedSymptoms(updatedAskedSymptoms);
    
    console.log('Survey answer:', hasSymptom ? 'YES' : 'NO');
    console.log('Question asked:', currentQuestion);
    console.log('All asked symptoms:', Array.from(updatedAskedSymptoms));
    
    const newQuestionCount = questionCount + 1;
    setQuestionCount(newQuestionCount);
    
    if (hasSymptom) {
      // Add symptom and re-check with RAG only (no LLM call)
      const newSymptoms = currentSymptoms + ', ' + currentQuestion;
      // Don't hide survey yet - keep it visible to prevent blinking
      // setCurrentQuestion(null);
      // setSurveyMode(false);
      setNegativeCount(0);
      
      try {
        // Only call RAG to check scores, skip LLM
        const res = await axios.post('/api/ask', { 
          symptoms: newSymptoms,
          skip_llm: true 
        });
        
        const docs = res.data.retrieved_docs || [];
        const normalized = res.data.normalized_symptoms || [];
        setRetrievedDocs(docs);
        setNormalizedSymptomsList(normalized);
        
        // Check if we now have a confident match
        if (docs.length > 0) {
          const topScore = docs[0].final_score;
          const othersLow = docs.slice(1).every(d => d.final_score < 0.7);
          
          if (topScore > 0.7 && othersLow) {
            // Navigate to department with doctor info
            const normalizedText = normalized.join(', ');
            setSurveyMode(false); // Hide survey only when navigating
            setLoading(true); // Only show loading when navigating
            const doctorInfo = await getDoctorInfo(newSymptoms);
            setIsProcessingAnswer(false);
            onNavigateToDepartment(docs[0].Department, normalizedText, doctorInfo, docs);
            return;
          }
        }
        
        // No confident match yet, continue with existing symptoms list
        const normalizedText = normalized.join(', ');
        const currentSymptomsNormalized = normalized.map(s => normalizeSymptom(s));
        const availableSymptoms = availableSymptomsToAsk.filter(s => {
          const norm = normalizeSymptom(s);
          const alreadyAsked = Array.from(updatedAskedSymptoms).some(asked => normalizeSymptom(asked) === norm);
          const alreadyHas = currentSymptomsNormalized.some(current => current === norm);
          return !alreadyAsked && !alreadyHas;
        });
        
        if (availableSymptoms.length > 0 && newQuestionCount < 4) {
          // Continue survey with next question - survey stays visible
          setCurrentQuestion(availableSymptoms[0]);
          setCurrentSymptoms(normalizedText);
          setIsProcessingAnswer(false);
        } else {
          // No more questions or reached limit, navigate to top department
          if (docs.length > 0) {
            setSurveyMode(false); // Hide survey only when navigating
            setLoading(true); // Show loading only when navigating
            const doctorInfo = await getDoctorInfo(newSymptoms);
            setIsProcessingAnswer(false);
            onNavigateToDepartment(docs[0].Department, normalizedText, doctorInfo, docs);
          }
        }
      } catch (e) {
        console.error('API error', e);
        setError(e.message || 'API error');
        setIsProcessingAnswer(false);
      }
      // No finally block needed - loading is only set when navigating
    } else {
      // Increment negative count
      const newNegativeCount = negativeCount + 1;
      setNegativeCount(newNegativeCount);

      if (newNegativeCount >= 3) {
        // Navigate to top department after 3 negatives
        if (retrievedDocs.length > 0) {
          setLoading(true);
          const doctorInfo = await getDoctorInfo(currentSymptoms);
          setLoading(false);
          setIsProcessingAnswer(false);
          onNavigateToDepartment(retrievedDocs[0].Department, currentSymptoms, doctorInfo, retrievedDocs);
        }
        return;
      }

      // Ask next question from existing list (no API call needed)
      const currentSymptomsNormalized = normalizedSymptomsList.map(s => normalizeSymptom(s));
      const availableSymptoms = availableSymptomsToAsk.filter(s => {
        const normalized = normalizeSymptom(s);
        const alreadyAsked = Array.from(updatedAskedSymptoms).some(asked => normalizeSymptom(asked) === normalized);
        const alreadyHas = currentSymptomsNormalized.some(current => current === normalized);
        return !alreadyAsked && !alreadyHas;
      });
      
      console.log('Available symptoms to ask:', availableSymptoms);
      console.log('Already asked (normalized):', Array.from(updatedAskedSymptoms).map(s => normalizeSymptom(s)));
      console.log('Patient already has (normalized):', currentSymptomsNormalized);
      
      if (availableSymptoms.length > 0 && newQuestionCount < 4) {
        setCurrentQuestion(availableSymptoms[0]);
        setIsProcessingAnswer(false);
      } else {
        // No more questions or reached limit, navigate to top department
        if (retrievedDocs.length > 0) {
          setLoading(true);
          const doctorInfo = await getDoctorInfo(currentSymptoms);
          setLoading(false);
          setIsProcessingAnswer(false);
          onNavigateToDepartment(retrievedDocs[0].Department, currentSymptoms, doctorInfo, retrievedDocs);
        }
      }
    }
  };

  const handleSubmit = () => {
    if (!symptoms) return setError('Lütfen semptom girin.');
    setNegativeCount(0);
    setQuestionCount(0);
    setAskedSymptoms(new Set());
    setNormalizedSymptomsList([]);
    setAvailableSymptomsToAsk([]);
    analyzeSymptoms(symptoms);
  };

  if (surveyMode && currentQuestion) {
    return (
      <div className="container">
        {loading && (
          <div className="overlay" role="status" aria-busy="true">
            <div className="overlay-inner">
              <img src={Logo} alt="logo" className="logo-anim" />
              <div className="overlay-text">Bölüm öneriniz hazırlanıyor...</div>
            </div>
          </div>
        )}
        
        <main className="content survey-container">
          <div className="survey-card">
            <h2>Ek Belirtiler</h2>
            <p className="survey-question">Aşağıdaki belirtiyi yaşıyor musunuz?</p>
            <div className="symptom-box" key={currentQuestion}>
              {currentQuestion}
            </div>
            
            {isProcessingAnswer && (
              <div style={{
                textAlign: 'center',
                padding: '16px',
                color: 'var(--accent1)',
                fontSize: '14px',
                fontWeight: 500
              }}>
                <div style={{
                  display: 'inline-block',
                  width: '20px',
                  height: '20px',
                  border: '3px solid rgba(88, 166, 255, 0.3)',
                  borderTopColor: 'var(--accent1)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                  marginRight: '8px',
                  verticalAlign: 'middle'
                }}></div>
                Analiz ediliyor...
              </div>
            )}
            
            <div className="survey-actions">
              <button 
                onClick={() => handleSurveyAnswer(true)} 
                className="btn-primary"
                disabled={isProcessingAnswer || loading}
                style={{
                  opacity: isProcessingAnswer ? 0.6 : 1,
                  cursor: isProcessingAnswer ? 'not-allowed' : 'pointer'
                }}
              >
                {isProcessingAnswer ? '⏳ Bekleniyor...' : 'Evet'}
              </button>
              <button 
                onClick={() => handleSurveyAnswer(false)} 
                className="btn-secondary"
                disabled={isProcessingAnswer || loading}
                style={{
                  opacity: isProcessingAnswer ? 0.6 : 1,
                  cursor: isProcessingAnswer ? 'not-allowed' : 'pointer'
                }}
              >
                {isProcessingAnswer ? '⏳ Bekleniyor...' : 'Hayır'}
              </button>
            </div>
            <p className="survey-hint">
              {questionCount < 4 && negativeCount < 3 
                ? `En fazla ${Math.max(0, 4 - questionCount)} soru daha veya ${Math.max(0, 3 - negativeCount)} "Hayır" yanıtından sonra bölüm önerisi yapılacak.`
                : ''}
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="container">
      {loading && (
        <div className="overlay" role="status" aria-busy="true">
          <div className="overlay-inner">
            <img src={Logo} alt="logo" className="logo-anim" />
            <div className="overlay-text">{loadingMessages[loadingMsgIndex]}</div>
          </div>
        </div>
      )}

      <aside className="sidebar">
        <h1>🩺 Hasta Girişi</h1>
        <p className="muted">Semptomlarınızı girin, size en uygun bölümü bulalım.</p>
      </aside>

      <main className="content">
        <label className="label">🩺 Hangi semptomlara sahipsiniz?</label>
        <textarea 
          value={symptoms} 
          onChange={(e) => setSymptoms(e.target.value)} 
          placeholder="örn: Başım ağrıyor ve midem bulanıyor"
        />

        <div className="actions">
          <button onClick={handleSubmit} disabled={loading} className="btn-primary">
            {loading ? 'Bekleniyor...' : 'Gönder'}
          </button>
          <button onClick={() => setSymptoms('')} className="btn-ghost">Temizle</button>
        </div>

        {error && <div className="error">{error}</div>}
      </main>
    </div>
  );
}

export default PatientView;
