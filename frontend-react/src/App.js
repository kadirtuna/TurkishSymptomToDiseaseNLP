import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Logo from './assets/logo.svg';

function App() {
  const [symptoms, setSymptoms] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!symptoms) return setError('Lütfen semptom girin.');
    setLoading(true); setError(null); setAnswer(null); setDocs([]);
    try {
      const res = await axios.post('/api/ask', { symptoms });
      // Log the raw LLM output and retrieved docs to the browser console for debugging
      console.log('API response:', res.data);
      console.log('LLM answer:', res.data.answer);
      console.log('Retrieved docs:', res.data.retrieved_docs);
      setDocs(res.data.retrieved_docs || []);
      setAnswer(res.data.answer || res.data.fallback || null);
    } catch (e) {
      console.error('API error', e);
      setError(e.message || 'API error');
    } finally {
      setLoading(false);
    }
  }

  // Loading messages rotated while waiting
  const [loadingMsgIndex, setLoadingMsgIndex] = useState(0);
  const loadingMessages = [
    'Semptomlarına uygun bölümü buluyoruz',
    'Benzer kayıtları arıyoruz',
    'Seni en uygun bölüme yönlendireceğiz',
    'Kısa bir süre içinde sonuç gösterilecek'
  ];

  useEffect(()=>{
    if (!loading) return;
    setLoadingMsgIndex(0);
    const t = setInterval(()=>{
      setLoadingMsgIndex(i=> (i+1) % loadingMessages.length)
    }, 3000);
    return ()=> clearInterval(t);
  },[loading]);

  return (
    <div className="App">
      {/* Full page loader overlay when waiting */}
      {loading && (
        <div className="overlay" role="status" aria-busy="true">
          <div className="overlay-inner">
            <img src={Logo} alt="logo" className="logo-anim" />
            <div className="overlay-text">{loadingMessages[loadingMsgIndex]}</div>
          </div>
        </div>
      )}

      <div className="container">
        <aside className="sidebar">
          <img src={Logo} alt="logo" className="logo-small" />
          <h1>🩺 RAG Tıbbi Asistan</h1>
          <p className="muted">Kısa semptom açıklaması girin, sistem benzer kayıtları bulup öneride bulunur.</p>
        </aside>

        <main className="content">
          <label className="label">🩺 Hangi semptomlara sahipsin?</label>
          <textarea value={symptoms} onChange={(e)=>setSymptoms(e.target.value)} placeholder="örn: Başım ağrıyor ve midem bulanıyor" />

          <div className="actions">
            <button onClick={handleSubmit} disabled={loading} className="btn-primary">{loading ? 'Bekleniyor...' : 'Gönder'}</button>
            <button onClick={()=>{setSymptoms('')}} className="btn-ghost">Temizle</button>
          </div>

          {error && <div className="error">{error}</div>}

          {answer && (
            <section className="result-card">
              <h2>Sonuç</h2>
              {typeof answer === 'object' ? (
                <div className="result-grid">
                  <div>
                    <h3>Özet Belirtiler</h3>
                    <ul>{answer.patient_symptoms && answer.patient_symptoms.map((s,i)=>{
                      const cap = s && s.length ? s.charAt(0).toUpperCase() + s.slice(1) : s;
                      return (<li key={i}>{cap}</li>)
                    })}</ul>
                  </div>
                  <div>
                    <h3>Bölümler</h3>
                    <ul>{answer.departments && answer.departments.map((d,i)=>(<li key={i}>{d}</li>))}</ul>
                  </div>
                  <div className="full">
                    <h3>Açıklama</h3>
                    <p>{answer.explanation}</p>
                  </div>
                </div>
              ) : (
                <pre className="answer">{answer}</pre>
              )}
            </section>
          )}

          <section className="docs-card">
            <h3>İlgili Belgeler</h3>
            <div className="docs">
              {docs.length === 0 && <div className="muted">(Belgeler burada görünecek)</div>}
              {docs.map((d,i)=> (
                <div key={i} className="doc">
                  <div className="doc-head"><strong>{i+1}. {d.Disease}</strong><span className="dept">{d.Department}</span></div>
                  <div className="doc-text">{d.text}</div>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
