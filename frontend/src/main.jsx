import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { LanguageProvider } from './contexts/LanguageContext.jsx'; // ADD THIS

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageProvider>  {/* WRAP APP WITH PROVIDER */}
      <App />
    </LanguageProvider>
  </React.StrictMode>,
);