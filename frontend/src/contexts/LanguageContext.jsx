// frontend/src/contexts/LanguageContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';

const LanguageContext = createContext();

export const translations = {
  en: {
    // Navigation
    dashboard: "Dashboard",
    settings: "Settings",
    backToDashboard: "Back to Dashboard",
    
    // Header
    sproutHub: "Sprout Hub",
    monitoring: "Monitoring",
    nodes: "nodes",
    node: "node",
    detected: "detected",
    autoDetecting: "Auto-detecting soil monitoring nodes",
    
    // Loading
    loading: "Loading Sprout Hub System...",
    detectingNodes: "Detecting soil nodes...",
    
    // No Nodes
    noNodesDetected: "No Soil Nodes Detected",
    waitingForNodes: "Waiting for soil nodes to come online...",
    autoDetectionActive: "Auto-Detection Active",
    autoDetectionDesc: "New nodes will automatically appear when they send their first reading.",
    refreshPage: "Refresh Page",
    
    // New Node Notification
    newNodeDetected: "New Node Detected!",
    isNowOnline: "is now online",
    
    // Alerts
    activeAlerts: "Active Alerts",
    noAlerts: "No active alerts",
    
    // Node Status
    lastSeen: "Last seen",
    never: "Never",
    battery: "Battery",
    online: "Online",
    offline: "Offline",
    
    // Soil Conditions
    soilConditions: "Soil Conditions",
    soilMoisture: "Soil Moisture",
    soilTemperature: "Soil Temperature",
    soilPH: "Soil pH",
    optimal: "Optimal",
    critical: "Critical",
    tooWet: "Too Wet",
    tooHot: "Too Hot",
    tooCold: "Too Cold",
    normal: "Normal",
    tooAcidic: "Too Acidic",
    tooAlkaline: "Too Alkaline",
    neutral: "Neutral",
    noData: "No Data",
    
    // Environmental Conditions
    environmentalConditions: "Environmental Conditions",
    airTemperature: "Air Temperature",
    airHumidity: "Air Humidity",
    veryHot: "Very Hot",
    cool: "Cool",
    comfortable: "Comfortable",
    dry: "Dry",
    veryHumid: "Very Humid",
    
    // NPK
    npkLevels: "NPK Levels",
    nitrogen: "Nitrogen (N)",
    phosphorus: "Phosphorus (P)",
    potassium: "Potassium (K)",
    
    // Charts
    soilConditionsChart: "Soil Conditions",
    environmentalConditionsChart: "Environmental Conditions",
    moisturePercent: "Moisture %",
    soilTempC: "Soil Temp °C",
    airTempC: "Air Temp °C",
    humidityPercent: "Humidity %",
    
    // Chatbot
    aiAgronomist: "AI Agronomist",
    askAboutSoil: "Ask about soil, crops...",
    hello: "Hello! I am your AI Agronomist. Ask me about your soil health or crop conditions.",
    
    // Settings Page
    knowledgeBaseSettings: "Agricultural Knowledge Base Settings",
    knowledgeBaseDesc: "Upload documents about crop growing conditions to teach the AI about optimal soil requirements for different crops.",
    uploadDocuments: "Upload Documents",
    supportedFormats: "Supported formats: PDF, DOCX, TXT",
    uploading: "Uploading...",
    uploadDocument: "Upload Document",
    whatToUpload: "What to upload:",
    uploadItem1: "Growing guides for specific crops (tomato, lettuce, rice, etc.)",
    uploadItem2: "Soil requirement charts and tables",
    uploadItem3: "Agricultural research papers",
    uploadItem4: "Farming best practices documentation",
    uploadItem5: "NPK fertilizer recommendations",
    
    testKnowledgeBase: "Test Knowledge Base",
    testKnowledgeDesc: "Search the knowledge base to verify uploaded documents are properly indexed.",
    searchPlaceholder: "e.g., 'What are optimal conditions for tomatoes?'",
    searching: "Searching...",
    search: "Search",
    foundResults: "Found",
    relevantChunks: "relevant chunks:",
    chunk: "Chunk",
    
    uploadedDocuments: "Uploaded Documents",
    documentsInKnowledgeBase: "in knowledge base",
    noDocumentsYet: "No documents uploaded yet",
    uploadFirstDoc: "Upload your first document to start building the knowledge base",
    knowledgeChunks: "knowledge chunks",
    crop: "Crop",
    source: "Source",
    deleteDocument: "Delete document",
    
    documentInfo: "Document Information",
    documentInfoDesc: "Help the AI understand this document",
    cropTypeOptional: "Crop Type (Optional)",
    cropTypePlaceholder: "e.g., tomato, lettuce, rice",
    cropTypeHelp: "Specify the crop if this document is crop-specific",
    descriptionOptional: "Description (Optional)",
    descriptionPlaceholder: "Brief description of the document content",
    cancel: "Cancel",
    
    // Language Settings
    languageSettings: "Language Settings",
    selectLanguage: "Select your preferred language",
    language: "Language",
    english: "English",
    filipino: "Filipino",
    
    // Notifications
    documentUploaded: "Document uploaded successfully! Created",
    uploadFailed: "Upload failed",
    documentDeleted: "Document deleted",
    deleteFailed: "Delete failed",
    searchFailed: "Search failed",
  },
  
  fil: {
    // Navigation
    dashboard: "Dashboard",
    settings: "Mga Setting",
    backToDashboard: "Bumalik sa Dashboard",
    
    // Header
    sproutHub: "Sprout Hub",
    monitoring: "Sinusubaybayan ang",
    nodes: "mga node",
    node: "node",
    detected: "nadetect",
    autoDetecting: "Automatic na sinusubaybayan ang mga soil monitoring node",
    
    // Loading
    loading: "Niloload ang Sprout Hub System...",
    detectingNodes: "Naghahanap ng mga soil node...",
    
    // No Nodes
    noNodesDetected: "Walang Nadetect na Soil Node",
    waitingForNodes: "Naghihintay para sa mga soil node na mag-online...",
    autoDetectionActive: "Auto-Detection Active",
    autoDetectionDesc: "Awtomatikong lalabas ang mga bagong node kapag nagpadala ng unang reading.",
    refreshPage: "I-refresh ang Page",
    
    // New Node Notification
    newNodeDetected: "May Bagong Node na Nadetect!",
    isNowOnline: "ay online na",
    
    // Alerts
    activeAlerts: "Mga Aktibong Alerto",
    noAlerts: "Walang mga aktibong alerto",
    
    // Node Status
    lastSeen: "Huling nakita",
    never: "Hindi pa",
    battery: "Baterya",
    online: "Online",
    offline: "Offline",
    
    // Soil Conditions
    soilConditions: "Kalagayan ng Lupa",
    soilMoisture: "Halumigmig ng Lupa",
    soilTemperature: "Temperatura ng Lupa",
    soilPH: "pH ng Lupa",
    optimal: "Tama",
    critical: "Kritikal",
    tooWet: "Sobrang Basa",
    tooHot: "Sobrang Init",
    tooCold: "Sobrang Lamig",
    normal: "Normal",
    tooAcidic: "Masyadong Asido",
    tooAlkaline: "Masyadong Alkaline",
    neutral: "Neutral",
    noData: "Walang Data",
    
    // Environmental Conditions
    environmentalConditions: "Kalagayan ng Kapaligiran",
    airTemperature: "Temperatura ng Hangin",
    airHumidity: "Halumigmig ng Hangin",
    veryHot: "Napakainit",
    cool: "Malamig",
    comfortable: "Komportable",
    dry: "Tuyo",
    veryHumid: "Napakahalumigmig",
    
    // NPK
    npkLevels: "Antas ng NPK",
    nitrogen: "Nitrogen (N)",
    phosphorus: "Phosphorus (P)",
    potassium: "Potassium (K)",
    
    // Charts
    soilConditionsChart: "Kalagayan ng Lupa",
    environmentalConditionsChart: "Kalagayan ng Kapaligiran",
    moisturePercent: "Halumigmig %",
    soilTempC: "Temp ng Lupa °C",
    airTempC: "Temp ng Hangin °C",
    humidityPercent: "Halumigmig %",
    
    // Chatbot
    aiAgronomist: "AI Agronomo",
    askAboutSoil: "Magtanong tungkol sa lupa, tanim...",
    hello: "Kumusta! Ako ang iyong AI Agronomo. Magtanong tungkol sa kalusugan ng iyong lupa o tanim.",
    
    // Settings Page
    knowledgeBaseSettings: "Mga Setting ng Agricultural Knowledge Base",
    knowledgeBaseDesc: "Mag-upload ng mga dokumento tungkol sa kondisyon ng pagtatanim upang turuan ang AI tungkol sa optimal na kinakailangan ng lupa para sa iba't ibang pananim.",
    uploadDocuments: "Mag-upload ng mga Dokumento",
    supportedFormats: "Supported na format: PDF, DOCX, TXT",
    uploading: "Nag-uupload...",
    uploadDocument: "I-upload ang Dokumento",
    whatToUpload: "Ano ang i-upload:",
    uploadItem1: "Mga gabay sa pagtatanim ng mga pananim (kamatis, lettuce, palay, atbp.)",
    uploadItem2: "Mga tsart at talahanayan ng kinakailangan ng lupa",
    uploadItem3: "Mga pananaliksik sa agrikultura",
    uploadItem4: "Dokumentasyon ng pinakamahusay na gawi sa pagsasaka",
    uploadItem5: "Mga rekomendasyon sa NPK fertilizer",
    
    testKnowledgeBase: "Subukan ang Knowledge Base",
    testKnowledgeDesc: "Maghanap sa knowledge base upang i-verify na tama ang pag-index ng mga naka-upload na dokumento.",
    searchPlaceholder: "hal., 'Ano ang optimal na kondisyon para sa kamatis?'",
    searching: "Naghahanap...",
    search: "Maghanap",
    foundResults: "Nakahanap ng",
    relevantChunks: "mga relevant na chunk:",
    chunk: "Chunk",
    
    uploadedDocuments: "Mga Na-upload na Dokumento",
    documentsInKnowledgeBase: "sa knowledge base",
    noDocumentsYet: "Wala pang na-upload na dokumento",
    uploadFirstDoc: "Mag-upload ng iyong unang dokumento upang magsimulang bumuo ng knowledge base",
    knowledgeChunks: "knowledge chunk",
    crop: "Pananim",
    source: "Pinagmulan",
    deleteDocument: "Tanggalin ang dokumento",
    
    documentInfo: "Impormasyon ng Dokumento",
    documentInfoDesc: "Tulungan ang AI na maintindihan ang dokumentong ito",
    cropTypeOptional: "Uri ng Pananim (Opsyonal)",
    cropTypePlaceholder: "hal., kamatis, lettuce, palay",
    cropTypeHelp: "Tukuyin ang pananim kung ang dokumentong ito ay para sa partikular na pananim",
    descriptionOptional: "Paglalarawan (Opsyonal)",
    descriptionPlaceholder: "Maikling paglalarawan ng nilalaman ng dokumento",
    cancel: "Kanselahin",
    
    // Language Settings
    languageSettings: "Mga Setting ng Wika",
    selectLanguage: "Pumili ng iyong preferred na wika",
    language: "Wika",
    english: "English",
    filipino: "Filipino",
    
    // Notifications
    documentUploaded: "Matagumpay na na-upload ang dokumento! Lumikha ng",
    uploadFailed: "Nabigo ang pag-upload",
    documentDeleted: "Tinanggal ang dokumento",
    deleteFailed: "Nabigo ang pagtanggal",
    searchFailed: "Nabigo ang paghahanap",
  }
};

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    // Load from localStorage or default to English
    return localStorage.getItem('sprouthub_language') || 'en';
  });

  useEffect(() => {
    // Save to localStorage when language changes
    localStorage.setItem('sprouthub_language', language);
  }, [language]);

  const t = (key) => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
}