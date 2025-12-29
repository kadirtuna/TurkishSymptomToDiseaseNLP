import React, { useState } from 'react';

function DoctorView({ patients }) {
  const [selectedDepartment, setSelectedDepartment] = useState('all');
  const [selectedPatient, setSelectedPatient] = useState(null);
  
  // Group patients by department
  const departmentGroups = {};
  patients.forEach(patient => {
    if (!departmentGroups[patient.department]) {
      departmentGroups[patient.department] = [];
    }
    departmentGroups[patient.department].push(patient);
  });

  const departments = Object.keys(departmentGroups).sort();
  const filteredPatients = selectedDepartment === 'all' 
    ? patients 
    : departmentGroups[selectedDepartment] || [];

  const handlePatientClick = (patient) => {
    setSelectedPatient(patient);
  };

  const handleBackToList = () => {
    setSelectedPatient(null);
  };

  // If a patient is selected, show detail view
  if (selectedPatient) {
    let doctorInfo = selectedPatient.doctorInfo;
    const docs = selectedPatient.retrievedDocs || [];
    
    // Handle case where doctorInfo might be a string (old data)
    if (typeof doctorInfo === 'string') {
      try {
        const jsonMatch = doctorInfo.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          doctorInfo = JSON.parse(jsonMatch[0]);
        } else {
          doctorInfo = { explanation: doctorInfo };
        }
      } catch (e) {
        doctorInfo = { explanation: doctorInfo };
      }
    }
    
    // Ensure doctorInfo is an object
    if (!doctorInfo || typeof doctorInfo !== 'object') {
      doctorInfo = {};
    }
    
    // Debug log to see what we have
    console.log('=== DOCTOR VIEW DEBUG ===');
    console.log('Patient Doctor Info:', doctorInfo);
    console.log('Doctor Info Keys:', doctorInfo ? Object.keys(doctorInfo) : 'null');
    console.log('Explanation:', doctorInfo?.explanation);
    console.log('Symptoms to ask:', doctorInfo?.symptoms_to_ask);
    console.log('Retrieved Docs:', docs);
    console.log('========================');
    
    return (
      <div className="container">
        <aside className="sidebar">
          <h1>👨‍⚕️ Hasta Detayı</h1>
          <button onClick={handleBackToList} className="btn-secondary">
            ← Hasta Listesine Dön
          </button>
          <div className="patient-summary">
            <h3>Hasta #{selectedPatient.id}</h3>
            <p><strong>Bölüm:</strong> {selectedPatient.department}</p>
            <p><strong>Kayıt:</strong> {new Date(selectedPatient.timestamp).toLocaleString('tr-TR')}</p>
            {docs.length > 0 && (
              <>
                <hr style={{margin: '12px 0', opacity: 0.2}} />
                <p><strong>En Olası Tanı:</strong></p>
                <p style={{color: 'var(--accent1)', fontSize: '15px', fontWeight: 600}}>
                  {docs[0].Disease}
                </p>
                <p style={{fontSize: '13px', color: 'var(--muted)'}}>
                  Güven: {((docs[0].final_score || 0) * 100).toFixed(1)}%
                </p>
              </>
            )}
          </div>
        </aside>

        <main className="content">
          <div className="patient-detail">
            
            {/* Show warning if no LLM data available */}
            {(!doctorInfo || Object.keys(doctorInfo).length === 0) && (
              <section className="detail-section" style={{borderColor: 'rgba(255,193,7,0.5)', background: 'rgba(255,193,7,0.08)'}}>
                <h2>⚠️ Dikkat</h2>
                <p>Bu hasta için detaylı analiz bilgisi bulunmamaktadır. Aşağıdaki RAG eşleşmelerine dayanarak değerlendirme yapabilirsiniz.</p>
              </section>
            )}

            <section className="detail-section">
              <h2>🔍 Tespit Edilen Belirtiler</h2>
              <div className="symptoms-box">
                {doctorInfo && doctorInfo.patient_symptoms && Array.isArray(doctorInfo.patient_symptoms) ? (
                  <ul>
                    {doctorInfo.patient_symptoms.map((symptom, idx) => {
                      const symptomStr = String(symptom);
                      return <li key={idx}>{symptomStr.charAt(0).toUpperCase() + symptomStr.slice(1)}</li>;
                    })}
                  </ul>
                ) : (
                  <p>{String(selectedPatient.symptoms || 'Belirtiler bulunamadı')}</p>
                )}
              </div>
            </section>
            
                        {/* Suggested Departments */}
            {(() => {
              const otherDepartments = doctorInfo && doctorInfo.departments && Array.isArray(doctorInfo.departments)
                ? doctorInfo.departments.filter(dept => String(dept).toLowerCase() !== String(selectedPatient.department).toLowerCase())
                : [];
              return otherDepartments.length > 0 && (
                <section className="detail-section">
                  <h2>🏥 Önerilen Diğer Bölümler</h2>
                  <div className="departments-box">
                    {otherDepartments.map((dept, idx) => (
                      <span key={idx} className="department-badge">{String(dept)}</span>
                    ))}
                  </div>
                </section>
              );
            })()}

            {/* Additional Symptoms to Ask - Separate Section */}
            {doctorInfo && doctorInfo.symptoms_to_ask && Array.isArray(doctorInfo.symptoms_to_ask) && doctorInfo.symptoms_to_ask.length > 0 ? (
              <section className="detail-section highlight">
                <h2>❓ Sorulması Önerilen Ek Belirtiler</h2>
                <p className="info-text">Hasta ile yüz yüze görüşmede bu belirtileri sorgulayabilirsiniz:</p>
                <ul className="symptoms-ask-list">
                  {doctorInfo.symptoms_to_ask.map((symptom, idx) => {
                    const symptomStr = String(symptom);
                    return <li key={idx}>{symptomStr.charAt(0).toUpperCase() + symptomStr.slice(1)}</li>;
                  })}
                </ul>
              </section>
            ) : (
              <section className="detail-section" style={{opacity: 0.6, background: 'rgba(255,100,100,0.05)'}}>
                <h2>❓ Sorulması Önerilen Ek Belirtiler</h2>
                <p className="info-text" style={{color: '#ff9999'}}>
                  Bu hasta için ek belirti önerisi bulunmamaktadır.
                  {doctorInfo && (
                    <span style={{display: 'block', fontSize: '12px', marginTop: '8px', fontFamily: 'monospace'}}>
                      Debug: symptoms_to_ask = {JSON.stringify(doctorInfo.symptoms_to_ask)}
                    </span>
                  )}
                </p>
              </section>
            )}

            {doctorInfo && doctorInfo.disease_probabilities && Array.isArray(doctorInfo.disease_probabilities) && doctorInfo.disease_probabilities.length > 0 && (
              <section className="detail-section">
                <h2>📊 Hastalık Olasılıkları</h2>
                <div className="probability-list">
                  {doctorInfo.disease_probabilities
                    .slice()
                    .sort((a, b) => (b.probability || 0) - (a.probability || 0))
                    .map((item, idx) => (
                    <div key={idx} className="probability-item">
                      <div className="probability-header">
                        <span className="disease-name">{String(item.disease || 'Bilinmeyen')}</span>
                        <span className="probability-value">{((item.probability || 0) * 100).toFixed(1)}%</span>
                      </div>
                      <div className="probability-bar">
                        <div 
                          className="probability-fill" 
                          style={{ width: `${((item.probability || 0) * 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Clinical Explanation - Only show the explanation field */}
            {doctorInfo && doctorInfo.explanation && typeof doctorInfo.explanation === 'string' && doctorInfo.explanation.trim() ? (
              <section className="detail-section important">
                <h2>💡 Klinik Değerlendirme ve Öneriler</h2>
                <div className="explanation-box">
                  {doctorInfo.explanation.split('\n').filter(line => line.trim()).map((line, idx) => (
                    <p key={idx}>{line}</p>
                  ))}
                </div>
              </section>
            ) : (
              <section className="detail-section" style={{opacity: 0.6, background: 'rgba(255,100,100,0.05)'}}>
                <h2>💡 Klinik Değerlendirme ve Öneriler</h2>
                <p className="info-text" style={{color: '#ff9999'}}>
                  Bu hasta için detaylı klinik değerlendirme bilgisi bulunmamaktadır.
                  {doctorInfo && (
                    <span style={{display: 'block', fontSize: '12px', marginTop: '8px', fontFamily: 'monospace'}}>
                      Debug: explanation type = {typeof doctorInfo.explanation}, value = {JSON.stringify(doctorInfo.explanation)?.substring(0, 100)}
                    </span>
                  )}
                </p>
              </section>
            )}


            {docs.length > 0 && (
              <section className="detail-section">
                <h2>📚 Eşleşen Hastalık Kayıtları (Top {Math.min(3, docs.length)})</h2>
                {docs.slice(0, 3).map((doc, idx) => (
                  <div key={idx} className="doc-card">
                    <div className="doc-header">
                      <h3>{String(doc.Disease || 'Bilinmeyen')}</h3>
                      <span className="doc-score">Skor: {((doc.final_score || 0) * 100).toFixed(1)}%</span>
                    </div>
                    <p><strong>Bölüm:</strong> {String(doc.Department || 'Bilinmeyen')}</p>
                    <p className="doc-text">{String(doc.text || 'Açıklama bulunamadı')}</p>
                  </div>
                ))}
              </section>
            )}
          </div>
        </main>
      </div>
    );
  }

  // List view
  return (
    <div className="container">
      <aside className="sidebar">
        <h1>👨‍⚕️ Doktor Paneli</h1>
        <p className="muted">Bölümlere göre hasta listesi</p>
        
        <div className="department-filter">
          <label>Bölüm Seçimi:</label>
          <select 
            value={selectedDepartment} 
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="select-box"
          >
            <option value="all">Tüm Bölümler</option>
            {departments.map((dept, idx) => (
              <option key={idx} value={dept}>{dept}</option>
            ))}
          </select>
        </div>
      </aside>

      <main className="content">
        <h2>
          {selectedDepartment === 'all' 
            ? 'Tüm Hastalar' 
            : `${selectedDepartment} Hastaları`}
        </h2>
        
        <div className="patient-list">
          {filteredPatients.length === 0 ? (
            <div className="empty-state">Henüz hasta bulunmamaktadır.</div>
          ) : (
            filteredPatients.map((patient, idx) => (
              <div 
                key={idx} 
                className="patient-card clickable" 
                onClick={() => handlePatientClick(patient)}
              >
                <div className="patient-header">
                  <span className="patient-id">Hasta #{patient.id}</span>
                  <span className="patient-department">{patient.department}</span>
                </div>
                <div className="patient-symptoms">
                  <strong>Belirtiler:</strong> {patient.symptoms}
                </div>
                <div className="patient-time">
                  {new Date(patient.timestamp).toLocaleString('tr-TR')}
                </div>
                <div className="patient-action">
                  Detayları Görüntüle →
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}

export default DoctorView;
