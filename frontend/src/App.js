import React, { useState } from 'react';
import './App.css';
import Logo from './assets/logo.svg';
import PatientView from './PatientView';
import DoctorView from './DoctorView';

function App() {
  const [currentView, setCurrentView] = useState('role-selection'); // 'role-selection', 'patient', 'doctor', 'navigation'
  const [patients, setPatients] = useState([]);
  const [navigationInfo, setNavigationInfo] = useState(null);

  const handleRoleSelect = (role) => {
    if (role === 'patient') {
      setCurrentView('patient');
    } else if (role === 'doctor') {
      setCurrentView('doctor');
    }
  };

  const handleNavigateToDepartment = async (department, symptoms, doctorInfo = null, retrievedDocs = null) => {
    // Add patient to the list
    const newPatient = {
      id: patients.length + 1,
      department,
      symptoms,
      timestamp: new Date().toISOString(),
      doctorInfo: doctorInfo || null,
      retrievedDocs: retrievedDocs || []
    };
    setPatients([...patients, newPatient]);
    
    // Show navigation page
    setNavigationInfo({ department, symptoms, doctorInfo });
    setCurrentView('navigation');
  };

  const handleBackToRoleSelection = () => {
    setCurrentView('role-selection');
    setNavigationInfo(null);
  };

  // Role Selection View
  if (currentView === 'role-selection') {
    return (
      <div className="App">
        <div className="container role-selection">
          <div className="role-selection-inner">
            <img src={Logo} alt="logo" className="logo-large" />
            <h1>🩺 RAG Tıbbi Asistan Sistemi</h1>
            <p className="subtitle">Lütfen rolünüzü seçiniz</p>
            
            <div className="role-cards">
              <div className="role-card" onClick={() => handleRoleSelect('patient')}>
                <div className="role-icon">🧑‍🦱</div>
                <h2>Hasta</h2>
                <p>Semptomlarınızı girin ve bölüm önerisi alın</p>
              </div>
              
              <div className="role-card" onClick={() => handleRoleSelect('doctor')}>
                <div className="role-icon">👨‍⚕️</div>
                <h2>Doktor</h2>
                <p>Hasta listesini görüntüleyin</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Navigation/Redirection View
  if (currentView === 'navigation') {
    return (
      <div className="App">
        <div className="container navigation-view">
          <div className="navigation-inner">
            <div className="navigation-icon">✅</div>
            <h1>Yönlendirme Tamamlandı</h1>
            <div className="navigation-department">
              Sizi <strong>{navigationInfo.department}</strong> bölümüne yönlendiriyoruz...
            </div>
            <div className="navigation-symptoms">
              <strong>Belirtileriniz:</strong> {navigationInfo.symptoms}
            </div>
            <button onClick={handleBackToRoleSelection} className="btn-primary">
              Ana Sayfaya Dön
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Patient View
  if (currentView === 'patient') {
    return (
      <div className="App">
        <div className="header-bar">
          <img 
            src={Logo} 
            alt="logo" 
            className="logo-small" 
            onClick={handleBackToRoleSelection}
            style={{cursor: 'pointer'}}
            title="Ana Sayfaya Dön"
          />
          <button onClick={handleBackToRoleSelection} className="btn-back">← Ana Sayfa</button>
        </div>
        <PatientView onNavigateToDepartment={handleNavigateToDepartment} />
      </div>
    );
  }

  // Doctor View
  if (currentView === 'doctor') {
    return (
      <div className="App">
        <div className="header-bar">
          <img 
            src={Logo} 
            alt="logo" 
            className="logo-small" 
            onClick={handleBackToRoleSelection}
            style={{cursor: 'pointer'}}
            title="Ana Sayfaya Dön"
          />
          <button onClick={handleBackToRoleSelection} className="btn-back">← Ana Sayfa</button>
        </div>
        <DoctorView patients={patients} />
      </div>
    );
  }

  return null;
}

export default App;
