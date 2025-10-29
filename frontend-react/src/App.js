import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

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
      setDocs(res.data.retrieved_docs || []);
      setAnswer(res.data.answer || res.data.fallback || null);
    } catch (e) {
      setError(e.message || 'API error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>🩺 RAG Tıbbi Asistan</h1>
      </header>

      <main>
        <label>🩺 Hangi semptomlara sahipsin?:</label>
        <textarea value={symptoms} onChange={(e)=>setSymptoms(e.target.value)} placeholder="örn: Başım ağrıyor ve midem bulanıyor" />
        <div className="actions">
          <button onClick={handleSubmit} disabled={loading}>{loading ? 'Bekleniyor...' : 'Gönder'}</button>
        </div>

        {error && <div className="error">{error}</div>}
        {answer && <pre className="answer">{typeof answer === 'object' ? JSON.stringify(answer, null, 2) : answer}</pre>}

        <h3>İlgili Belgeler</h3>
        <div className="docs">
          {docs.length === 0 && <div>(Belgeler burada görünecek)</div>}
          {docs.map((d,i)=> (
            <div key={i} className="doc">
              <strong>{i+1}. {d.Disease} ({d.Department})</strong>
              <div>{d.text}</div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

export default App;
